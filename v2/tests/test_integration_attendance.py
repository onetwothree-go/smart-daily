"""TK-V2-904 · 考勤集成用例（C11）骨架 · 第 4 周测试工程师杨佳莹。

交付物：tasks.md §8 TK-V2-904 指定文件。依据 design 0.7-diff 0.4 §3-5（record_id 内嵌
detail）、§4-2（occurred_at 口径）、§5-2（badge「考勤」）、proposal 0.5-diff 0.2 C11。

状态：骨架已建立，任务状态仍 ⬜ 未勾销。P8 串行，依赖 TK-V2-902（CLI 第五源）与
TK-V2-903（badge 映射 / 生成层接入），二者未落地时整文件 skip，避免伪造通过、
避免把全量门禁跑红。解除条件：902/903 合入后 SOURCE_TYPES 含 feishu_attendance
且 _KIND_LABELS 含 attendance，本文件自动启用（无需手改 skip）。

计数口径：design §8-B#1 / proposal §7-1 未裁决前，本文件只断言「考勤条目自身
1:1 与逐字格式」，不写 C1 计数分母断言。裁决并入 C1 后须另补断言并同步修订
C1 判据（另走评审），不得在此静默扩充。

边界：AI 辅助起草骨架，未代签、未代勾任务状态、未改 design/proposal/tasks。

2026-11-26 修订登记（于悦请求代修，杨佳莹本人找 user_id 无暇）：902/903 合入后本文件
自动启用，暴露两处用例构造问题——① test_904_02 把条目直传 build_personal_report，
漏了 group_by_member 成员过滤；② test_904_05 原按验收⑤原文同传 --mock 与
--source feishu_attendance（CLI 互斥组不接受），且断言 stdout 含考勤正文，但 main()
按退出码契约只落库不打印正文。本次只修这两条用例构造，使其验证真实的验收意图
（成员隔离 / exit 0 + 落库日报含考勤行）；未代杨佳莹签认、未勾销 904、未改验收标准
原文（验收⑤字面与 CLI 契约的冲突另走组内对齐）。
"""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

import pytest

from smart_daily_v2.cli import SOURCE_TYPES
from smart_daily_v2.models import LOCAL_TZ, WorkItem, local_date
from smart_daily_v2.reports import generator
from smart_daily_v2.reports.generator import (
    build_personal_report,
    build_team_report,
    group_by_member,
)

DAY = date(2026, 11, 25)
_KIND_LABELS = getattr(generator, "_KIND_LABELS", {})
ATTENDANCE_READY = "feishu_attendance" in SOURCE_TYPES and "attendance" in _KIND_LABELS
pytestmark = pytest.mark.skipif(
    not ATTENDANCE_READY,
    reason="依赖 TK-V2-902（CLI 第五源）与 TK-V2-903（badge 映射/生成层接入）；"
    "落地后 SOURCE_TYPES 与 _KIND_LABELS 齐备即自动启用",
)


def make_attendance_item(
    record_id: str, member: str, at: datetime, status: str = "正常出勤"
) -> WorkItem:
    """构造考勤条目：出勤状态入 title，record_id 内嵌 detail（design §3-5 方案①）。"""
    return WorkItem(
        record_id=record_id,
        source="feishu_attendance",
        member=member,
        kind="attendance",
        title=status,
        detail=f"{status}（record_id={record_id}）",
        occurred_at=at,
        local_day=local_date(at),
    )


def attendance_rows(body: str) -> list[str]:
    """团队日报的考勤表格行（C11③ 团队分组表格行原样保留）。"""
    return [line for line in body.splitlines() if "`考勤`" in line and line.startswith("|")]


def personal_attendance_lines(body: str) -> list[str]:
    """个人日报 `## 今日考勤` 块的列表行（S11 乙案 / TK-V2-905 / 906①）。"""
    lines = body.splitlines()
    if "## 今日考勤" not in lines:
        return []
    start = lines.index("## 今日考勤") + 1
    out: list[str] = []
    for line in lines[start:]:
        if line.startswith("## ") or line == "---":
            break
        if line.strip():
            out.append(line)
    return out


