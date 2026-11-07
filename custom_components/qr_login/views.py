"""HTTP endpoints and pages for QR Login."""

import hmac
import logging
import secrets
import time
from pathlib import Path
from urllib.parse import urlparse

from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant
from homeassistant.helpers.network import NoURLAvailableError

from .auth_util import (
    async_create_token_for_user,
    async_resolve_user,
    resolve_client_id,
)
from .const import (
    CHANNEL_NOTIFY,
    CHANNEL_QR,
    CONF_ALLOWED_CLIENT_IDS,
    CONF_CHANNEL,
    CONF_DEFAULT_CHANNEL,
    CONF_ENABLED_CHANNELS,
    CONF_NOTIFY_TARGET,
    CONF_RECAPTCHA_SECRET_KEY,
    CONF_RECAPTCHA_SITE_KEY,
    CONF_SESSION_TIMEOUT,
    CONF_TARGET_USER,
    CONF_USER_MAPPINGS,
    DEFAULT_CHANNEL,
    DEFAULT_ENABLED_CHANNELS,
    DEFAULT_SESSION_TIMEOUT,
    DOMAIN,
    VALID_CHANNELS,
)
from .notify_channel import send_approval_notification
from .session import QRLoginSession, record_outcome

_LOGGER = logging.getLogger(__name__)

WWW_DIR = Path(__file__).parent / "www"


def _get_data(hass: HomeAssistant):
    """Return the single QrLoginData holder, or None before setup."""
    return hass.data.get(DOMAIN)


async def _read_json_object(request: web.Request) -> dict | None:
    """Parse a request body that must be a JSON object."""
    try:
        payload = await request.json()
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _clean_str(value, max_length: int = 255) -> str:
    """Coerce an untrusted JSON value to a bounded, stripped string."""
    if not isinstance(value, str):
        return ""
    return value.strip()[:max_length]


def _origin_from_request(request: web.Request) -> str:
    """Accept a page origin only when it matches the request host."""
    candidate = request.headers.get("Origin") or request.headers.get("Referer")
    if not candidate:
        return ""
    try:
        parsed = urlparse(candidate)
    except ValueError:
        return ""
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return ""
    if not request.host or parsed.netloc.casefold() != request.host.casefold():
        return ""
    return f"{parsed.scheme}://{parsed.netloc}/"


