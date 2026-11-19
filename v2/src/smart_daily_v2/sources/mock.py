"""无凭证可复现夹具。

不是第四路正式数据源，不进 C1 计数口径，不自动挂载默认降级链，仅 --mock 显式指定。
"""

from datetime import datetime

from smart_daily_v2.models import WorkItem, local_date

FIXTURE_MEMBERS: tuple[str, ...] = ("甲", "乙", "丙", "丁")

_FIXTURE_ROWS: tuple[dict[str, str], ...] = (
    {
        "record_id": "mock-001",
        "member": "甲",
        "kind": "commit",
        "title": "更新日报汇总逻辑",
        "detail": "完善条目排序",
        "occurred_at": "2026-11-18T09:00:00+08:00",
        "source": "mock",
    },
    {
        "record_id": "mock-002",
        "member": "乙",
        "kind": "task",
        "title": "整理任务状态",
        "detail": "补充待办进度",
        "occurred_at": "2026-11-18T09:20:00+08:00",
        "source": "mock",
    },
    {
        "record_id": "mock-003",
        "member": "丙",
        "kind": "message",
        "title": "确认接口约定",
        "detail": "记录字段保持一致",
        "occurred_at": "2026-11-18T09:40:00+08:00",
        "source": "mock",
    },
    {
        "record_id": "mock-004",
        "member": "丁",
        "kind": "commit",
        "title": "添加时间筛选测试",
        "detail": "覆盖边界时刻",
        "occurred_at": "2026-11-18T10:00:00+08:00",
        "source": "mock",
    },
    {
        "record_id": "mock-005",
        "member": "甲",
        "kind": "task",
        "title": "检查归一化结果",
        "detail": "核对日期归属",
        "occurred_at": "2026-11-18T10:20:00+08:00",
        "source": "mock",
    },
    {
        "record_id": "mock-006",
        "member": "乙",
        "kind": "message",
        "title": "同步日报格式",
        "detail": "确认分节标题",
        "occurred_at": "2026-11-18T10:40:00+08:00",
        "source": "mock",
    },
    {
        "record_id": "mock-007",
        "member": "丙",
        "kind": "commit",
        "title": "调整成员分组",
        "detail": "保留稳定排序",
        "occurred_at": "2026-11-18T11:00:00+08:00",
        "source": "mock",
    },
    {
        "record_id": "mock-008",
        "member": "丁",
        "kind": "task",
        "title": "核对日报条目",
        "detail": "检查样例覆盖",
        "occurred_at": "2026-11-18T11:20:00+08:00",
        "source": "mock",
    },
    {
        "record_id": "mock-009",
        "member": "甲",
        "kind": "message",
        "title": "补充验收记录",
        "detail": "确认样例可复用",
        "occurred_at": "2026-11-18T11:40:00+08:00",
        "source": "mock",
    },
    {
        "record_id": "mock-010",
        "member": "乙",
        "kind": "commit",
        "title": "完成测试样例",
        "detail": "准备后续对账",
        "occurred_at": "2026-11-18T12:00:00+08:00",
        "source": "mock",
    },
)


def load_fixture_items() -> list[WorkItem]:
    items = []
    for row in _FIXTURE_ROWS:
        occurred_at = datetime.fromisoformat(row["occurred_at"])
        items.append(
            WorkItem(
                record_id=row["record_id"],
                source="mock",
                member=row["member"],
                kind=row["kind"],
                title=row["title"],
                detail=row["detail"],
                occurred_at=occurred_at,
                local_day=local_date(occurred_at),
            )
        )
    return items


class MockSource:
    name = "mock"

    def collect(
        self,
        *,
        since: datetime,
        until: datetime,
        author: str | None = None,
    ) -> list[WorkItem]:
        return [
            item
            for item in load_fixture_items()
            if since <= item.occurred_at <= until and (author is None or item.member == author)
        ]
