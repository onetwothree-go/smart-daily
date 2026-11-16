"""统一的数据模型 —— 各采集模块共用

放在独立模块的原因：models 不依赖任何具体数据源实现（GitHub / 飞书 / 本地 Git），
采集器与生成层都只依赖它，避免出现循环依赖。

三类记录的关系：
    CommitEntry  —— Git 提交（GitHub API / 本地 Git 仓库）
    MessageEntry —— 飞书消息（群聊）
    TaskEntry    —— 飞书任务

它们都是「工作痕迹」，但字段不同、来源不同。生成层不直接消费这三种类型，
而是通过 WorkItem 归一化后的统一视图，这样生成逻辑不必为每种数据源写一遍。
"""

# --- 答辩口径 · 采集层统一数据模型（见答辩稿 2.6.1）---
# CommitEntry / MessageEntry / TaskEntry 是 frozen dataclass，normalize() 统一压成 WorkItem；
# 生成层只认 WorkItem 这一种输入，因此不必为每个数据源各写一套逻辑。
# local_date() 用 astimezone().date() 取本地日历，避免东八区晚 8 点后 UTC 日期错一天（I3/C9）。

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any, Literal


@dataclass(frozen=True)
class CommitEntry:
    """一条提交记录对应的日报条目候选。

    字段设计依据「日报条目 = 谁 + 什么时候 + 做了什么 + 在哪个仓库」。
    协作归属（谁共同贡献）留到第 2 周由关联规则补全，本期先保证单条记录完整。

    用 frozen=True 是因为条目一旦采集完成就不应被下游随意修改 ——
    需要变更时用 dataclasses.replace 生成新对象，保证数据流可追溯。
    """

    sha: str
    author_login: str
    author_name: str
    timestamp: datetime
    message: str
    repo: str
    url: str
    additions: int = 0
    deletions: int = 0
    changed_files: int = 0
    files: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """序列化为日报条目（可 JSON 化）。"""
        return {
            "sha": self.sha,
            "author_login": self.author_login,
            "author_name": self.author_name,
            "timestamp": self.timestamp.isoformat(),
            "message": self.message,
            "repo": self.repo,
            "url": self.url,
            "additions": self.additions,
            "deletions": self.deletions,
            "changed_files": self.changed_files,
            "files": self.files,
        }


@dataclass(frozen=True)
class MessageEntry:
    """一条飞书消息。

    采集群聊消息时，「谁发的」和「说了什么」是两个独立维度：
    消息有 sender_id（可能是用户也可能是机器人），内容是富文本，
    需要把富文本里的 @提及 和链接拍平成纯文本。
    """

    message_id: str
    chat_id: str
    sender_id: str
    sender_name: str
    timestamp: datetime
    text: str
    msg_type: str = "text"
    mentions: list[str] = field(default_factory=list)
    thread_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "message_id": self.message_id,
            "chat_id": self.chat_id,
            "sender_id": self.sender_id,
            "sender_name": self.sender_name,
            "timestamp": self.timestamp.isoformat(),
            "text": self.text,
            "msg_type": self.msg_type,
            "mentions": self.mentions,
            "thread_id": self.thread_id,
        }


@dataclass(frozen=True)
class TaskEntry:
    """一条飞书任务。

    任务有两个关键的时间维度：
        created_at —— 任务什么时候建的
        completed_at —— 什么时候完成的（未完成则为 None）
    日报关心的是「当天有什么进展」，所以两个时间都要保留，
    由生成层决定用哪个做归属判断。
    """

    task_id: str
    summary: str
    description: str
    creator_id: str
    creator_name: str
    created_at: datetime
    completed_at: datetime | None = None
    completed: bool = False
    members: list[str] = field(default_factory=list)
    due: datetime | None = None
    url: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "summary": self.summary,
            "description": self.description,
            "creator_id": self.creator_id,
            "creator_name": self.creator_name,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "completed": self.completed,
            "members": self.members,
            "due": self.due.isoformat() if self.due else None,
            "url": self.url,
        }


# 归一化后的统一工作痕迹 —— 生成层只认这一种
SourceKind = Literal["commit", "message", "task"]