class QRLoginStartView(HomeAssistantView):
    url = "/api/qr_login/start"
    name = "api:qr_login:start"
    requires_auth = False
    cors_allowed = True

    async def post(self, request: web.Request) -> web.Response:
        hass: HomeAssistant = request.app["hass"]
        data = _get_data(hass)

        if data is None or not data.config.get("enabled", True):
            return self.json({"error": "disabled"}, status_code=503)

        client_ip = request.remote or "unknown"

        if not data.rate_limiter.check_ip_limit(client_ip):
            return self.json(
                {
                    "error": "rate_limited",
                    "retry_after": data.rate_limiter.ip_window,
                },
                status_code=429,
            )

        if not data.rate_limiter.check_global_limit():
            return self.json(
                {
                    "error": "rate_limited_global",
                    "retry_after": data.rate_limiter.global_window,
                },
                status_code=429,
            )

        payload = await _read_json_object(request)
        if payload is None:
            return self.json({"error": "invalid_json"}, status_code=400)

        allowed_client_ids = data.config.get(CONF_ALLOWED_CLIENT_IDS)
        if not allowed_client_ids:
            request_origin = _origin_from_request(request)
            try:
                resolved_client_id = resolve_client_id(hass, None)
            except NoURLAvailableError:
                resolved_client_id = ""
            allowed_client_ids = [
                value for value in (request_origin, resolved_client_id) if value
            ]
            if not allowed_client_ids:
                return self.json({"error": "client_id_unavailable"}, status_code=503)
        client_id = payload.get("client_id", allowed_client_ids[0])
        if not isinstance(client_id, str) or client_id not in allowed_client_ids:
            return self.json({"error": "invalid_client_id"}, status_code=400)

        username = _clean_str(payload.get("username"))
        requested_channel = payload.get("channel")
        recaptcha_token = payload.get("recaptcha_token")

        if data.config.get(CONF_RECAPTCHA_SECRET_KEY) and not recaptcha_token:
            return self.json({"error": "recaptcha_required"}, status_code=400)

        if recaptcha_token:
            from .recaptcha import verify_recaptcha

            if not isinstance(recaptcha_token, str) or not await verify_recaptcha(
                hass, recaptcha_token
            ):
                return self.json({"error": "recaptcha_failed"}, status_code=400)

        user_mappings = data.config.get(CONF_USER_MAPPINGS, {})
        mapping = user_mappings.get(username) if username else None

        session_id = secrets.token_urlsafe(24)

        enabled_channels = data.config.get(
            CONF_ENABLED_CHANNELS, DEFAULT_ENABLED_CHANNELS
        )
        if (
            requested_channel in VALID_CHANNELS
            and requested_channel in enabled_channels
        ):
            channel = requested_channel
        else:
            channel = data.config.get(CONF_DEFAULT_CHANNEL, DEFAULT_CHANNEL)
            if channel not in enabled_channels:
                channel = enabled_channels[0] if enabled_channels else CHANNEL_QR

        public_channel = channel

        target_user = ""
        target_from_mapping = False
        notify_target = ""
        if mapping:
            target_user = mapping.get(CONF_TARGET_USER) or ""
            target_from_mapping = bool(target_user)
            notify_target = mapping.get(CONF_NOTIFY_TARGET) or ""
            mapped_channel = mapping.get(CONF_CHANNEL)
            if mapped_channel in VALID_CHANNELS:
                channel = mapped_channel

        session = QRLoginSession(
            session_id=session_id,
            username=username,
            target_user=target_user,
            notify_target=notify_target,
            channel=channel,
            public_channel=public_channel,
            target_from_mapping=target_from_mapping,
            client_id=client_id,
            poll_secret=secrets.token_urlsafe(32),
            client_ip=client_ip,
            user_agent=_clean_str(request.headers.get("User-Agent")) or "unknown",
            expires_at=time.time()
            + data.config.get(CONF_SESSION_TIMEOUT, DEFAULT_SESSION_TIMEOUT),
        )
        data.sessions[session_id] = session

        if mapping and notify_target and channel == CHANNEL_NOTIFY:
            cooldown_key = f"notify_{notify_target}"
            if data.rate_limiter.check_notification_cooldown(cooldown_key):
                try:
                    await send_approval_notification(hass, session)
                except Exception:
                    _LOGGER.warning(
                        "Could not send the approval notification to %s",
                        notify_target,
                        exc_info=True,
                    )

        return self.json(
            {
                "status": "pending",
                "session_id": session_id,
                "poll_secret": session.poll_secret,
                "channel": public_channel,
                "expires_in": data.config.get(
                    CONF_SESSION_TIMEOUT, DEFAULT_SESSION_TIMEOUT
                ),
            },
            headers={"Cache-Control": "no-store"},
        )


class QRLoginStatusView(HomeAssistantView):
    url = "/api/qr_login/status"
    name = "api:qr_login:status"
    requires_auth = False
    cors_allowed = True

    @staticmethod
    def json(result, status_code=200, headers=None):
        return HomeAssistantView.json(
            result, status_code, headers={**(headers or {}), "Cache-Control": "no-store"}
        )

    async def get(self, request: web.Request) -> web.Response:
        data = _get_data(request.app["hass"])
        session_id = request.query.get("session_id")

        if not session_id:
            return self.json({"error": "session_id_required"}, status_code=400)

        if data is None:
            return self.json({"error": "session_not_found"}, status_code=404)

        if not data.config.get("enabled", True):
            return self.json({"error": "disabled"}, status_code=503)

        session = data.sessions.get(session_id)
        if session is None:
            return self.json({"error": "session_not_found"}, status_code=404)

        if session.is_expired():
            record_outcome(data, session, "expired")
            data.sessions.pop(session_id, None)
            return self.json({"status": "expired"})

        if session.status in ("denied", "error"):
            data.sessions.pop(session_id, None)
            return self.json(session.to_public_dict())

        # The QR is public, so only its separate poll secret can collect tokens.
        scheme, _, poll_secret = request.headers.get("Authorization", "").partition(" ")
        if scheme.casefold() != "qrlogin":
            poll_secret = ""
        if (
            session.status == "approved"
            and session.access_token is not None
            and poll_secret.isascii()
            and hmac.compare_digest(session.poll_secret, poll_secret)
        ):
            payload = session.to_public_dict(include_tokens=True)
            session.access_token = None
            session.refresh_token = None
            data.sessions.pop(session_id, None)
            return self.json(payload)

        return self.json(session.to_public_dict())


