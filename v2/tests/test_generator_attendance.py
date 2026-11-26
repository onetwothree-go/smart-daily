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
from smart_daily_v2.reports.generator import build_personal_report, format_item

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
    report = build_personal_report("甲", [_attendance_item()], DAY)

    assert "`考勤`" in report
    assert "record_id: mock-att-001" in report


# --- 验收③护栏：_KIND_LABELS 含 attendance，既有 kind 映射不动 ---


def test_kind_labels_extended_without_touching_existing() -> None:
    from smart_daily_v2.reports.generator import _KIND_LABELS

    assert _KIND_LABELS.get("attendance") == "考勤"
    assert _KIND_LABELS.get("commit") == "提交"
    assert _KIND_LABELS.get("task") == "任务"
    assert _KIND_LABELS.get("message") == "消息"
