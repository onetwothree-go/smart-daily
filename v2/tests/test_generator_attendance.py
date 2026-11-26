"""TK-V2-903 日报 badge 映射与 301–304 影响核查红测试（第 4 周变更涟漪）。

契约：design 0.7-diff 0.4 §5-1 / §5-2 / §8-A、tasks TK-V2-903。
- kind="attendance" → badge「考勤」（§5-2：即使标题含 conventional 前缀也强制中文徽标）
- 考勤条目按 v2 现行 Markdown 表格行渲染（format_item 同源，不单开列表行）
- 无考勤数据成员不出现考勤条目（C8 语义不变）
- 301–304 逐条影响核查结论见 v2/docs/于悦-第4周-301至304影响核查.md（文档，不在代码内）

红→绿：本文件先于实现落地，pytest 应红；实现后应绿。
"""

from datetime import date, datetime

from smart_daily_v2.models import WorkItem
from smart_daily_v2.reports.generator import (
    build_personal_report,
    build_team_report,
    format_item,
    group_by_member,
)

DAY = date(2026, 11, 18)
OCCURRED = datetime.fromisoformat("2026-11-18T09:05:00+08:00")


def _attendance_item(
    *,
    title: str = "考勤：正常",
    detail: str = "出勤状态：正常\nrecord_id: mock-att-001",
) -> WorkItem:
    return WorkItem(
        record_id="mock-att-001",
        source="feishu_attendance",
        member="甲",
        kind="attendance",
        title=title,
        detail=detail,
        occurred_at=OCCURRED,
        local_day=DAY,
    )


# --- 验收①：badge 映射 + 现行表格行 ---


def test_attendance_badge_is_chinese() -> None:
    assert format_item(_attendance_item()) == (
        "| 09:05 | `考勤` | 已打卡 —— record_id: mock-att-001 |"
    )


def test_attendance_status_not_exposed_in_report() -> None:
    """早退/迟到等考勤判定不进日报正文；record_id 保留供 C11 对账。"""
    rendered = format_item(
        _attendance_item(title="考勤：早退", detail="出勤状态：早退\nrecord_id: mock-att-001")
    )

    assert "早退" not in rendered
    assert "迟到" not in rendered
    assert "出勤状态" not in rendered
    assert "已打卡" in rendered
    assert "record_id: mock-att-001" in rendered


def test_attendance_badge_forced_over_conventional_prefix() -> None:
    """design §5-2：标题含 feat: 时仍强制「考勤」，不得显示英文徽标。"""
    rendered = format_item(_attendance_item(title="feat: 补打卡记录"))

    assert "`考勤`" in rendered
    assert "`feat`" not in rendered


def test_attendance_uses_same_markdown_table_row() -> None:
    rendered = format_item(_attendance_item())

    assert rendered.startswith("| 09:05 |")
    assert rendered.endswith(" |")
    assert rendered.count("|") == 4


# --- 验收④：无考勤数据成员不出现考勤条目 ---


def test_member_without_attendance_has_no_attendance_row() -> None:
    report = build_personal_report("乙", [], DAY)

    assert "今日无工作记录" in report
    assert "考勤" not in report
    assert "attendance" not in report


def test_attendance_in_report_when_present() -> None:
    """个人日报：考勤进 `## 今日考勤` 独立块，正文「已打卡」+ record_id（905 双块）。"""
    report = build_personal_report("甲", [_attendance_item()], DAY)

    assert "## 今日考勤" in report
    assert "已打卡" in report
    assert "record_id: mock-att-001" in report


# --- 验收③护栏：_KIND_LABELS 含 attendance，既有 kind 映射不动 ---


def test_kind_labels_extended_without_touching_existing() -> None:
    from smart_daily_v2.reports.generator import _KIND_LABELS

    assert _KIND_LABELS.get("attendance") == "考勤"
    assert _KIND_LABELS.get("commit") == "提交"
    assert _KIND_LABELS.get("task") == "任务"
    assert _KIND_LABELS.get("message") == "消息"


# --- 考勤置顶护栏：考勤不得夹在工作记录中间（用户 2026-11-26 截图反馈） ---


def _work_item(record_id: str, occurred_at: datetime) -> WorkItem:
    return WorkItem(
        record_id=record_id,
        source="github",
        member="甲",
        kind="commit",
        title=f"feat: 工作 {record_id}",
        detail=f"工作 {record_id}",
        occurred_at=occurred_at,
        local_day=DAY,
    )


