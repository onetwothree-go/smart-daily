import builtins
import re
import socket
from datetime import date, datetime, timezone

from smart_daily_v2.models import WorkItem
from smart_daily_v2.reports.generator import (
    build_personal_report,
    build_team_report,
    format_item,
    group_by_member,
)


def is_entry_line(line: str) -> bool:
    """识别表格数据行（团队日报用，排除表头与分隔行，如 | 09:30 | 提交 | ... |）。"""
    return bool(re.match(r"^\| \d{2}:\d{2} \|", line))


def _normalize_entry(line: str) -> str:
    """去掉表格行/列表行的外壳与空白，只比对 badge 与内容是否同源。"""
    return " ".join(line.replace("|", " ").replace("- ", " ").split())


def work_lines(report: str) -> list[str]:
    """个人日报 `## 工作记录` 块的列表行（TK-V2-905 双块呈现）。"""
    lines = report.splitlines()
    if "## 工作记录" not in lines:
        return []
    start = lines.index("## 工作记录") + 1
    out: list[str] = []
    for line in lines[start:]:
        if line == "---":
            break
        if line.startswith("- "):
            out.append(line)
    return out


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
    expected = "| 09:30 | `fix` | 修复登录超时 —— 3 files, +42 -8 |"

    assert format_item(item) == expected
    assert (
        format_item(
            make_format_item(occurred_at=datetime.fromisoformat("2026-11-18T01:30:00+00:00"))
        )
        == expected
    )


def test_format_item_keeps_title_body_verbatim():
    title = "fix: 保留 中文 标题（包含括号）"
    body = "保留 中文 标题（包含括号）"
    item = make_format_item(title=title, detail="example detail")

    rendered = format_item(item)

    assert body in rendered
    assert rendered.index(body) < rendered.index(" —— example detail")
    assert rendered.split(" —— ", 1)[1].strip(" |") == "example detail"


def test_format_item_does_not_repeat_identical_detail():
    item = make_format_item(title="feat: 双分支去重", detail="feat: 双分支去重")

    assert format_item(item) == "| 09:30 | `feat` | 双分支去重 |"


def test_format_item_flattens_multiline_detail_and_escapes_pipe():
    item = make_format_item(
        title="docs: 补记录",
        detail="docs: 补记录\n\n含 | 竖线\n第二行正文",
    )

    rendered = format_item(item)

    assert "\n" not in rendered
    assert "\\|" in rendered
    assert rendered == "| 09:30 | `docs` | 补记录 —— 含 \\| 竖线 第二行正文 |"


def test_format_item_falls_back_to_kind_label():
    item = make_format_item(title="Merge dev into main: 纳入全部工作", detail="")

    assert format_item(item) == "| 09:30 | `提交` | Merge dev into main: 纳入全部工作 |"


def test_format_item_is_byte_stable():
    item = make_format_item()

    assert format_item(item).encode() == format_item(item).encode()


