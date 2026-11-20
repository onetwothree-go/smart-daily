import inspect
from datetime import datetime
from pathlib import Path

import httpx
import pytest

from smart_daily_v2.identity import normalize_key
from smart_daily_v2.models import LOCAL_TZ, WorkItem, local_date
from smart_daily_v2.sources.base import SourceUnavailableError, WorkSource

CHAT_ID = "oc-placeholder-team-chat"
OTHER_CHAT_ID = "oc-placeholder-other"
SINCE = datetime(2026, 11, 18, 0, 0, tzinfo=LOCAL_TZ)
UNTIL = datetime(2026, 11, 19, 0, 0, tzinfo=LOCAL_TZ)
LONG_TEXT = (
    "甲乙丙丁同步接口字段，保留消息正文原样；This is a deliberately long placeholder text "
    "for verifying that details are never shortened, rewritten, summarized, or redacted."
)


def _msg(
    message_id: str,
    text: str,
    *,
    chat_id: str = CHAT_ID,
    chat_type: str = "group",
    sender_name: str = " MemberA ",
    create_time: str = "2026-11-18T09:00:00+08:00",
    msg_type: str = "text",
) -> dict[str, object]:
    return {
        "message_id": message_id,
        "chat_id": chat_id,
        "chat_type": chat_type,
        "sender": {"sender_name": sender_name, "sender_id": "ou-placeholder"},
        "text": text,
        "create_time": create_time,
        "msg_type": msg_type,
        "mentions": [{"id": "ou-placeholder"}],
    }


def _page(
    items: list[dict[str, object]], has_more: bool = False, page_token: str = ""
) -> dict[str, object]:
    return {
        "code": 0,
        "data": {"items": items, "has_more": has_more, "page_token": page_token},
    }


def _error_page(code: int) -> dict[str, object]:
    return {"code": code, "msg": "placeholder error"}


def _response(status: int, payload: object) -> httpx.Response:
    return httpx.Response(
        status,
        json=payload,
        request=httpx.Request("GET", "https://example.com"),
    )


def _install_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "fake-app-id")
    monkeypatch.setenv("FEISHU_APP_SECRET", "fake-app-secret")
    monkeypatch.setenv("FEISHU_CHAT_ID", CHAT_ID)
    monkeypatch.setenv("FEISHU_API", "https://example.com")


def _fake_get(
    monkeypatch: pytest.MonkeyPatch,
    pages: list[httpx.Response],
) -> list[dict[str, object]]:
    calls: list[dict[str, object]] = []

    def fake_get(url: str, *, params, headers, timeout):
        calls.append({"url": url, "params": params, "headers": headers, "timeout": timeout})
        return pages[len(calls) - 1]

    monkeypatch.setattr(httpx, "get", fake_get)
    monkeypatch.setattr(
        httpx,
        "post",
        lambda *a, **k: httpx.Response(
            200,
            json={"code": 0, "tenant_access_token": "fake-token", "expire": 7200},
            request=httpx.Request("POST", "https://example.com"),
        ),
    )
    return calls


def test_only_target_group_messages_returned(monkeypatch, cleared_env) -> None:
    import smart_daily_v2.sources.feishu_chat as fc

    _install_env(monkeypatch)
    target_messages = [
        _msg("msg-203-001", "甲群短消息"),
        _msg("msg-203-002", "乙群短消息", sender_name="MEMBERB"),
    ]
    other_group = _msg("msg-203-003", "其他群占位消息", chat_id=OTHER_CHAT_ID)
    private_with_chat_id = _msg("msg-203-004", "私聊占位消息", chat_type="p2p")
    private_without_chat_id = _msg("msg-203-005", "缺群标识的私聊占位消息")
    private_without_chat_id.pop("chat_id")
    _fake_get(
        monkeypatch,
        [
            _response(
                200,
                _page(
                    target_messages + [other_group, private_with_chat_id, private_without_chat_id]
                ),
            )
        ],
    )

    items = fc.FeishuChatSource.from_env().collect(since=SINCE, until=UNTIL)

    assert len(items) == 2
    assert all(isinstance(item, WorkItem) for item in items)
    assert [item.record_id for item in items] == [
        message["message_id"] for message in target_messages
    ]
    assert all(item.source == "feishu_chat" for item in items)
    assert all(item.kind == "message" for item in items)
    returned_ids = [item.record_id for item in items]
    assert all(
        message["message_id"] not in returned_ids
        for message in (other_group, private_with_chat_id, private_without_chat_id)
    )


def test_message_body_preserved_verbatim(monkeypatch, cleared_env) -> None:
    import smart_daily_v2.sources.feishu_chat as fc

    _install_env(monkeypatch)
    text = "  甲：原文照录！\n乙，保留标点与空格。  "
    message = _msg("msg-203-006", text)
    _fake_get(monkeypatch, [_response(200, _page([message]))])

    items = fc.FeishuChatSource.from_env().collect(since=SINCE, until=UNTIL)

    assert len(items) == 1
    item = items[0]
    assert item.record_id == message["message_id"]
    assert item.detail == text
    assert item.title == text
    assert item.occurred_at == datetime.fromisoformat(message["create_time"])
    assert item.occurred_at.tzinfo is not None
    assert item.local_day == local_date(item.occurred_at)
    assert item.member == normalize_key(message["sender"]["sender_name"])
    assert "甲：原文照录！" in item.detail
    assert "乙，保留标点与空格。" in item.detail


