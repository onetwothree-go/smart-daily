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
    """团队日报所有成员 `#### 工作记录` 块的列表行（907 双块；汇总表不算条目）。"""
    return [line for member in _members(report) for line in team_lines_for(report, member)]


def _members(team: str) -> list[str]:
    return [line[4:].split(" · ", 1)[0] for line in team.splitlines() if line.startswith("### ")]


def team_lines_for(team: str, member: str) -> list[str]:
    """团队日报某成员 `#### 工作记录` 块的列表行（907 双块）。"""
    lines = team.splitlines()
    header = next(line for line in lines if line.startswith(f"### {member} · "))
    start = lines.index(header) + 1
    section: list[str] = []
    for line in lines[start:]:
        if line.startswith("### ") or line == "---":
            break
        section.append(line)
    if "#### 工作记录" not in section:
        return []
    work_start = section.index("#### 工作记录") + 1
    out: list[str] = []
    for line in section[work_start:]:
        if line.startswith("#### "):
            break
        if line.startswith("- ") and "今日无工作记录" not in line:
            out.append(line)
    return out


def expected_lines(items: list[WorkItem]) -> list[str]:
    """期望的 format_item 表格行；与团队双块列表行用 _normalize_entry 去外壳后同源比对。"""
    return [format_item(item) for item in items]


def personal_entry_lines(report: str) -> list[str]:
    """个人日报 `## 工作记录` 块的列表行（905 双块）。"""
    lines = report.splitlines()
    if "## 工作记录" not in lines:
        return []
    start = lines.index("## 工作记录") + 1
    out: list[str] = []
    for line in lines[start:]:
        if line == "---":
            break
        if line.startswith("- ") and "今日无工作记录" not in line:
            out.append(line)
    return out


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
    assert len(personal_entry_lines(outcome.personal["甲"])) == 5
    assert "**5 条工作记录**" in outcome.team


def test_no_hand_written_entries_counter_matches(format_harness):
    items = [
        make_item("commit-1", kind="commit", source="github", minute=0),
        make_item("commit-2", kind="commit", source="feishu_task", minute=1),
        make_item("commit-3", kind="commit", source="feishu_chat", minute=2),
        make_item("task-1", kind="task", source="local_git", minute=3),
        make_item("task-2", kind="task", source="mock", minute=4),
    ]

    outcome = format_harness(items)
    actual = [_normalize_entry(line) for line in entry_lines(outcome.team)]
    expected = [_normalize_entry(line) for line in expected_lines(items)]

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


def _normalize_entry(line: str) -> str:
    """去掉表格行/列表行外壳，只比对 badge 与内容是否同源。"""
    return " ".join(line.replace("|", " ").replace("- ", " ").split())


def test_personal_and_team_entry_lines_verbatim_equal(format_harness):
    outcome = format_harness()

    # 905/907 双块：个人与团队成员明细同走列表行，内容逐字一致
    for member in outcome.members:
        assert personal_entry_lines(outcome.personal[member]) == team_lines_for(
            outcome.team, member
        )


def test_both_reports_share_single_format_item_source(format_harness):
    # 905/907 双块后两路日报都走 _content_with_extra / _local_hhmm 渲染列表行；
    # format_item 表格行保留供既有 badge / 脱敏 / 对账断言复用，输出逐字不动。
    assert "_content_with_extra(" in inspect.getsource(build_personal_report)
    assert "_content_with_extra(" in inspect.getsource(build_team_report)

    items = [
        make_item("甲-1", member="甲", minute=0),
        make_item("甲-2", member="甲", minute=1, source="feishu_task"),
        make_item("乙-1", member="乙", minute=2, source="feishu_chat"),
    ]
    outcome = format_harness(items)

    for member, member_items in outcome.groups.items():
        expected = [_normalize_entry(line) for line in expected_lines(member_items)]
        assert [_normalize_entry(line) for line in team_lines_for(outcome.team, member)] == expected
        personal = [
            _normalize_entry(line) for line in personal_entry_lines(outcome.personal[member])
        ]
        assert personal == expected


def test_twenty_entry_member_fully_listed(format_harness):
    items = [make_item(f"entry-{minute}", minute=minute) for minute in range(20)]

    outcome = format_harness(items)

    assert "### 甲 · 20 条" in outcome.team
    assert len(team_lines_for(outcome.team, "甲")) == 20
    assert "**20 条工作记录**" in outcome.team
    assert len(personal_entry_lines(outcome.personal["甲"])) == 20


def test_zero_entry_member_still_listed(format_harness):
    items = [make_item("甲-1", minute=0), make_item("甲-2", minute=1)]

    outcome = format_harness(items, empty_members=("丁",))

    assert "### 甲 · 2 条" in outcome.team
    assert "### 丁 · 0 条" in outcome.team
    zero_member_section = outcome.team.split("### 丁 · 0 条", 1)[1].split("\n### ", 1)[0]
    assert "今日无工作记录" in zero_member_section
    assert outcome.members == ["丁", "甲"]
    assert "今日无工作记录" in outcome.personal["丁"]
    assert outcome.team.index("### 甲 · 2 条") < outcome.team.index("### 丁 · 0 条")


def test_fixture_reconciliation_and_record_ids_stable(format_harness, monkeypatch):
    first = format_harness()
    second = format_harness()

    assert first.record_ids == second.record_ids
    assert f"**{len(first.groups)} 位成员**" in first.team
    assert f"**{len(first.items)} 条工作记录**" in first.team
    assert Counter(_normalize_entry(line) for line in entry_lines(first.team)) == Counter(
        _normalize_entry(line) for line in expected_lines(first.items)
    )

    def fail(*args, **kwargs):
        raise AssertionError("unexpected I/O")

    monkeypatch.setattr(builtins, "open", fail)
    monkeypatch.setattr(socket, "socket", fail)
    assert format_item(first.items[0])
