"""采集层抽象基类 —— 数据源可替换的设计落点

为什么有这个模块：
    指导书 FAQ 明确写道「凭证申请不下来或审核未通过时，不必阻塞进度：先接 GitHub 数据源与
    模拟数据源（mock 数据源），保证主流程可跑；凭证就绪后再切换真实接口。这正是
    design.md 中『数据源可替换』的设计要求——把它写进接口契约。」

    本模块把「工作痕迹采集」抽象成一个协议（Protocol），所有数据源实现同一套接口：
        collect(since, until) -> list[WorkItem]

    三个数据源（GitHub / 飞书 / 本地 Git）产出不同类型的原始记录，
    但都归一化成 WorkItem，生成层因此不必为每种数据源写一遍逻辑。

设计约束（对应指导书第六部分 AI 使用四色清单）：
    业务逻辑与接口契约属「黄色」等级 —— 人工验证并留审查记录，未审查即视为未完成。
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable

from .models import RawRecord, WorkItem, normalize


@runtime_checkable
class WorkSource(Protocol):
    """工作痕迹数据源协议。

    任何实现本协议的对象都可以作为采集层的输入，编排层不关心数据来自
    GitHub API、飞书开放平台还是本地 Git 仓库。

    约定：collect() 返回「原始记录」（CommitEntry / MessageEntry / TaskEntry），
    归一化成 WorkItem 由 collect_with_fallback 在入口统一做 ——
    这样每个采集器只需要负责「把数据取回来」，不必关心下游怎么用。
    """

    #: 数据源名称，用于日志与降级提示
    name: str

    def collect(
        self,
        *,
        since: datetime | None = None,
        until: datetime | None = None,
        author: str | None = None,
    ) -> list[RawRecord]:
        """采集时间窗口内的工作痕迹。

        Args:
            since: 起始时间（含），None 表示不限
            until: 截止时间（含），None 表示不限
            author: 只采集该作者的记录，None 表示全部

        Returns:
            原始记录列表（按时间倒序）；无数据时返回空列表。

        Raises:
            SourceUnavailableError: 数据源不可用（凭证缺失、网络失败、仓库为空等）
        """
        ...


class SourceUnavailableError(RuntimeError):
    """数据源不可用。

    编排层捕获此异常后应降级到下一个候选数据源，而不是让主流程中断 ——
    这正是「无手工编写也能跑通」的关键保障。
    """


def collect_with_fallback(
    sources: list[WorkSource],
    *,
    since: datetime | None = None,
    until: datetime | None = None,
    author: str | None = None,
) -> tuple[list[WorkItem], str]:
    """按优先级依次尝试数据源，返回首个成功的结果。

    这是采集层的容错入口：任一数据源不可用时自动尝试下一个，
    全部失败才抛出异常（由编排层决定最终降级策略）。

    Returns:
        (归一化后的工作痕迹列表, 实际生效的数据源名称)

    Raises:
        SourceUnavailableError: 所有数据源均不可用
    """
    errors: list[str] = []
    for src in sources:
        try:
            raw = src.collect(since=since, until=until, author=author)
        except SourceUnavailableError as exc:
            errors.append(f"{src.name}: {exc}")
            # 降级成功时 errors 不会进异常消息，必须同步打到 stdout，
            # 否则日志里只有「生效数据源 = xxx」，看不到前一个源为什么挂了
            print(f"[source] {src.name} 不可用：{exc}")
            continue
        except Exception as exc:  # noqa: BLE001 - 任何数据源异常都不应中断主流程
            errors.append(f"{src.name}: {type(exc).__name__}: {exc}")
            print(f"[source] {src.name} 不可用：{type(exc).__name__}: {exc}")
            continue
        return normalize(raw), src.name

    raise SourceUnavailableError("所有数据源均不可用 -> " + " | ".join(errors))
