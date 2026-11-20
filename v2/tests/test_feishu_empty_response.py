from datetime import datetime
from pathlib import Path

import httpx

from smart_daily_v2.models import LOCAL_TZ

SINCE = datetime(2026, 11, 18, 0, 0, tzinfo=LOCAL_TZ)
UNTIL = datetime(2026, 11, 19, 0, 0, tzinfo=LOCAL_TZ)


def test_feishu_empty_tasks_data_without_items_key(monkeypatch, cleared_env) -> None:
    import smart_daily_v2.sources.feishu_tasks as ft

    monkeypatch.setenv("FEISHU_APP_ID", "fake-app-id")
    monkeypatch.setenv("FEISHU_APP_SECRET", "fake-app-secret")
    monkeypatch.setenv("FEISHU_API", "https://example.com")
    monkeypatch.setattr(
        httpx,
        "post",
        lambda *a, **k: httpx.Response(
            200,
            json={"code": 0, "tenant_access_token": "fake-token", "expire": 7200},
            request=httpx.Request("POST", "https://example.com"),
        ),
    )

    def fake_get(url, **kwargs):
        return httpx.Response(
            200,
            json={"code": 0, "data": {"has_more": False, "page_token": ""}},
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(httpx, "get", fake_get)

    items = ft.FeishuTaskSource.from_env().collect(since=SINCE, until=UNTIL)

    assert items == []


def test_feishu_empty_chat_data_without_items_key(monkeypatch, cleared_env) -> None:
    import smart_daily_v2.sources.feishu_chat as fc

    monkeypatch.setenv("FEISHU_APP_ID", "fake-app-id")
    monkeypatch.setenv("FEISHU_APP_SECRET", "fake-app-secret")
    monkeypatch.setenv("FEISHU_API", "https://example.com")
    monkeypatch.setenv("FEISHU_CHAT_ID", "fake-chat-id")
    monkeypatch.setattr(
        httpx,
        "post",
        lambda *a, **k: httpx.Response(
            200,
            json={"code": 0, "tenant_access_token": "fake-token", "expire": 7200},
            request=httpx.Request("POST", "https://example.com"),
        ),
    )

    def fake_get(url, **kwargs):
        return httpx.Response(
            200,
            json={"code": 0, "data": {"has_more": False, "page_token": ""}},
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(httpx, "get", fake_get)

    items = fc.FeishuChatSource.from_env().collect(since=SINCE, until=UNTIL)

    assert items == []


def test_feishu_empty_scope_uses_safe_get() -> None:
    import smart_daily_v2.sources.feishu_chat as fc
    import smart_daily_v2.sources.feishu_tasks as ft

    safe_access = ".get(" + '"items"' + ", [])"
    forbidden = (
        "gh" + "p_",
        "xox" + "b-",
        "@" + "qq.com",
        "@gmail" + ".com",
        "open.feishu" + ".cn",
    )
    for module in (ft, fc):
        source = Path(module.__file__).read_text(encoding="utf-8")
        assert safe_access in source
        assert "待确认" in (module.__doc__ or "")
        assert "已裁定" not in source
        for value in forbidden:
            assert value not in source


def test_feishu_empty_normal_items_still_parsed(monkeypatch, cleared_env) -> None:
    import smart_daily_v2.sources.feishu_tasks as ft

    monkeypatch.setenv("FEISHU_APP_ID", "fake-app-id")
    monkeypatch.setenv("FEISHU_APP_SECRET", "fake-app-secret")
    monkeypatch.setenv("FEISHU_API", "https://example.com")
    monkeypatch.setattr(
        httpx,
        "post",
        lambda *a, **k: httpx.Response(
            200,
            json={"code": 0, "tenant_access_token": "fake-token", "expire": 7200},
            request=httpx.Request("POST", "https://example.com"),
        ),
    )
    task = {
        "task_id": "t1",
        "summary": "s",
        "description": "d",
        "creator_name": "甲",
        "created_at": "2026-11-18T10:00:00+08:00",
        "completed_at": "",
        "completed": False,
    }

    def fake_get(url, **kwargs):
        return httpx.Response(
            200,
            json={
                "code": 0,
                "data": {"items": [task], "has_more": False, "page_token": ""},
            },
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(httpx, "get", fake_get)

    items = ft.FeishuTaskSource.from_env().collect(since=SINCE, until=UNTIL)

    assert len(items) == 1