@dataclass(frozen=True)
class WorkItem:
    """归一化后的工作痕迹，生成层的唯一输入。

    把 CommitEntry / MessageEntry / TaskEntry 三种类型压平成同一个视图，
    生成层就不需要为每种数据源写一套逻辑 —— 这是分层架构带来的收益。

    字段对应「日报条目 = 谁 + 什么时候 + 做了什么 + 在哪」：
        member    —— 归属到谁
        timestamp —— 归属到哪一天
        title     —— 做了什么（标题）
        detail    —— 补充说明
        source    —— 来自哪个数据源（生成层可据此分组或加来源标签）
    """

    member: str
    timestamp: datetime
    title: str
    source: SourceKind
    detail: str = ""
    url: str = ""
    record_id: str = ""
    metrics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "member": self.member,
            "timestamp": self.timestamp.isoformat(),
            "title": self.title,
            "source": self.source,
            "detail": self.detail,
            "url": self.url,
            "record_id": self.record_id,
            "metrics": self.metrics,
        }

    @classmethod
    def from_commit(cls, entry: CommitEntry) -> "WorkItem":
        """从 Git 提交归一化。"""
        detail = entry.message
        if entry.changed_files:
            detail += f"（{entry.changed_files} 个文件，+{entry.additions}/-{entry.deletions}）"
        return cls(
            member=entry.author_name or entry.author_login,
            timestamp=entry.timestamp,
            title=entry.message,
            source="commit",
            detail=detail,
            url=entry.url,
            record_id=entry.sha,
            metrics={
                "repo": entry.repo,
                "additions": entry.additions,
                "deletions": entry.deletions,
                "changed_files": entry.changed_files,
            },
        )

    @classmethod
    def from_message(cls, entry: MessageEntry) -> "WorkItem":
        """从飞书消息归一化。"""
        return cls(
            member=entry.sender_name or entry.sender_id,
            timestamp=entry.timestamp,
            title=entry.text[:60],
            source="message",
            detail=entry.text,
            url="",
            record_id=entry.message_id,
            metrics={"chat_id": entry.chat_id, "mentions": entry.mentions},
        )

    @classmethod
    def from_task(cls, entry: TaskEntry) -> "WorkItem":
        """从飞书任务归一化。"""
        return cls(
            member=entry.creator_name or entry.creator_id,
            timestamp=entry.created_at,
            title=entry.summary,
            source="task",
            detail=entry.description,
            url=entry.url,
            record_id=entry.task_id,
            metrics={
                "completed": entry.completed,
                "completed_at": entry.completed_at.isoformat() if entry.completed_at else None,
                "members": entry.members,
            },
        )


def local_date(timestamp: datetime) -> date:
    """取时间戳对应的「本地日期」。

    为什么不能用 timestamp.date()：
        采集层拿到的都是带时区的时间（GitHub API 返回 UTC，本地 git 也转成 UTC）。
        直接取 .date() 得到的是 UTC 日期，而日报是给人看的，应该按本地日历归属 ——
        东八区晚上 8 点之后的提交，UTC 日期还停在当天，日报标题就会写成前一天。

    这个坑在 mock 数据源上尤其明显：本地 09:00 时 UTC 还是前一天 01:00。
    """
    return timestamp.astimezone().date()


def record_timestamp(entry: Any) -> datetime:
    """取任意原始记录的「事件发生时间」。

    为什么需要这个函数：
        三种记录类型的时间字段名并不统一 ——
            CommitEntry.timestamp / MessageEntry.timestamp / TaskEntry.created_at
        凡是「按时间排序或过滤」的地方都得处理这个差异，
        散落各处理容易出错，所以收敛到这一处。

    Raises:
        TypeError: 记录类型不受支持
    """
    if isinstance(entry, (CommitEntry, MessageEntry)):
        return entry.timestamp
    if isinstance(entry, TaskEntry):
        return entry.created_at
    if isinstance(entry, WorkItem):
        return entry.timestamp
    raise TypeError(f"无法取时间的记录类型：{type(entry).__name__}")


def normalize(entries: list[Any]) -> list[WorkItem]:
    """把任意来源的记录列表归一化成 WorkItem 列表，按时间倒序。

    接受 CommitEntry / MessageEntry / TaskEntry 的任意混合列表 ——
    采集层各数据源独立获取，归一化在生成层入口统一做。
    """
    out: list[WorkItem] = []
    for e in entries:
        if isinstance(e, CommitEntry):
            out.append(WorkItem.from_commit(e))
        elif isinstance(e, MessageEntry):
            out.append(WorkItem.from_message(e))
        elif isinstance(e, TaskEntry):
            out.append(WorkItem.from_task(e))
        elif isinstance(e, WorkItem):
            out.append(e)  # 已归一化的条目原样放行，便于二次调用不报错
        else:
            raise TypeError(f"无法归一化的记录类型：{type(e).__name__}")
    out.sort(key=lambda w: w.timestamp, reverse=True)
    return out


#: 采集器允许返回的原始记录类型
RawRecord = CommitEntry | MessageEntry | TaskEntry
