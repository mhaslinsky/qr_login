"""Actionable push notifications for approval requests."""

import logging

from homeassistant.core import HomeAssistant, Event
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from homeassistant.util import slugify

try:
    # Private constant of the legacy notify platform, imported
    # defensively so its removal degrades to the slugify fallback below.
    from homeassistant.components.notify.legacy import NOTIFY_SERVICES
except ImportError:
    NOTIFY_SERVICES = "notify_services"

from .auth_util import async_create_token_for_user, async_resolve_user
from .const import (
    ACTION_APPROVE_PREFIX,
    ACTION_DENY_PREFIX,
    DOMAIN,
    EVENT_MOBILE_APP_NOTIFICATION_ACTION,
    NOTIFICATION_TAG,
)
from .session import QRLoginSession, record_outcome

_LOGGER = logging.getLogger(__name__)


def _async_resolve_notify_service(
    hass: HomeAssistant, entity_id: str
) -> str | None:
    """Resolve the per-device notify service for a notify entity.

    The service is named after the device registration, not the entity id,
    which can be renamed at any time, so match on the webhook id instead.
    """
    if not entity_id:
        return None

    registry = async_get_entity_registry(hass)
    entry = registry.async_get(entity_id)
    if entry is None or entry.config_entry_id is None:
        return None

    config_entry = hass.config_entries.async_get_entry(entry.config_entry_id)
    if config_entry is None:
        return None

    webhook_id = config_entry.data.get("webhook_id")
    for services in hass.data.get(NOTIFY_SERVICES, {}).values():
        for service in services:
            for name, target in getattr(service, "registered_targets", {}).items():
                if target == webhook_id:
                    return name

    device_name = config_entry.data.get("device_name")
    if entry.platform and device_name:
        return slugify(f"{entry.platform}_{device_name}")

    return None


_NOTIFICATION_STRINGS = {
    "en": {
        "title": "QR Login access request",
        "for_account": "Access requested for '{account}'",
        "username": "Requested username: {username}",
        "user_agent": "User agent",
        "approve": "Approve",
        "deny": "Reject",
    },
    "it": {
        "title": "Richiesta accesso QR Login",
        "for_account": "Richiesta di accesso per '{account}'",
        "username": "Username richiesto: {username}",
        "user_agent": "User-Agent",
        "approve": "Approva",
        "deny": "Rifiuta",
    },
}


def _notification_strings(hass: HomeAssistant) -> dict[str, str]:
    """Pick the notification wording for the instance language."""
    language = (getattr(hass.config, "language", None) or "en").lower()
    return (
        _NOTIFICATION_STRINGS.get(language)
        or _NOTIFICATION_STRINGS.get(language.split("-")[0])
        or _NOTIFICATION_STRINGS["en"]
    )


async def send_approval_notification(
    hass: HomeAssistant, session: QRLoginSession
) -> None:
    """Send a push notification with Approve/Deny actions."""
    target_user = await async_resolve_user(hass, session.target_user)
    target_label = (
        target_user.name if target_user and target_user.name else session.target_user
    )

    strings = _notification_strings(hass)

    title = strings["title"]
    message = (
        f"{strings['for_account'].format(account=target_label)}\n"
        f"{strings['username'].format(username=session.username)}\n"
        f"IP: {session.client_ip}\n"
        f"{strings['user_agent']}: {session.user_agent}"
    )

    approve_action = f"{ACTION_APPROVE_PREFIX}{session.session_id}"
    deny_action = f"{ACTION_DENY_PREFIX}{session.session_id}"

    data = {
        "actions": [
            {"action": approve_action, "title": strings["approve"]},
            {"action": deny_action, "title": strings["deny"]},
        ],
        "tag": NOTIFICATION_TAG,
    }

    service_name = _async_resolve_notify_service(hass, session.notify_target)
    if service_name is None:
        _LOGGER.error(
            "No notify service found for entity '%s' "
            "(renamed entity, or not a mobile_app one?)",
            session.notify_target,
        )
        return

    if not hass.services.has_service("notify", service_name):
        _LOGGER.error(
            "Notify service '%s' is not available for entity '%s'",
            service_name,
            session.notify_target,
        )
        return

    await hass.services.async_call(
        "notify",
        service_name,
        {
            "message": message,
            "title": title,
            "data": data,
        },
        blocking=False,
    )


def async_setup_notification_listener(hass: HomeAssistant):
    """Listen for mobile_app_notification_action events."""

    async def handle_notification_action(event: Event) -> None:
        action = event.data.get("action")
        if not action:
            return

        session_id = None
        approve = None

        if action.startswith(ACTION_APPROVE_PREFIX):
            session_id = action[len(ACTION_APPROVE_PREFIX) :]
            approve = True
        elif action.startswith(ACTION_DENY_PREFIX):
            session_id = action[len(ACTION_DENY_PREFIX) :]
            approve = False
        else:
            return

        data = hass.data.get(DOMAIN)
        if data is None:
            return

        if not data.config.get("enabled", True):
            _LOGGER.warning(
                "Approval action ignored: QR Login is disabled"
            )
            return

        session = data.sessions.get(session_id)
        if session is None or session.status != "pending":
            return

        if session.is_expired():
            record_outcome(data, session, "expired")
            data.sessions.pop(session_id, None)
            return

        decided_by = f"notification → {session.notify_target}"

        if not approve:
            session.status = "denied"
            record_outcome(data, session, "denied", decided_by)
            return

        if not (session.target_from_mapping and session.target_user):
            _LOGGER.error(
                "Session %s approved by notification but has no mapping: "
                "there is no account to issue the token for",
                session_id,
            )
            session.status = "error"
            record_outcome(data, session, "error", decided_by)
            return

        user = await async_resolve_user(hass, session.target_user)
        if user is None:
            session.status = "error"
            record_outcome(data, session, "error", decided_by)
            return

        try:
            access_token, refresh_token, expires_in = await async_create_token_for_user(
                hass, user, client_ip=session.client_ip, client_id=session.client_id
            )
        except Exception:
            _LOGGER.exception(
                "Could not issue the token for session %s", session_id
            )
            session.status = "error"
            record_outcome(data, session, "error", decided_by)
            return

        session.access_token = access_token
        session.refresh_token = refresh_token
        session.token_expires_in = expires_in
        session.status = "approved"
        record_outcome(data, session, "approved", decided_by)

    return hass.bus.async_listen(
        EVENT_MOBILE_APP_NOTIFICATION_ACTION, handle_notification_action
    )
