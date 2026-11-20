from datetime import datetime
from pathlib import Path

import httpx
import pytest

from smart_daily_v2.models import LOCAL_TZ
from smart_daily_v2.sources.base import SourceUnavailableError

SINCE = datetime(2026, 11, 18, 0, 0, tzinfo=LOCAL_TZ)
UNTIL = datetime(2026, 11, 19, 0, 0, tzinfo=LOCAL_TZ)


def _response(status: int, payload: object) -> httpx.Response:
    return httpx.Response(
        status,
        json=payload,
        request=httpx.Request("POST", "https://example.com"),
    )


def _install_env(monkeypatch: pytest.MonkeyPatch, *, chat: bool = False) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "fake-app-id")
    monkeypatch.setenv("FEISHU_APP_SECRET", "fake-app-secret")
    monkeypatch.setenv("FEISHU_API", "https://example.com/open-apis")
    if chat:
        monkeypatch.setenv("FEISHU_CHAT_ID", "fake-chat-id")


def test_feishu_auth_token_endpoint_and_body(monkeypatch, cleared_env) -> None:
    import smart_daily_v2.sources.feishu_tasks as ft

    calls = []

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        return _response(
            200,
            {"code": 0, "tenant_access_token": "fake-token", "expire": 7200},
        )

    monkeypatch.setattr(httpx, "post", fake_post)

    token = ft._fetch_tenant_access_token(
        "fake-app-id", "fake-app-secret", "https://example.com/open-apis"
    )

    assert calls[0][0].endswith("/auth/v3/tenant_access_token/internal")
    assert calls[0][1]["json"] == {
        "app_id": "fake-app-id",
        "app_secret": "fake-app-secret",
    }
    assert token == "fake-token"


def test_feishu_auth_token_error_code_raises(monkeypatch, cleared_env) -> None:
    import smart_daily_v2.sources.feishu_tasks as ft

    monkeypatch.setattr(
        httpx,
        "post",
        lambda *args, **kwargs: _response(200, {"code": 99991661, "msg": "no token"}),
    )

    with pytest.raises(SourceUnavailableError):
        ft._fetch_tenant_access_token(
            "fake-app-id", "fake-app-secret", "https://example.com/open-apis"
        )


def test_feishu_auth_token_http_error_raises(monkeypatch, cleared_env) -> None:
    import smart_daily_v2.sources.feishu_tasks as ft

    def raise_connect_error(*args, **kwargs):
        request = httpx.Request("POST", "https://example.com")
        raise httpx.ConnectError("connection failed", request=request)

    monkeypatch.setattr(httpx, "post", raise_connect_error)

    with pytest.raises(SourceUnavailableError):
        ft._fetch_tenant_access_token(
            "fake-app-id", "fake-app-secret", "https://example.com/open-apis"
        )


def test_feishu_auth_collect_adds_bearer_tasks(monkeypatch, cleared_env) -> None:
    import smart_daily_v2.sources.feishu_tasks as ft

    _install_env(monkeypatch)
    monkeypatch.setattr(
        httpx,
        "post",
        lambda *args, **kwargs: _response(
            200,
            {"code": 0, "tenant_access_token": "fake-token", "expire": 7200},
        ),
    )
    calls = []

    def fake_get(url, *, params, headers, timeout):
        calls.append({"url": url, "params": params, "headers": headers})
        return httpx.Response(
            200,
            json={"code": 0, "data": {"items": [], "has_more": False, "page_token": ""}},
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(httpx, "get", fake_get)

    ft.FeishuTaskSource.from_env().collect(since=SINCE, until=UNTIL)

    headers = calls[0]["headers"]
    assert headers["Authorization"] == "Bearer fake-token"
    assert headers["X-Application-Id"] == "fake-app-id"
    assert headers["X-Application-Secret"] == "fake-app-secret"


def test_feishu_auth_collect_adds_bearer_chat(monkeypatch, cleared_env) -> None:
    import smart_daily_v2.sources.feishu_chat as fc

    _install_env(monkeypatch, chat=True)
    monkeypatch.setattr(
        httpx,
        "post",
        lambda *args, **kwargs: _response(
            200,
            {"code": 0, "tenant_access_token": "fake-token", "expire": 7200},
        ),
    )
    calls = []

    def fake_get(url, *, params, headers, timeout):
        calls.append({"url": url, "params": params, "headers": headers})
        return httpx.Response(
            200,
            json={"code": 0, "data": {"items": [], "has_more": False, "page_token": ""}},
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(httpx, "get", fake_get)

    fc.FeishuChatSource.from_env().collect(since=SINCE, until=UNTIL)

    headers = calls[0]["headers"]
    assert headers["Authorization"] == "Bearer fake-token"
    assert headers["X-Application-Id"] == "fake-app-id"
    assert headers["X-Application-Secret"] == "fake-app-secret"


def test_feishu_auth_scope_and_no_real_credentials() -> None:
    import smart_daily_v2.sources.feishu_chat as fc
    import smart_daily_v2.sources.feishu_tasks as ft

    for module in (ft, fc):
        source = Path(module.__file__).read_text(encoding="utf-8")
        assert "_fetch_tenant_access_token" in source
        assert "Authorization" in source
        assert "待确认" in (module.__doc__ or "")
        for forbidden in (
            "gh" + "p_",
            "xox" + "b-",
            "@" + "qq.com",
            "@gmail" + ".com",
            "open.feishu" + ".cn",
        ):
            assert forbidden not in source
        assert "已裁定" not in source
