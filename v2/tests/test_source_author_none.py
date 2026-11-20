from datetime import datetime
from pathlib import Path

import httpx

from smart_daily_v2.models import LOCAL_TZ

SINCE = datetime(2026, 11, 18, 0, 0, tzinfo=LOCAL_TZ)
UNTIL = datetime(2026, 11, 19, 0, 0, tzinfo=LOCAL_TZ)


def _capture_get(monkeypatch, response: httpx.Response) -> list[dict[str, object]]:
    calls = []

    def fake_get(url, *, params, headers, timeout):
        calls.append({"url": url, "params": params, "headers": headers})
        return response

    monkeypatch.setattr(httpx, "get", fake_get)
    return calls


def _install_github_env(monkeypatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    monkeypatch.setenv("GITHUB_REPO_OWNER", "fake-owner")
    monkeypatch.setenv("GITHUB_REPO_NAME", "fake-repo")
    monkeypatch.setenv("GITHUB_API", "https://example.com")
    monkeypatch.setenv("GITHUB_BRANCH", "main")


def _install_feishu_env(monkeypatch, *, chat: bool = False) -> None:
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
    if chat:
        monkeypatch.setenv("FEISHU_CHAT_ID", "fake-chat-id")


def _github_response(url: str) -> httpx.Response:
    return httpx.Response(200, json=[], request=httpx.Request("GET", url))


def _feishu_response(url: str) -> httpx.Response:
    return httpx.Response(
        200,
        json={"code": 0, "data": {"items": [], "has_more": False, "page_token": ""}},
        request=httpx.Request("GET", url),
    )


def test_author_none_github_omits_author_key(monkeypatch, cleared_env) -> None:
    import smart_daily_v2.sources.github as gh

    _install_github_env(monkeypatch)
    calls = _capture_get(monkeypatch, _github_response("https://example.com/commits"))

    gh.GithubSource.from_env().collect(since=SINCE, until=UNTIL)

    assert "author" not in calls[0]["params"]


def test_author_none_feishu_tasks_omits_author_key(monkeypatch, cleared_env) -> None:
    import smart_daily_v2.sources.feishu_tasks as ft

    _install_feishu_env(monkeypatch)
    calls = _capture_get(monkeypatch, _feishu_response("https://example.com/tasks"))

    ft.FeishuTaskSource.from_env().collect(since=SINCE, until=UNTIL)

    assert "author" not in calls[0]["params"]
    assert "completed" in calls[0]["params"]


def test_author_none_feishu_chat_omits_author_key(monkeypatch, cleared_env) -> None:
    import smart_daily_v2.sources.feishu_chat as fc

    _install_feishu_env(monkeypatch, chat=True)
    calls = _capture_get(monkeypatch, _feishu_response("https://example.com/messages"))

    fc.FeishuChatSource.from_env().collect(since=SINCE, until=UNTIL)

    assert "author" not in calls[0]["params"]


def test_author_none_github_present_when_passed(monkeypatch, cleared_env) -> None:
    import smart_daily_v2.sources.github as gh

    _install_github_env(monkeypatch)
    calls = _capture_get(monkeypatch, _github_response("https://example.com/commits"))

    gh.GithubSource.from_env().collect(since=SINCE, until=UNTIL, author="MemberA")

    assert calls[0]["params"]["author"] == "MemberA"


def test_author_none_scope_no_real_credentials() -> None:
    import smart_daily_v2.sources.feishu_chat as fc
    import smart_daily_v2.sources.feishu_tasks as ft
    import smart_daily_v2.sources.github as gh

    guard = "if author is" + " not None"
    forbidden = (
        "gh" + "p_",
        "xox" + "b-",
        "@" + "qq.com",
        "@gmail" + ".com",
        "open.feishu" + ".cn",
    )
    for module in (gh, ft, fc):
        source = Path(module.__file__).read_text(encoding="utf-8")
        assert guard in source
        assert "待确认" in (module.__doc__ or "")
        assert "已裁定" not in source
        for value in forbidden:
            assert value not in source
