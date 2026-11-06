"""Mock 数据源 —— 无需任何凭证的演示数据源

为什么需要它（指导书第 24 页 FAQ 原文）：
    「飞书应用 / 邮箱授权码申请不下来，或审核未通过 —— 不必阻塞进度：
      先接 GitHub 数据源与模拟数据（mock 数据源），保证主流程可跑；
      凭证就绪后再切换真实接口。这也正是 design.md 中『数据源可替换』的设计要求。」

定位：
    这不是「假的」，而是「不依赖外部凭证的确定性数据源」。
    它有三个实际用途：
      1. 验收演示 —— 现场环境网络不通时，主流程依然能跑出完整日报
      2. 单元测试 —— 生成层的渲染逻辑需要一个稳定可预期的输入
      3. 接口契约的活文档 —— 新增采集器时照着它实现一遍就知道对不对

实现方式：生成相对当前时间偏移的条目，
所以无论何时运行，日报内容都落在「当天」，符合日报场景的时间语义。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from .models import CommitEntry, MessageEntry, TaskEntry, record_timestamp

#: 演示用的成员与各自的行为模板
#: 成员为本小组成员（姓名与 GitHub 登录名对应拼音，演示数据不含任何真实凭证）
_MOCK_PROFILES: list[dict[str, object]] = [
    {
        "login": "yangjiaying",
        "name": "杨佳莹",
        "commits": [
            ("docs: 完成需求澄清问答记录与隐含需求清单", 9),
            ("docs: 撰写业务调研报告初稿", 10),
            ("spec: 完善 proposal.md 范围与成功标准", 11),
        ],
        "messages": [("需求澄清的 12 个问题已全部回答，隐含需求整理出 6 条", 12)],
        "tasks": [("汇总 proposal.md 范围条目与用例对照表", 13, True)],
    },
    {
        "login": "yuyue",
        "name": "于悦",
        "commits": [
            ("design: 确定四层架构与模块职责划分", 10),
            ("adr: 补充 httpx 与 SQLite 选型决策记录", 12),
        ],
        "messages": [("design.md 的接口契约已按开发侧评审意见改了一版", 14)],
        "tasks": [("完成系统分析报告的数据模型章节", 15, False)],
    },
    {
        "login": "fanghe",
        "name": "方赫",
        "commits": [
            ("chore: 初始化 specs/ 目录与分支规范", 9),
            ("test: 补充采集器降级场景单元测试", 13),
            ("ci: 配置静态扫描与提交规范检查", 15),
        ],
        "messages": [("分支规范已发群里，大家提交前看一眼 BRANCHING.md", 11)],
        "tasks": [("归档本周组内 AI 使用日志并登记凭证就绪状态", 16, False)],
    },
    {
        "login": "zhaorui",
        "name": "赵蕊",
        "commits": [
            ("feat: 实现采集层数据源协议抽象与降级链路", 10),
            ("feat: 打通飞书推送通道与签名校验", 12),
            ("fix: 修复时间窗口过滤时边界未闭合的问题", 14),
        ],
        "messages": [("推送通道实测通过了，日报已经进群", 16)],
        "tasks": [("完成日报生成层分组渲染与集成测试", 17, False)],
    },
]


class MockCollector:
    """演示用数据源，实现 WorkSource 协议。

    特点：永不失败 —— 它不依赖网络、不依赖凭证。
    因此它应该排在降级链的**最后**，只在所有真实数据源都不可用时兜底，
    或者在演示/测试时显式指定使用。
    """

    name = "mock"

    def __init__(self, day: datetime | None = None) -> None:
        """初始化。

        Args:
            day: 基准时间，默认取当前本地时间。条目时间相对它偏移，
                  保证日报内容总是落在基准日当天。
        """
        # 用本地时间做基准：日报是按本地日历归属的，
        # 若拿 UTC 当基准，东八区早上运行时整份日报会落到前一天
        self._base = (day or datetime.now()).astimezone()

    def collect(
        self,
        *,
        since: datetime | None = None,
        until: datetime | None = None,
        author: str | None = None,
    ) -> list[CommitEntry | MessageEntry | TaskEntry]:
        """生成演示记录。

        行为约束（与真实采集器一致）：
          - 按时间倒序返回
          - 无数据时返回空列表（不抛异常）
          - since / until 为闭区间
        """
        base = self._base.replace(hour=0, minute=0, second=0, microsecond=0)
        out: list[CommitEntry | MessageEntry | TaskEntry] = []

        for profile in _MOCK_PROFILES:
            login = str(profile["login"])
            name = str(profile["name"])
            if author and author not in (login, name):
                continue

            for idx, (msg, hour) in enumerate(profile["commits"]):  # type: ignore[misc]
                ts = base + timedelta(hours=int(hour), minutes=idx * 7)
                out.append(
                    CommitEntry(
                        sha=f"mock{login[:2]}{idx:03d}",
                        author_login=login,
                        author_name=name,
                        timestamp=ts,
                        message=str(msg),
                        repo="smart-daily",
                        url=f"https://example.invalid/{login}/{idx}",
                        additions=30 + idx * 11,
                        deletions=5 + idx * 3,
                        changed_files=1 + idx,
                        files=["src/example.py"],
                    )
                )

            for idx, (text, hour) in enumerate(profile["messages"]):  # type: ignore[misc]
                ts = base + timedelta(hours=int(hour), minutes=idx * 13)
                out.append(
                    MessageEntry(
                        message_id=f"mockmsg{login[:2]}{idx:02d}",
                        chat_id="oc_mock_chat",
                        sender_id=f"ou_mock_{login}",
                        sender_name=name,
                        timestamp=ts,
                        text=str(text),
                    )
                )

            for idx, (summary, hour, done) in enumerate(profile["tasks"]):  # type: ignore[misc]
                ts = base + timedelta(hours=int(hour), minutes=idx * 5)
                out.append(
                    TaskEntry(
                        task_id=f"mocktask{login[:2]}{idx:02d}",
                        summary=str(summary),
                        description=f"[演示数据] {summary}",
                        creator_id=f"ou_mock_{login}",
                        creator_name=name,
                        created_at=ts,
                        completed_at=ts + timedelta(hours=1) if done else None,
                        completed=bool(done),
                        members=[name],
                    )
                )

        # 与真实采集器一致的时间窗口过滤（闭区间）
        # 注意：三种记录类型的时间字段名不统一（TaskEntry 用 created_at），
        # 必须走 record_timestamp 取值，不能直接 e.timestamp
        if since:
            out = [e for e in out if record_timestamp(e) >= since]
        if until:
            out = [e for e in out if record_timestamp(e) <= until]

        out.sort(key=record_timestamp, reverse=True)
        return out
