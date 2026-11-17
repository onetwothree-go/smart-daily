"""数据模型与归一化入口测试（TK-V2-102 红步）。

覆盖合约（v2/specs/tasks.md TK-V2-102 Interfaces / 验收标准 ①–④）：
- WorkItem：frozen dataclass，字段 record_id / source / member / kind / title / detail /
  occurred_at / local_day
- CommitEntry / TaskEntry / MessageEntry：三种源记录类型
- normalize(entries) -> list[WorkItem]：按 occurred_at 倒序、条数不丢不重、
  WorkItem 输入原样放行（G7 禁二次归一化）、未知类型抛 TypeError
- local_date(ts: datetime) -> date：按东八区 Asia/Shanghai 归属（R4）

依据 v2/README.md §2：normalize 只执行一次，local_date 按东八区归属。
"""

import dataclasses
from datetime import date, datetime, timedelta, timezone

import pytest

from smart_daily_v2.models import (
    CommitEntry,
    MessageEntry,
    TaskEntry,
    WorkItem,
    local_date,
    normalize,
)

UTC8 = timezone(timedelta(hours=8))


def test_normalize_sorts_and_keeps_count() -> None:
    # ① 三型混合输入 → 输出全为 WorkItem、按 occurred_at 倒序、条数与输入相等（不丢不重）
    commit = CommitEntry(
        record_id="sha-1",
        member="zhaorui715",
        title="feat: add models",
        detail="2 files changed",
        occurred_at=datetime(2026, 11, 9, 10, 0, tzinfo=UTC8),
    )
    task = TaskEntry(
        record_id="task-1",
        member="yuyue",
        title="整理接口契约",
        detail="P1",
        occurred_at=datetime(2026, 11, 9, 23, 30, tzinfo=UTC8),
    )
    message = MessageEntry(
        record_id="msg-1",
        member="zhaorui715",
        title="群内讨论",
        detail="方案评审",
        occurred_at=datetime(2026, 11, 10, 2, 0, tzinfo=timezone.utc),
    )

    result = normalize([commit, task, message])

    assert len(result) == 3
    assert all(isinstance(item, WorkItem) for item in result)
    # 倒序：按绝对时刻最新的在前（msg-1 的 02:00Z = 11-10 10:00+08 最新）
    assert [item.record_id for item in result] == ["msg-1", "task-1", "sha-1"]
    # 不丢不重：record_id 与输入一一对应
    assert {item.record_id for item in result} == {"sha-1", "task-1", "msg-1"}
    # 归一化时按东八区算 local_day：02:00Z → 11-10，其余两条在 11-09
    assert [item.local_day for item in result] == [
        date(2026, 11, 10),
        date(2026, 11, 9),
        date(2026, 11, 9),
    ]


def test_normalize_idempotent() -> None:
    # ② 已是 WorkItem 的输入 → 原样放行（二次归一化幂等，G7）
    older = WorkItem(
        record_id="r-old",
        source="github",
        member="zhaorui715",
        kind="commit",
        title="旧条目",
        detail="",
        occurred_at=datetime(2026, 11, 9, 9, 0, tzinfo=UTC8),
        local_day=date(2026, 11, 9),
    )
    newer = WorkItem(
        record_id="r-new",
        source="github",
        member="zhaorui715",
        kind="commit",
        title="新条目",
        detail="",
        occurred_at=datetime(2026, 11, 9, 18, 0, tzinfo=UTC8),
        local_day=date(2026, 11, 9),
    )

    result = normalize([older, newer])  # 故意按时间升序传入

    assert result == [older, newer]  # 原样放行：不重排、不改写
    assert result[0] is older
    assert result[1] is newer


def test_unknown_type_raises() -> None:
    # ③ 输入含未知类型 → 抛 TypeError，不静默丢弃
    entry = CommitEntry(
        record_id="sha-x",
        member="zhaorui715",
        title="x",
        detail="",
        occurred_at=datetime(2026, 11, 9, 10, 0, tzinfo=UTC8),
    )
    with pytest.raises(TypeError):
        normalize([entry, "not-an-entry"])


def test_local_date_utc8_boundary() -> None:
    # ④ R4：东八区 23:30 归当日；东八区次日零点归次日
    assert local_date(datetime(2026, 11, 9, 23, 30, tzinfo=UTC8)) == date(2026, 11, 9)
    assert local_date(datetime(2026, 11, 10, 0, 0, tzinfo=UTC8)) == date(2026, 11, 10)
    # tasks.md ④ 同款另一角：2026-11-10T00:00Z（= 08:00+08）仍归 11-10
    assert local_date(datetime(2026, 11, 10, 0, 0, tzinfo=timezone.utc)) == date(2026, 11, 10)
    # 与 naive ts.date() 的差异场景：UTC 16:00 直接 .date() 得 11-09，东八区归属是 11-10
    ts = datetime(2026, 11, 9, 16, 0, tzinfo=timezone.utc)
    assert ts.date() == date(2026, 11, 9)
    assert local_date(ts) != ts.date()
    assert local_date(ts) == date(2026, 11, 10)


def test_workitem_is_frozen() -> None:
    # Interfaces：WorkItem 为 frozen dataclass，字段不可变
    item = WorkItem(
        record_id="r-frozen",
        source="github",
        member="zhaorui715",
        kind="commit",
        title="不可变条目",
        detail="",
        occurred_at=datetime(2026, 11, 9, 10, 0, tzinfo=UTC8),
        local_day=date(2026, 11, 9),
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        item.title = "改写应失败"  # type: ignore[misc]
