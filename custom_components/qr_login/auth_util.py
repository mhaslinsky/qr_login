"""User lookup and token creation helpers."""

import ipaddress
import logging
from typing import TYPE_CHECKING

from homeassistant.core import HomeAssistant
from homeassistant.helpers.network import NoURLAvailableError, get_url

from .const import CLIENT_NAME

if TYPE_CHECKING:
    from homeassistant.auth.models import User

_LOGGER = logging.getLogger(__name__)


async def async_resolve_user(
    hass: HomeAssistant, identifier: str
) -> "User | None":
    """Resolve a user by id, then by display name.

    Display names are not unique, so an ambiguous name is refused rather
    than resolved to whichever account comes first.
    """
    if not identifier:
        return None

    if user := await hass.auth.async_get_user(identifier):
        return user

    identifier_lower = identifier.casefold()
    matches = [
        user
        for user in await hass.auth.async_get_users()
        if user.name
        and user.name.casefold() == identifier_lower
        and user.is_active
        and not user.system_generated
    ]

    if len(matches) > 1:
        _LOGGER.error(
            "Name '%s' matches %d accounts, cannot decide which one to issue "
            "the token for. Use the user id in the mapping.",
            identifier,
            len(matches),
        )
        return None

    return matches[0] if matches else None


def resolve_client_id(hass: HomeAssistant, preferred: str | None) -> str:
    """Return the client_id to mint the refresh token with.

    HA ties a refresh token to a client_id and the frontend refreshes it by
    posting its own origin with a trailing slash. A mismatch, or a non-URL
    client_id, makes the token unrefreshable.
    """
    if preferred:
        return preferred

    for prefer_external in (False, True):
        try:
            return get_url(hass, prefer_external=prefer_external).rstrip("/") + "/"
        except NoURLAvailableError:
            continue

    raise NoURLAvailableError(
        "Cannot determine the Home Assistant URL for the client_id"
    )


def _sanitize_remote_ip(client_ip: str | None) -> str | None:
    """Drop placeholder values HA would store as a bogus remote address."""
    if not client_ip:
        return None
    try:
        ipaddress.ip_address(client_ip)
    except ValueError:
        return None
    return client_ip


async def async_create_token_for_user(
    hass: HomeAssistant,
    user: "User",
    client_ip: str | None = None,
    client_id: str | None = None,
) -> tuple[str, str, int]:
    """Create a refresh + access token, returning them with the lifetime."""
    refresh_token = await hass.auth.async_create_refresh_token(
        user,
        client_id=resolve_client_id(hass, client_id),
        client_name=CLIENT_NAME,
    )
    access_token = hass.auth.async_create_access_token(
        refresh_token, remote_ip=_sanitize_remote_ip(client_ip)
    )
    expires_in = int(refresh_token.access_token_expiration.total_seconds())
    return access_token, refresh_token.token, expires_in