def test_904_01_recorded_member_has_exactly_one_attendance_row():
    """个人日报考勤行：906① 双块断言取代原表格行逐字断言（团队日报断言保持 904 原样）。"""
    item = make_attendance_item("att-001", "甲", datetime(2026, 11, 25, 9, 0, tzinfo=LOCAL_TZ))

    body = build_personal_report("甲", [item], DAY)
    lines = personal_attendance_lines(body)

    assert len(lines) == 1
    assert lines[0] == "- 09:00 已打卡 —— record_id=att-001"
    assert "att-001" in lines[0]


def test_904_02_member_without_attendance_has_no_row():
    items = [make_attendance_item("att-001", "甲", datetime(2026, 11, 25, 9, 0, tzinfo=LOCAL_TZ))]

    # build_personal_report 只渲染传入条目、不按成员过滤；成员过滤在 group_by_member 层。
    groups = group_by_member(items)
    body = build_personal_report("乙", groups.get("乙", []), DAY)

    assert personal_attendance_lines(body) == []
    assert "## 今日考勤" not in body


def test_904_03_team_report_groups_all_attendance_items():
    items = [
        make_attendance_item("att-001", "甲", datetime(2026, 11, 25, 9, 0, tzinfo=LOCAL_TZ)),
        make_attendance_item("att-002", "乙", datetime(2026, 11, 25, 9, 5, tzinfo=LOCAL_TZ)),
    ]
    groups = group_by_member(items)

    assert set(groups) == {"甲", "乙"}

    body = build_team_report(groups, DAY)
    rows = attendance_rows(body)

    assert len(rows) == 2
    assert any("att-001" in row for row in rows)
    assert any("att-002" in row for row in rows)


def test_904_04_record_id_in_detail_is_one_to_one_with_source_records():
    source_ids = ["att-001", "att-002", "att-003"]
    items = [
        make_attendance_item(rid, "甲", datetime(2026, 11, 25, 9, idx, tzinfo=LOCAL_TZ))
        for idx, rid in enumerate(source_ids)
    ]

    body = build_team_report(group_by_member(items), DAY)

    for rid in source_ids:
        assert rid in body
    assert body.count("record_id=") == len(source_ids)


def test_904_05_cli_mock_attendance_source_exit_zero(tmp_path):
    # 验收⑤原文「--source feishu_attendance --mock」两参数在 CLI 互斥组内，无法同传；
    # 且 main() 按退出码契约不向 stdout 打印日报正文，正文落 SQLite daily_reports.content。
    # 故改用 --mock（夹具含考勤条目、无需真实凭证）+ --no-notify（不触发推送失败码 3），
    # 并把 DB_PATH 指向临时库，从落库正文验证「exit 0 且日报含考勤行」。
    # mock 考勤夹具日期为 2026-11-18，与 DAY（11-25）不同，按夹具实际日期取日报。
    import sqlite3

    root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    src = str(root / "src")
    env["PYTHONPATH"] = src + os.pathsep + env.get("PYTHONPATH", "")
    db_path = tmp_path / "attendance.db"
    env["DB_PATH"] = str(db_path)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "smart_daily_v2.cli",
            "--mock",
            "--no-notify",
            "--day",
            "2026-11-18",
        ],
        capture_output=True,
        text=True,
        env=env,
        cwd=root,
        timeout=60,
    )

    assert result.returncode == 0, result.stderr
    conn = sqlite3.connect(db_path)
    try:
        contents = [
            row[0]
            for row in conn.execute(
                "SELECT content FROM daily_reports WHERE report_date = ?", ("2026-11-18",)
            )
        ]
    finally:
        conn.close()
    assert contents, "CLI 应落库当日日报"
    assert any("## 今日考勤" in body and "已打卡" in body for body in contents), (
        "落库个人日报正文应含双块考勤行（905）"
    )
