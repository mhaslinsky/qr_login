import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from custom_components.qr_login import _config_from_options, views
from custom_components.qr_login.config_flow import QRLoginOptionsFlow
from custom_components.qr_login.const import DOMAIN

@pytest.fixture
def login(hass):
    hass.config.external_url = "https://ha.test"
    data = SimpleNamespace(config=_config_from_options({}), sessions={}, rate_limiter=Mock())
    hass.data[DOMAIN] = data
    return data, Mock(app={"hass": hass}, remote="127.0.0.1", headers={}, query={}, json=AsyncMock(return_value={}))

async def test_poll_secret_collects_tokens_once(login):
    data, request = login
    start = json.loads((await views.QRLoginStartView().post(request)).body)
    session = data.sessions[start["session_id"]]
    assert start["poll_secret"] != session.session_id and session.client_id == "https://ha.test/"
    session.status, session.access_token, session.refresh_token = "approved", "access", "refresh"
    for secret, collects in ((None, False), ("wrong", False), (start["poll_secret"], True), (start["poll_secret"], False)):
        request.query = {"session_id": session.session_id, "poll_secret": start["poll_secret"]}
        request.headers = {"Authorization": f"QRLogin {secret}"} if secret is not None else {}
        response = await views.QRLoginStatusView().get(request)
        assert response.headers["Cache-Control"] == "no-store"
        result = json.loads(response.body)
        if secret == start["poll_secret"] and not collects:
            assert response.status == 404
            continue
        assert result["status"] == "approved"
        assert ("access_token" in result) == collects
        assert ("refresh_token" in result) == collects
        if collects:
            assert (result["access_token"], result["refresh_token"]) == ("access", "refresh")
    assert session.access_token is None and session.refresh_token is None
    assert session.session_id not in data.sessions

async def test_client_id_allowlist_and_empty_default(login):
    data, request = login
    for allowed, client_id, expected in (([], "https://ha.test/", 200), (["https://home.test/"], "https://home.test/", 200), (["https://home.test/"], "https://evil.test/", 400)):
        data.config["allowed_client_ids"] = allowed
        request.json.return_value = {"client_id": client_id}
        response = await views.QRLoginStartView().post(request)
        assert response.status == expected
        if expected == 200:
            assert data.sessions[json.loads(response.body)["session_id"]].client_id == client_id

async def test_malformed_start_payloads(login):
    _, request = login
    for payload in ([], None, {"client_id": []}):
        request.json.return_value = payload
        assert (await views.QRLoginStartView().post(request)).status == 400
    request.json.side_effect = ValueError("invalid JSON")
    assert (await views.QRLoginStartView().post(request)).status == 400

async def test_clearing_allowlist_resets_option():
    flow = QRLoginOptionsFlow(SimpleNamespace(options={"allowed_client_ids": ["https://home.test/"]}))
    flow.async_create_entry = Mock(return_value={})
    validated = flow._main_schema(flow._options)({
        "channels": {"enabled_channels": ["qr"]}, "recaptcha": {},
        "rate_limiting": {}, "notifications": {},
    })
    await flow.async_step_main(validated)
    assert flow.async_create_entry.call_args.kwargs["data"]["allowed_client_ids"] == []

def test_only_public_polling_views_allow_cors():
    assert views.QRLoginStartView.cors_allowed and views.QRLoginStatusView.cors_allowed
    assert all(not view.cors_allowed for view in (views.QRLoginApproveView, views.QRLoginSessionInfoView, views.QRLoginSessionsView, views.QRLoginSessionCancelView, views.QRLoginPublicConfigView, views.QRLoginStartPageView, views.QRLoginApprovePageView, views.QRLoginSessionsPageView, views.QRLoginAssetView))

async def test_denied_and_error_sessions_are_consumed(login):
    data, request = login
    for status in ("denied", "error"):
        start = json.loads((await views.QRLoginStartView().post(request)).body)
        data.sessions[start["session_id"]].status = status
        request.query = {"session_id": start["session_id"]}
        assert json.loads((await views.QRLoginStatusView().get(request)).body)["status"] == status
        assert (await views.QRLoginStatusView().get(request)).status == 404

async def test_internal_origin_with_empty_allowlist(login):
    data, request = login
    request.host = "10.0.0.14:8123"
    request.headers = {"Origin": "http://10.0.0.14:8123"}
    request.json.return_value = {"client_id": "http://10.0.0.14:8123/"}
    response = await views.QRLoginStartView().post(request)
    assert response.status == 200
    assert data.sessions[json.loads(response.body)["session_id"]].client_id == "http://10.0.0.14:8123/"
    data.config["allowed_client_ids"] = ["https://home.test/"]
    assert (await views.QRLoginStartView().post(request)).status == 400

async def test_missing_ha_url_returns_clean_error(login, monkeypatch):
    _, request = login
    monkeypatch.setattr(views, "resolve_client_id", Mock(side_effect=views.NoURLAvailableError))
    response = await views.QRLoginStartView().post(request)
    assert response.status == 503
    assert json.loads(response.body) == {"error": "client_id_unavailable"}


async def test_status_errors_disable_caching(login):
    _, request = login
    for query, expected in (({}, 400), ({"session_id": "missing"}, 404)):
        request.query = query
        response = await views.QRLoginStatusView().get(request)
        assert response.status == expected and response.headers["Cache-Control"] == "no-store"
