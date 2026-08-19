"""Server-side reCAPTCHA v3 verification."""

import logging

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_RECAPTCHA_SECRET_KEY,
    CONF_RECAPTCHA_THRESHOLD,
    DOMAIN,
    RECAPTCHA_ACTION,
)

_LOGGER = logging.getLogger(__name__)

RECAPTCHA_VERIFY_URL = "https://www.google.com/recaptcha/api/siteverify"


async def verify_recaptcha(hass: HomeAssistant, token: str) -> bool:
    """Verify a reCAPTCHA v3 token server-side using HA's shared session."""
    data = hass.data.get(DOMAIN)
    if data is None:
        return False

    config = data.config
    secret_key = config.get(CONF_RECAPTCHA_SECRET_KEY)
    threshold = config.get(CONF_RECAPTCHA_THRESHOLD, 0.5)

    if not secret_key:
        return True

    session = async_get_clientsession(hass)
    try:
        async with session.post(
            RECAPTCHA_VERIFY_URL,
            data={"secret": secret_key, "response": token},
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            result = await resp.json()

        if not result.get("success", False):
            _LOGGER.debug(
                "reCAPTCHA rejected: %s", result.get("error-codes")
            )
            return False

        action = result.get("action")
        if action is not None and action != RECAPTCHA_ACTION:
            _LOGGER.warning(
                "reCAPTCHA token has unexpected action '%s' (expected '%s')",
                action,
                RECAPTCHA_ACTION,
            )
            return False

        score = result.get("score", 0.0)
        if score < threshold:
            _LOGGER.debug(
                "reCAPTCHA score %.2f below threshold %.2f", score, threshold
            )
            return False

        return True
    except Exception:
        _LOGGER.warning("reCAPTCHA verification failed", exc_info=True)
        return False
