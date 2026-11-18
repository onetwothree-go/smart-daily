from datetime import date, datetime, timezone

from smart_daily_v2.models import WorkItem
from smart_daily_v2.reports.generator import group_by_member


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
