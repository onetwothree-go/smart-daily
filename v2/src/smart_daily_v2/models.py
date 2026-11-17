"""数据模型与归一化入口。

三种源记录（CommitEntry / TaskEntry / MessageEntry）经 `normalize()` 统一成
`WorkItem`；归一化只执行一次，下游禁止二次归一化（G7）。

日期归属一律走 `local_date()`：按东八区（Asia/Shanghai）算归属日，
而非直接取 `datetime.date()`——UTC 的 16:00 在东八区已是次日。
"""

from dataclasses import dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo

# 东八区归属的唯一来源。用 IANA 时区库而非硬编码 +8 偏移，
# 以便历史时区数据变更时能跟着变（Windows 缺时区库由 tzdata 依赖提供）。
LOCAL_TZ = ZoneInfo("Asia/Shanghai")


def local_date(ts: datetime) -> date:
    """按东八区归属取日期（R4）。

    naive datetime 视为已是东八区本地时间，不做偏移（避免二次换算）；
    带 tzinfo 的按绝对时刻转东八区。
    """
    if ts.tzinfo is None:
        return ts.date()
    return ts.astimezone(LOCAL_TZ).date()


@dataclass(frozen=True)
class WorkItem:
    """归一化后的工作条目，下游各层只消费这一种类型。"""

    record_id: str
    source: str
    member: str
    kind: str
    title: str
    detail: str
    occurred_at: datetime
    local_day: date


@dataclass(frozen=True)
class CommitEntry:
    """GitHub 提交源记录。"""

    record_id: str
    member: str
    title: str
    detail: str
    occurred_at: datetime


@dataclass(frozen=True)
class TaskEntry:
    """飞书任务源记录。"""

    record_id: str
    member: str
    title: str
    detail: str
    occurred_at: datetime


@dataclass(frozen=True)
class MessageEntry:
    """飞书群消息源记录。"""

    record_id: str
    member: str
    title: str
    detail: str
    occurred_at: datetime


_SOURCE_BY_TYPE: dict[type, tuple[str, str]] = {
    CommitEntry: ("github", "commit"),
    TaskEntry: ("feishu_task", "task"),
    MessageEntry: ("feishu_chat", "message"),
}


def normalize(entries: list[object]) -> list[WorkItem]:
    """把三类源记录归一成 WorkItem，并按 occurred_at 倒序排列。

    - 已是 WorkItem 的输入原样放行、不重新构造（幂等，G7）；
    - 条数与输入相等，不丢不重；
    - 未知类型抛 TypeError，不静默丢弃。
    """
    for entry in entries:
        if not isinstance(entry, (WorkItem, CommitEntry, TaskEntry, MessageEntry)):
            raise TypeError(
                f"unknown entry type: {type(entry).__name__!r}; "
                "expected WorkItem / CommitEntry / TaskEntry / MessageEntry"
            )

    if all(isinstance(entry, WorkItem) for entry in entries):
        # 全部已是 WorkItem：原样放行，不重排也不改写
        return list(entries)

    items: list[WorkItem] = []
    for entry in entries:
        if isinstance(entry, WorkItem):
            items.append(entry)
            continue
        source, kind = _SOURCE_BY_TYPE[type(entry)]
        items.append(
            WorkItem(
                record_id=entry.record_id,
                source=source,
                member=entry.member,
                kind=kind,
                title=entry.title,
                detail=entry.detail,
                occurred_at=entry.occurred_at,
                local_day=local_date(entry.occurred_at),
            )
        )
    items.sort(key=lambda item: item.occurred_at, reverse=True)
    return items
