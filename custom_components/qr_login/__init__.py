"""The QR Login integration."""

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from homeassistant.components import frontend
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_interval

from .const import (
    CONF_DEFAULT_CHANNEL,
    CONF_ENABLED_CHANNELS,
    CONF_NOTIFICATION_COOLDOWN,
    CONF_RATE_LIMIT_GLOBAL,
    CONF_RATE_LIMIT_GLOBAL_WINDOW,
    CONF_RATE_LIMIT_IP,
    CONF_RATE_LIMIT_IP_WINDOW,
    CONF_RECAPTCHA_SECRET_KEY,
    CONF_RECAPTCHA_SITE_KEY,
    CONF_RECAPTCHA_THRESHOLD,
    CONF_SESSION_TIMEOUT,
    CONF_USER_MAPPINGS,
    DEFAULT_CHANNEL,
    DEFAULT_ENABLED_CHANNELS,
    DEFAULT_NOTIFICATION_COOLDOWN,
    DEFAULT_RATE_LIMIT_GLOBAL,
    DEFAULT_RATE_LIMIT_GLOBAL_WINDOW,
    DEFAULT_RATE_LIMIT_IP,
    DEFAULT_RATE_LIMIT_IP_WINDOW,
    DEFAULT_RECAPTCHA_THRESHOLD,
    DEFAULT_SESSION_TIMEOUT,
    DOMAIN,
)
from .notify_channel import async_setup_notification_listener
from .rate_limit import RateLimiter
from .session import QRLoginSession, new_history, record_outcome
from .switch import QRLoginEnabledSwitch
from .views import (
    QRLoginApprovePageView,
    QRLoginApproveView,
    QRLoginAssetView,
    QRLoginPublicConfigView,
    QRLoginSessionCancelView,
    QRLoginSessionInfoView,
    QRLoginSessionsPageView,
    QRLoginSessionsView,
    QRLoginStartPageView,
    QRLoginStartView,
    QRLoginStatusView,
)

_VIEWS_REGISTERED_KEY = f"{DOMAIN}_views_registered"
_PANEL_URL_PATH = "qr-login"


@dataclass
class QrLoginData:
    config: dict[str, Any]
    sessions: dict[str, QRLoginSession]
    rate_limiter: RateLimiter
    kill_switch: QRLoginEnabledSwitch | None = None
    history: deque = field(default_factory=new_history)


def _config_from_options(options: dict[str, Any]) -> dict[str, Any]:
    return {
        "enabled": True,
        CONF_DEFAULT_CHANNEL: options.get(CONF_DEFAULT_CHANNEL, DEFAULT_CHANNEL),
        CONF_ENABLED_CHANNELS: options.get(
            CONF_ENABLED_CHANNELS, DEFAULT_ENABLED_CHANNELS
        ),
        CONF_RECAPTCHA_SITE_KEY: options.get(CONF_RECAPTCHA_SITE_KEY, ""),
        CONF_RECAPTCHA_SECRET_KEY: options.get(CONF_RECAPTCHA_SECRET_KEY, ""),
        CONF_RECAPTCHA_THRESHOLD: options.get(
            CONF_RECAPTCHA_THRESHOLD, DEFAULT_RECAPTCHA_THRESHOLD
        ),
        CONF_RATE_LIMIT_IP: options.get(CONF_RATE_LIMIT_IP, DEFAULT_RATE_LIMIT_IP),
        CONF_RATE_LIMIT_IP_WINDOW: options.get(
            CONF_RATE_LIMIT_IP_WINDOW, DEFAULT_RATE_LIMIT_IP_WINDOW
        ),
        CONF_RATE_LIMIT_GLOBAL: options.get(
            CONF_RATE_LIMIT_GLOBAL, DEFAULT_RATE_LIMIT_GLOBAL
        ),
        CONF_RATE_LIMIT_GLOBAL_WINDOW: options.get(
            CONF_RATE_LIMIT_GLOBAL_WINDOW, DEFAULT_RATE_LIMIT_GLOBAL_WINDOW
        ),
        CONF_NOTIFICATION_COOLDOWN: options.get(
            CONF_NOTIFICATION_COOLDOWN, DEFAULT_NOTIFICATION_COOLDOWN
        ),
        CONF_SESSION_TIMEOUT: options.get(
            CONF_SESSION_TIMEOUT, DEFAULT_SESSION_TIMEOUT
        ),
        CONF_USER_MAPPINGS: options.get(CONF_USER_MAPPINGS, {}),
    }


def _make_rate_limiter(config: dict[str, Any]) -> RateLimiter:
    return RateLimiter(
        max_per_ip=config[CONF_RATE_LIMIT_IP],
        ip_window=config[CONF_RATE_LIMIT_IP_WINDOW],
        max_global=config[CONF_RATE_LIMIT_GLOBAL],
        global_window=config[CONF_RATE_LIMIT_GLOBAL_WINDOW],
        notification_cooldown=config[CONF_NOTIFICATION_COOLDOWN],
    )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    config = _config_from_options(entry.options)
    data = QrLoginData(
        config=config,
        sessions={},
        rate_limiter=_make_rate_limiter(config),
    )
    hass.data[DOMAIN] = data
    entry.runtime_data = data

    # HA cannot unregister views, so registering them again on a config
    # entry reload would raise on the duplicate routes.
    if not hass.data.get(_VIEWS_REGISTERED_KEY):
        hass.http.register_view(QRLoginStartView())
        hass.http.register_view(QRLoginStatusView())
        hass.http.register_view(QRLoginSessionInfoView())
        hass.http.register_view(QRLoginSessionsView())
        hass.http.register_view(QRLoginSessionCancelView())
        hass.http.register_view(QRLoginApproveView())
        hass.http.register_view(QRLoginPublicConfigView())
        hass.http.register_view(QRLoginStartPageView())
        hass.http.register_view(QRLoginApprovePageView())
        hass.http.register_view(QRLoginSessionsPageView())
        hass.http.register_view(QRLoginAssetView())
        hass.data[_VIEWS_REGISTERED_KEY] = True

    frontend.async_register_built_in_panel(
        hass,
        component_name="iframe",
        sidebar_title="QR Login",
        sidebar_icon="mdi:qrcode-scan",
        frontend_url_path=_PANEL_URL_PATH,
        config={"url": "/qr_login/sessions"},
        require_admin=True,
        update=True,
    )

    unsub = async_setup_notification_listener(hass)
    entry.async_on_unload(unsub)

    async def _cleanup_sessions(now: datetime | None = None) -> None:
        for session_id in [
            sid
            for sid, session in data.sessions.items()
            if session.is_expired()
        ]:
            record_outcome(data, data.sessions[session_id], "expired")
            del data.sessions[session_id]

    unsub_cleanup = async_track_time_interval(
        hass, _cleanup_sessions, timedelta(seconds=60)
    )
    entry.async_on_unload(unsub_cleanup)

    await hass.config_entries.async_forward_entry_setups(entry, ["switch"])

    entry.async_on_unload(entry.add_update_listener(async_update_options))

    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    data = hass.data.get(DOMAIN)
    if data is None:
        return
    data.config = _config_from_options(entry.options)
    data.rate_limiter = _make_rate_limiter(data.config)
    if data.kill_switch is not None:
        data.config["enabled"] = data.kill_switch.is_on


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, ["switch"]
    )
    if unload_ok:
        frontend.async_remove_panel(hass, _PANEL_URL_PATH, warn_if_unknown=False)
        hass.data.pop(DOMAIN, None)
    return unload_ok