def test_pagination_fetches_all_target_messages(monkeypatch, cleared_env) -> None:
    import smart_daily_v2.sources.feishu_chat as fc

    _install_env(monkeypatch)
    first_page = [
        _msg("msg-203-007", "甲第一页消息"),
        _msg("msg-203-008", "乙第一页消息"),
    ]
    second_page = [_msg("msg-203-009", "丙第二页消息")]
    calls = _fake_get(
        monkeypatch,
        [
            _response(200, _page(first_page, True, "page-2-placeholder")),
            _response(200, _page(second_page)),
        ],
    )
    author = " MemberA "

    items = fc.FeishuChatSource.from_env().collect(since=SINCE, until=UNTIL, author=author)

    expected_ids = [message["message_id"] for message in first_page + second_page]
    actual_ids = [item.record_id for item in items]
    assert len(items) == 3
    assert actual_ids == expected_ids
    assert len(set(actual_ids)) == 3
    assert len(calls) == 2
    assert calls[0]["params"]["container_id"] == CHAT_ID
    assert calls[1]["params"]["container_id"] == CHAT_ID
    assert calls[1]["params"]["page_token"] == "page-2-placeholder"
    assert calls[0]["params"]["author"] == author
    assert calls[0]["params"]["start_time"] == SINCE.timestamp()
    assert calls[0]["params"]["end_time"] == UNTIL.timestamp()


def test_long_text_detail_never_rewritten_or_truncated(monkeypatch, cleared_env) -> None:
    import smart_daily_v2.sources.feishu_chat as fc

    _install_env(monkeypatch)
    _fake_get(
        monkeypatch,
        [_response(200, _page([_msg("msg-203-010", LONG_TEXT)]))],
    )

    items = fc.FeishuChatSource.from_env().collect(since=SINCE, until=UNTIL)

    assert len(LONG_TEXT) > 60
    assert len(items) == 1
    assert items[0].detail == LONG_TEXT
    assert items[0].title in (LONG_TEXT, LONG_TEXT[:60])
    assert LONG_TEXT.startswith(items[0].title)


def test_missing_chat_id_raises_without_request(monkeypatch, cleared_env) -> None:
    import smart_daily_v2.sources.feishu_chat as fc

    monkeypatch.setenv("FEISHU_APP_ID", "fake-app-id")
    monkeypatch.setenv("FEISHU_APP_SECRET", "fake-app-secret")
    monkeypatch.setenv("FEISHU_API", "https://example.com")
    calls: list[object] = []
    monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: calls.append(args))

    with pytest.raises(SourceUnavailableError):
        fc.FeishuChatSource.from_env().collect(since=SINCE, until=UNTIL)

    assert calls == []


def test_missing_app_credentials_sends_no_request(monkeypatch, cleared_env) -> None:
    import smart_daily_v2.sources.feishu_chat as fc

    calls: list[object] = []
    monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: calls.append(args))

    with pytest.raises(SourceUnavailableError):
        fc.FeishuChatSource.from_env().collect(since=SINCE, until=UNTIL)

    assert calls == []


def test_feishu_error_code_raises_source_unavailable(monkeypatch, cleared_env) -> None:
    import smart_daily_v2.sources.feishu_chat as fc

    _install_env(monkeypatch)
    _fake_get(monkeypatch, [_response(200, _error_page(230001))])

    with pytest.raises(SourceUnavailableError) as exc_info:
        fc.FeishuChatSource.from_env().collect(since=SINCE, until=UNTIL)

    assert "230001" in str(exc_info.value)
    assert "placeholder error" in str(exc_info.value)


def test_http_error_status_raises_source_unavailable(monkeypatch, cleared_env) -> None:
    import smart_daily_v2.sources.feishu_chat as fc

    _install_env(monkeypatch)
    _fake_get(monkeypatch, [_response(500, {})])

    with pytest.raises(SourceUnavailableError):
        fc.FeishuChatSource.from_env().collect(since=SINCE, until=UNTIL)


def test_collect_signature_is_keyword_only_and_satisfies_worksource(
    monkeypatch, cleared_env
) -> None:
    import smart_daily_v2.sources.feishu_chat as fc

    _install_env(monkeypatch)
    source = fc.FeishuChatSource.from_env()
    parameters = inspect.signature(fc.FeishuChatSource.collect).parameters

    assert parameters["since"].kind is inspect.Parameter.KEYWORD_ONLY
    assert parameters["until"].kind is inspect.Parameter.KEYWORD_ONLY
    with pytest.raises(TypeError):
        source.collect(SINCE, UNTIL)
    assert isinstance(source, WorkSource)
    assert source.name == "feishu_chat"


def test_scope_registration_docstring_and_no_real_credentials(monkeypatch, cleared_env) -> None:
    import smart_daily_v2.sources.feishu_chat as fc

    source = Path(fc.__file__).read_text(encoding="utf-8")

    for forbidden in (
        "ghp_",
        "xoxb-",
        "@qq.com",
        "@gmail.com",
        "open.feishu.cn",
        "from smart_daily import",
    ):
        assert forbidden not in source
    for anchor in ("待确认", "RawRecord", "归一化单点"):
        assert anchor in source
    assert "已裁定" not in source
    for registration in (
        "S3",
        "I12",
        "N7",
        "S4",
        "I8",
        "单群",
        "范围过滤",
        "截断",
        "L292",
        "L339",
        "L300",
        "L480",
        "L145",
        "MessageEntry",
        "S5",
        "create_time",
        "L162",
        "mentions",
    ):
        assert registration in source
