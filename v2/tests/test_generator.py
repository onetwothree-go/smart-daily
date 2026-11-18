import builtins
import socket
from datetime import date, datetime, timezone

from smart_daily_v2.models import WorkItem
from smart_daily_v2.reports.generator import format_item, group_by_member


def make_item(record_id: str, member: str, source: str, occurred_at: datetime) -> WorkItem:
    return WorkItem(
        record_id=f"https://example.com/records/{record_id}",
        source=source,
        member=member,
        kind="work",
        title=f"Sample {record_id}",
        detail="Example detail",
        occurred_at=occurred_at,
        local_day=date(2026, 11, 17),
    )


def test_group_by_member_splits_and_sorts():
    items = [
        make_item("1", "甲", "github", datetime(2026, 11, 17, 9, tzinfo=timezone.utc)),
        make_item("2", "乙", "feishu_task", datetime(2026, 11, 17, 12, tzinfo=timezone.utc)),
        make_item("3", "甲", "feishu_chat", datetime(2026, 11, 17, 11, tzinfo=timezone.utc)),
        make_item("4", "乙", "github", datetime(2026, 11, 17, 10, tzinfo=timezone.utc)),
        make_item("5", "甲", "feishu_task", datetime(2026, 11, 17, 8, tzinfo=timezone.utc)),
    ]

    groups = group_by_member(items)

    assert len(groups) == 2
    assert set(groups) == {"甲", "乙"}
    assert sum(map(len, groups.values())) == 5
    for member_items in groups.values():
        times = [item.occurred_at for item in member_items]
        assert times == sorted(times, reverse=True)


def test_same_member_from_multiple_accounts_merges():
    items = [
        make_item("1", "甲", "github", datetime(2026, 11, 17, 9, tzinfo=timezone.utc)),
        make_item("2", "甲", "feishu_task", datetime(2026, 11, 17, 10, tzinfo=timezone.utc)),
        make_item("3", "乙", "github", datetime(2026, 11, 17, 11, tzinfo=timezone.utc)),
    ]

    groups = group_by_member(items)

    assert set(groups) == {"甲", "乙"}
    assert {item.record_id for item in groups["甲"]} == {
        "https://example.com/records/1",
        "https://example.com/records/2",
    }
    assert [item.record_id for item in groups["乙"]] == ["https://example.com/records/3"]


def test_group_order_is_stable_across_runs():
    items = [
        make_item("1", "乙", "github", datetime(2026, 11, 17, 9, tzinfo=timezone.utc)),
        make_item("2", "甲", "feishu_task", datetime(2026, 11, 17, 10, tzinfo=timezone.utc)),
        make_item("3", "丙", "feishu_chat", datetime(2026, 11, 17, 11, tzinfo=timezone.utc)),
    ]

    first_order = list(group_by_member(items))
    second_order = list(group_by_member(items))

    assert first_order == second_order


def make_format_item(
    *,
    kind: str = "commit",
    title: str = "fix: 修复登录超时",
    detail: str = "3 files, +42 -8",
    occurred_at: datetime | None = None,
) -> WorkItem:
    if occurred_at is None:
        occurred_at = datetime.fromisoformat("2026-11-18T09:30:00+08:00")
    return WorkItem(
        record_id="sample-record-302",
        source="github",
        member="测试成员",
        kind=kind,
        title=title,
        detail=detail,
        occurred_at=occurred_at,
        local_day=date(2026, 11, 18),
    )


def test_format_item_layout():
    item = make_format_item()
    expected = "- [09:30] （提交）fix: 修复登录超时 —— 3 files, +42 -8"

    assert format_item(item) == expected
    assert (
        format_item(
            make_format_item(occurred_at=datetime.fromisoformat("2026-11-18T01:30:00+00:00"))
        )
        == expected
    )


def test_format_item_keeps_title_verbatim():
    title = "fix: 保留 中文 标题（包含括号）"
    item = make_format_item(title=title, detail="example detail")

    rendered = format_item(item)

    assert title in rendered
    assert rendered.index(title) < rendered.index(" —— example detail")
    assert rendered.split(" —— ", 1)[1] == "example detail"


def test_format_item_is_byte_stable():
    item = make_format_item()

    assert format_item(item).encode() == format_item(item).encode()


def test_format_item_has_no_io(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("unexpected I/O")

    monkeypatch.setattr(builtins, "open", fail)
    monkeypatch.setattr(socket, "socket", fail)

    assert format_item(make_format_item()) == (
        "- [09:30] （提交）fix: 修复登录超时 —— 3 files, +42 -8"
    )