class QRLoginSessionInfoView(HomeAssistantView):
    """Request details for the approver.

    Authenticated on purpose: the anonymous /status endpoint must not
    disclose which account a request maps to.
    """

    url = "/api/qr_login/session"
    name = "api:qr_login:session"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        hass: HomeAssistant = request.app["hass"]
        data = _get_data(hass)
        session_id = request.query.get("session_id")

        if not session_id:
            return self.json({"error": "session_id_required"}, status_code=400)

        if data is None or not data.config.get("enabled", True):
            return self.json({"error": "disabled"}, status_code=503)

        session = data.sessions.get(session_id)
        if session is None:
            return self.json({"error": "session_not_found"}, status_code=404)

        if session.is_expired():
            data.sessions.pop(session_id, None)
            return self.json({"status": "expired"})

        details = session.to_detail_dict()

        if session.target_from_mapping and session.target_user:
            user = await async_resolve_user(hass, session.target_user)
            details["target_user_name"] = (
                user.name if user and user.name else session.target_user
            )
        else:
            approver = request["hass_user"]
            details["target_user_name"] = approver.name or approver.id

        return self.json(details)


class QRLoginSessionsView(HomeAssistantView):
    """Admin-only overview of the requests currently in flight."""

    url = "/api/qr_login/sessions"
    name = "api:qr_login:sessions"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        hass: HomeAssistant = request.app["hass"]
        data = _get_data(hass)

        if not request["hass_user"].is_admin:
            return self.json({"error": "admin_required"}, status_code=403)

        if data is None:
            return self.json({"error": "not_initialized"}, status_code=503)

        names = {
            user.id: user.name
            for user in await hass.auth.async_get_users()
            if user.name
        }

        sessions = []
        for session in list(data.sessions.values()):
            # Pending only: a resolved session would make the cancel button
            # look like a no-op, since the row would simply reappear.
            if session.is_expired() or session.status != "pending":
                continue
            details = session.to_detail_dict()
            details["target_user_name"] = names.get(
                session.target_user, session.target_user
            )
            sessions.append(details)

        sessions.sort(key=lambda item: item["age"])

        now = time.time()
        history = []
        for entry in data.history:
            item = dict(entry)
            item["target_user_name"] = names.get(
                entry["target_user"], entry["target_user"]
            )
            item["age"] = max(0, int(now - entry["at"]))
            history.append(item)

        return self.json(
            {
                "enabled": data.config.get("enabled", True),
                "sessions": sessions,
                "history": history,
            }
        )


class QRLoginSessionCancelView(HomeAssistantView):
    """Admin-only cancellation of a request in flight."""

    url = "/api/qr_login/sessions/{session_id}"
    name = "api:qr_login:session_cancel"
    requires_auth = True

    async def delete(self, request: web.Request, session_id: str) -> web.Response:
        data = _get_data(request.app["hass"])

        if not request["hass_user"].is_admin:
            return self.json({"error": "admin_required"}, status_code=403)

        if data is None:
            return self.json({"error": "not_initialized"}, status_code=503)

        session = data.sessions.get(session_id)
        if session is None:
            return self.json({"error": "session_not_found"}, status_code=404)

        session.status = "denied"
        session.access_token = None
        session.refresh_token = None

        admin_label = request["hass_user"].name or request["hass_user"].id
        record_outcome(data, session, "cancelled", admin_label)

        _LOGGER.info(
            "QR Login session %s cancelled by '%s'", session_id, admin_label
        )
        return self.json({"status": "denied"})