def test_format_item_has_no_io(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("unexpected I/O")

    monkeypatch.setattr(builtins, "open", fail)
    monkeypatch.setattr(socket, "socket", fail)

    assert format_item(make_format_item()) == (
        "| 09:30 | `fix` | 修复登录超时 —— 3 files, +42 -8 |"
    )


def make_personal_report_items() -> list[WorkItem]:
    day = date(2026, 11, 18)
    return [
        WorkItem(
            record_id=f"record-{index}",
            source="github" if index < 3 else "feishu_task",
            member="甲",
            kind="commit" if index < 3 else "task",
            title=f"工作条目 {index}",
            detail=f"详情 {index}",
            occurred_at=datetime(2026, 11, 18, 9 + index, 30),
            local_day=day,
        )
        for index in range(5)
    ]


def test_personal_report_counts_all_items():
    items = make_personal_report_items()

    report = build_personal_report("甲", items, date(2026, 11, 18))
    item_lines = work_lines(report)

    assert len(item_lines) == 5
    # 双块呈现：个人日报列表行 = `- HH:MM `badge` 内容`，团队日报仍走 format_item 表格行
    assert item_lines == [
        "- 09:30 `提交` 工作条目 0 —— 详情 0",
        "- 10:30 `提交` 工作条目 1 —— 详情 1",
        "- 11:30 `提交` 工作条目 2 —— 详情 2",
        "- 12:30 `任务` 工作条目 3 —— 详情 3",
        "- 13:30 `任务` 工作条目 4 —— 详情 4",
    ]


def test_personal_report_empty_day():
    report = build_personal_report("甲", [], date(2026, 11, 18))

    assert report
    assert "今日无工作记录" in report
    assert not any(is_entry_line(line) for line in report.splitlines())


def test_personal_report_is_pure(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("unexpected I/O")

    monkeypatch.setattr(builtins, "open", fail)
    monkeypatch.setattr(socket, "socket", fail)

    report = build_personal_report("甲", make_personal_report_items(), date(2026, 11, 18))

    assert report


def make_team_item(record_id: str, member: str, minute: int) -> WorkItem:
    day = date(2026, 11, 18)
    return WorkItem(
        record_id=record_id,
        source="github",
        member=member,
        kind="commit",
        title=f"工作条目 {record_id}",
        detail=f"详情 {record_id}",
        occurred_at=datetime(2026, 11, 18, 9, minute, tzinfo=timezone.utc),
        local_day=day,
    )


def test_team_report_lists_all_members_without_truncation():
    day = date(2026, 11, 18)
    groups = {
        "甲": [make_team_item(f"甲-{index}", "甲", index) for index in range(20)],
        "乙": [make_team_item(f"乙-{index}", "乙", index) for index in range(2)],
        "丙": [make_team_item("丙-0", "丙", 0)],
        "丁": [],
    }

    report = build_team_report(groups, day)
    lines = report.splitlines()
    section_headers = [line for line in lines if line.startswith("### ")]
    entry_lines = [line for line in lines if is_entry_line(line)]

    assert lines[0] == "# 团队日报 · 2026-11-18"
    assert "**4 位成员**" in report
    assert all(f"### {member} · {len(items)} 条" in report for member, items in groups.items())
    assert len(entry_lines) == sum(map(len, groups.values())) == 23
    assert section_headers == [
        "### 甲 · 20 条",
        "### 乙 · 2 条",
        "### 丙 · 1 条",
        "### 丁 · 0 条",
    ]
    assert "**23 条工作记录**" in report


def test_team_report_entry_lines_match_personal():
    day = date(2026, 11, 18)
    groups = {
        "甲": [make_team_item("甲-0", "甲", 0), make_team_item("甲-1", "甲", 1)],
        "乙": [make_team_item("乙-0", "乙", 2)],
    }

    report = build_team_report(groups, day)
    report_lines = report.splitlines()
    team_entry_lines = {member: [] for member in groups}
    current_member = None
    for line in report_lines:
        if line.startswith("### "):
            current_member = line[4:].split(" · ", 1)[0]
        elif is_entry_line(line):
            team_entry_lines[current_member].append(line)

    for member, items in groups.items():
        personal_report = build_personal_report(member, items, day)
        personal_lines = work_lines(personal_report)
        # 905 双块：个人走列表行、团队仍走 format_item 表格行，去外壳后内容同源
        assert len(personal_lines) == len(team_entry_lines[member])
        for personal_line, team_line in zip(personal_lines, team_entry_lines[member], strict=True):
            assert _normalize_entry(personal_line) == _normalize_entry(team_line)


def test_team_report_all_empty_day():
    report = build_team_report({"甲": [], "乙": []}, date(2026, 11, 18))

    assert report
    assert "今日无工作记录" in report
    assert not any(is_entry_line(line) for line in report.splitlines())