def test_group_by_member_puts_attendance_first() -> None:
    """group_by_member 排序后，考勤须排在该成员最前，其余按时间倒序。"""
    late_work = _work_item("late", datetime.fromisoformat("2026-11-18T20:00:00+08:00"))
    attend = _attendance_item()  # 09:05，时间处于中间
    early_work = _work_item("early", datetime.fromisoformat("2026-11-18T08:00:00+08:00"))

    groups = group_by_member([late_work, attend, early_work])

    assert groups["甲"][0].kind == "attendance"


def _is_work_line(line: str) -> bool:
    return "工作 late" in line or "工作 early" in line


def test_personal_report_attendance_not_in_middle() -> None:
    """个人日报：考勤独占 `## 今日考勤` 块，整体位于 `## 工作记录` 块之前（905 双块）。"""
    late_work = _work_item("late", datetime.fromisoformat("2026-11-18T20:00:00+08:00"))
    attend = _attendance_item()  # 09:05，时间处于中间
    early_work = _work_item("early", datetime.fromisoformat("2026-11-18T08:00:00+08:00"))

    groups = group_by_member([late_work, attend, early_work])
    report = build_personal_report("甲", groups["甲"], DAY)

    attendance_block = _personal_block(report, "## 今日考勤")
    work_block = _personal_block(report, "## 工作记录")

    assert attendance_block, "应有一条考勤行"
    assert work_block, "应有工作记录行"
    assert "已打卡" in attendance_block[0]
    assert report.index("## 今日考勤") < report.index("## 工作记录")


def test_team_report_attendance_not_in_middle() -> None:
    """团队日报里每个成员块的考勤行同样不得夹在工作记录中间，须置顶。"""
    late_work = _work_item("late", datetime.fromisoformat("2026-11-18T20:00:00+08:00"))
    attend = _attendance_item()
    early_work = _work_item("early", datetime.fromisoformat("2026-11-18T08:00:00+08:00"))

    groups = group_by_member([late_work, attend, early_work])
    report = build_team_report(groups, DAY)
    lines = report.splitlines()
    attendance_positions = [i for i, line in enumerate(lines) if "`考勤`" in line]
    work_positions = [i for i, line in enumerate(lines) if _is_work_line(line)]

    assert attendance_positions, "应有一条考勤行"
    assert work_positions, "应有工作记录行"
    assert attendance_positions[0] < min(work_positions), "考勤行须在该成员工作记录之前"


# --- TK-V2-905 双块呈现红测试（design 0.7-diff 0.6 §5-1 / proposal 0.5-diff 0.6 / issue #24）---


def _personal_block(body: str, heading: str) -> list[str]:
    """取个人日报某个 `## ` 块内的非空行（截至下一个 `## ` 或 `---`）。"""
    lines = body.splitlines()
    if heading not in lines:
        return []
    start = lines.index(heading) + 1
    out: list[str] = []
    for line in lines[start:]:
        if line.startswith("## ") or line == "---":
            break
        if line.strip():
            out.append(line)
    return out


def test_personal_report_uses_two_independent_blocks() -> None:
    """个人日报为 `## 今日考勤` + `## 工作记录` 两块独立呈现，考勤在前，无表格分隔行。"""
    work = _work_item("w", datetime.fromisoformat("2026-11-18T20:00:00+08:00"))
    body = build_personal_report("甲", [work, _attendance_item()], DAY)

    assert "## 今日考勤" in body
    assert "## 工作记录" in body
    assert body.index("## 今日考勤") < body.index("## 工作记录")
    assert "| :---" not in body


def test_personal_attendance_block_line_is_redacted() -> None:
    """考勤块每行 `- HH:MM 已打卡 —— record_id: XXX`；早退/迟到状态不渲染。"""
    body = build_personal_report("甲", [_attendance_item(title="考勤：早退")], DAY)

    assert _personal_block(body, "## 今日考勤") == ["- 09:05 已打卡 —— record_id: mock-att-001"]
    assert "早退" not in body


def test_personal_work_block_is_list_not_table() -> None:
    """工作记录块用 `- HH:MM `badge` 内容` 列表，不出现表格数据行。"""
    work = _work_item("w", datetime.fromisoformat("2026-11-18T20:00:00+08:00"))
    body = build_personal_report("甲", [work], DAY)

    block = _personal_block(body, "## 工作记录")
    assert len(block) == 1
    assert block[0].startswith("- 20:00 `feat` ")


def test_personal_report_without_attendance_has_no_attendance_block() -> None:
    """无记录成员不出现考勤块（906②），仍保留 C8「今日无工作记录」。"""
    body = build_personal_report("甲", [], DAY)

    assert "## 今日考勤" not in body
    assert "今日无工作记录" in body
