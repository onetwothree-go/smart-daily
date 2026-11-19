import builtins
import inspect
import socket
from collections import Counter
from datetime import date, datetime

from smart_daily_v2.models import LOCAL_TZ, WorkItem
from smart_daily_v2.reports.generator import (
    build_personal_report,
    build_team_report,
    format_item,
)


def make_item(
    record_id: str,
    *,
    member: str = "甲",
    kind: str = "commit",
    source: str = "github",
    minute: int = 0,
    title: str | None = None,
    detail: str = "示例详情",
) -> WorkItem:
    return WorkItem(
        record_id=record_id,
        source=source,
        member=member,
        kind=kind,
        title=title if title is not None else f"示例工作条目 {record_id}",
        detail=detail,
        occurred_at=datetime(2026, 11, 18, 9, minute, tzinfo=LOCAL_TZ),
        local_day=date(2026, 11, 18),
    )


def entry_lines(report: str) -> list[str]:
    return [line for line in report.splitlines() if line.startswith("- [")]


def team_lines_for(team: str, member: str) -> list[str]:
    lines = []
    in_member_section = False
    section_prefix = f"## {member}（"
    for line in team.splitlines():
        if line.startswith("## "):
            if in_member_section:
                break
            in_member_section = line.startswith(section_prefix)
        elif in_member_section and line.startswith("- ["):
            lines.append(line)
    return lines


def expected_lines(items: list[WorkItem]) -> list[str]:
    return [format_item(item) for item in items]


def test_three_commits_two_tasks_count_is_five(format_harness):
    items = [
        make_item("commit-1", kind="commit", source="github", minute=0),
        make_item("commit-2", kind="commit", source="feishu_task", minute=1),
        make_item("commit-3", kind="commit", source="feishu_chat", minute=2),
        make_item("task-1", kind="task", source="local_git", minute=3),
        make_item("task-2", kind="task", source="mock", minute=4),
    ]

    outcome = format_harness(items)

    assert len(entry_lines(outcome.team)) == 5
    assert len(entry_lines(outcome.personal["甲"])) == 5
    assert "条目 5 条" in outcome.team.splitlines()[0]


def test_no_hand_written_entries_counter_matches(format_harness):
    items = [
        make_item("commit-1", kind="commit", source="github", minute=0),
        make_item("commit-2", kind="commit", source="feishu_task", minute=1),
        make_item("commit-3", kind="commit", source="feishu_chat", minute=2),
        make_item("task-1", kind="task", source="local_git", minute=3),
        make_item("task-2", kind="task", source="mock", minute=4),
    ]

    outcome = format_harness(items)
    actual = entry_lines(outcome.team)
    expected = expected_lines(items)

    assert Counter(actual) == Counter(expected)
    assert len(actual) == 5
    assert all(line in expected for line in actual)


def test_same_action_across_three_sources_keeps_three_lines(format_harness):
    items = [
        make_item(
            "source-github",
            source="github",
            minute=0,
            title="同一动作",
            detail="示例详情",
        ),
        make_item(
            "source-task",
            source="feishu_task",
            minute=0,
            title="同一动作",
            detail="示例详情",
        ),
        make_item(
            "source-chat",
            source="feishu_chat",
            minute=0,
            title="同一动作",
            detail="示例详情",
        ),
    ]

    outcome = format_harness(items)
    matching_lines = [line for line in entry_lines(outcome.team) if "同一动作" in line]
    record_ids = [item.record_id for item in outcome.items]

    assert len(matching_lines) == 3
    assert len(set(record_ids)) == 3
    assert outcome.record_ids == tuple(record_ids)


def test_personal_and_team_entry_lines_verbatim_equal(format_harness):
    outcome = format_harness()

    for member in outcome.members:
        assert entry_lines(outcome.personal[member]) == team_lines_for(outcome.team, member)


def test_both_reports_share_single_format_item_source(format_harness):
    assert "format_item(" in inspect.getsource(build_personal_report)
    assert "format_item(" in inspect.getsource(build_team_report)

    items = [
        make_item("甲-1", member="甲", minute=0),
        make_item("甲-2", member="甲", minute=1, source="feishu_task"),
        make_item("乙-1", member="乙", minute=2, source="feishu_chat"),
    ]
    outcome = format_harness(items)

    for member, member_items in outcome.groups.items():
        expected = expected_lines(member_items)
        assert entry_lines(outcome.personal[member]) == expected
        assert team_lines_for(outcome.team, member) == expected


def test_twenty_entry_member_fully_listed(format_harness):
    items = [make_item(f"entry-{minute}", minute=minute) for minute in range(20)]

    outcome = format_harness(items)

    assert "## 甲（20 条）" in outcome.team
    assert len(team_lines_for(outcome.team, "甲")) == 20
    assert "条目 20 条" in outcome.team.splitlines()[0]
    assert len(entry_lines(outcome.personal["甲"])) == 20


def test_zero_entry_member_still_listed(format_harness):
    items = [make_item("甲-1", minute=0), make_item("甲-2", minute=1)]

    outcome = format_harness(items, empty_members=("丁",))

    assert "## 甲（2 条）" in outcome.team
    assert "## 丁（0 条）" in outcome.team
    zero_member_section = outcome.team.split("## 丁（0 条）", 1)[1].split("\n## ", 1)[0]
    assert "今日无工作记录" in zero_member_section
    assert outcome.members == ["丁", "甲"]
    assert "今日无工作记录" in outcome.personal["丁"]
    assert outcome.team.index("## 甲（2 条）") < outcome.team.index("## 丁（0 条）")


def test_fixture_reconciliation_and_record_ids_stable(format_harness, monkeypatch):
    first = format_harness()
    second = format_harness()

    assert first.record_ids == second.record_ids
    assert f"成员 {len(first.groups)} 人 · 条目 {len(first.items)} 条" in first.team.splitlines()[0]
    assert Counter(entry_lines(first.team)) == Counter(expected_lines(first.items))

    def fail(*args, **kwargs):
        raise AssertionError("unexpected I/O")

    monkeypatch.setattr(builtins, "open", fail)
    monkeypatch.setattr(socket, "socket", fail)
    assert format_item(first.items[0])