class QRLoginApproveView(HomeAssistantView):
    url = "/api/qr_login/approve"
    name = "api:qr_login:approve"
    requires_auth = True

    async def post(self, request: web.Request) -> web.Response:
        hass: HomeAssistant = request.app["hass"]
        data = _get_data(hass)

        if data is None or not data.config.get("enabled", True):
            return self.json({"error": "disabled"}, status_code=503)

        payload = await _read_json_object(request)
        if payload is None:
            return self.json({"error": "invalid_json"}, status_code=400)

        session_id = payload.get("session_id")
        action = payload.get("action")

        if not isinstance(session_id, str) or not session_id:
            return self.json({"error": "invalid_request"}, status_code=400)
        if action not in ("approve", "deny"):
            return self.json({"error": "invalid_request"}, status_code=400)

        session = data.sessions.get(session_id)
        if session is None:
            return self.json({"error": "session_not_found"}, status_code=404)

        if session.is_expired():
            data.sessions.pop(session_id, None)
            return self.json({"status": "expired"})

        if session.status != "pending":
            return self.json({"error": "session_already_processed"}, status_code=400)

        approver = request["hass_user"]
        approver_label = approver.name or approver.id

        if action == "deny":
            session.status = "denied"
            record_outcome(data, session, "denied", approver_label)
            return self.json({"status": "denied"})

        if session.target_from_mapping and session.target_user:
            user = await async_resolve_user(hass, session.target_user)
            if user is None:
                session.status = "error"
                record_outcome(data, session, "error", approver_label)
                return self.json(
                    {"error": "target_user_not_found"}, status_code=404
                )
        else:
            user = approver
            session.target_user = user.id

        # Approving for someone else hands out credentials the approver may
        # not hold, so it takes an admin.
        if user.id != approver.id and not approver.is_admin:
            _LOGGER.warning(
                "User '%s' is not an administrator and cannot approve access "
                "for account '%s'",
                approver_label,
                user.name or user.id,
            )
            session.status = "error"
            record_outcome(data, session, "error", approver_label)
            return self.json({"error": "admin_required"}, status_code=403)

        try:
            access_token, refresh_token, expires_in = await async_create_token_for_user(
                hass,
                user,
                client_ip=session.client_ip,
                client_id=session.client_id,
            )
        except Exception:
            _LOGGER.exception(
                "Could not issue the token for session %s", session_id
            )
            session.status = "error"
            record_outcome(data, session, "error", approver_label)
            return self.json({"error": "token_creation_failed"}, status_code=500)

        session.access_token = access_token
        session.refresh_token = refresh_token
        session.token_expires_in = expires_in
        session.status = "approved"
        record_outcome(data, session, "approved", approver_label)

        return self.json(
            {
                "status": "approved",
                "target_user": session.target_user,
                "target_user_name": user.name or session.target_user,
            }
        )


class QRLoginStartPageView(HomeAssistantView):
    url = "/qr_login/start"
    name = "qr_login:start_page"
    requires_auth = False

    async def get(self, request: web.Request) -> web.Response:
        html_path = WWW_DIR / "qr_login_start.html"
        if not html_path.exists():
            return web.Response(text="Start page not found", status=404)
        return web.FileResponse(html_path)


class QRLoginApprovePageView(HomeAssistantView):
    url = "/qr_login/approve"
    name = "qr_login:approve_page"
    requires_auth = False

    async def get(self, request: web.Request) -> web.Response:
        html_path = WWW_DIR / "qr_login_approve.html"
        if not html_path.exists():
            return web.Response(text="Approve page not found", status=404)
        return web.FileResponse(html_path)


class QRLoginSessionsPageView(HomeAssistantView):
    """The admin panel page. Its data comes from the admin-only API."""

    url = "/qr_login/sessions"
    name = "qr_login:sessions_page"
    requires_auth = False

    async def get(self, request: web.Request) -> web.Response:
        html_path = WWW_DIR / "qr_login_sessions.html"
        if not html_path.exists():
            return web.Response(text="Sessions page not found", status=404)
        return web.FileResponse(html_path)


class QRLoginAssetView(HomeAssistantView):
    """Serve the static assets bundled with the component."""

    url = "/qr_login/static/{filename}"
    name = "qr_login:static"
    requires_auth = False

    _ALLOWED = {
        "qrcode.min.js": "application/javascript",
        "i18n.js": "application/javascript",
    }

    async def get(self, request: web.Request, filename: str) -> web.Response:
        content_type = self._ALLOWED.get(filename)
        if content_type is None:
            return web.Response(text="Not found", status=404)

        asset_path = WWW_DIR / "static" / filename
        if not asset_path.is_file():
            return web.Response(text="Not found", status=404)

        return web.FileResponse(
            asset_path, headers={"Content-Type": content_type}
        )


class QRLoginPublicConfigView(HomeAssistantView):
    url = "/api/qr_login/config"
    name = "api:qr_login:config"
    requires_auth = False

    async def get(self, request: web.Request) -> web.Response:
        data = _get_data(request.app["hass"])
        if data is None:
            return self.json(
                {"error": "not_initialized"}, status_code=503
            )

        return self.json(
            {
                "enabled_channels": data.config.get(
                    CONF_ENABLED_CHANNELS, DEFAULT_ENABLED_CHANNELS
                ),
                "recaptcha_site_key": data.config.get(
                    CONF_RECAPTCHA_SITE_KEY, ""
                ),
                "default_channel": data.config.get(
                    CONF_DEFAULT_CHANNEL, DEFAULT_CHANNEL
                ),
            }
        )
