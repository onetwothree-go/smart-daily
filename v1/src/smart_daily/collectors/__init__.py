"""采集层 —— 负责从各数据源获取原始工作记录

模块职责边界（对应 design.md 的分层架构）：
    采集层只做「取数据 + 转成统一模型」，不做业务判断、不做日报文本生成。
    生成的活儿是生成层的责任。

包含：
    base.py       —— WorkSource 协议 + 降级入口（数据源可替换的设计落点）
    models.py     —— CommitEntry / MessageEntry / TaskEntry / WorkItem 统一数据模型
    github.py     —— GitHub API 采集器（真实数据源）
    feishu.py     —— 飞书开放平台采集器（任务 + 群消息）
    local_git.py  —— 本地 Git 仓库采集器（过渡/兜底数据源）
    mock.py       —— 演示数据源（无需凭证，保证主流程始终可跑）
"""

from .base import SourceUnavailableError, WorkSource, collect_with_fallback
from .feishu import FeishuCollector
from .github import GitHubCollector
from .local_git import LocalGitCollector
from .mock import MockCollector
from .models import CommitEntry, MessageEntry, RawRecord, TaskEntry, WorkItem, normalize

__all__ = [
    "WorkSource",
    "SourceUnavailableError",
    "collect_with_fallback",
    "CommitEntry",
    "MessageEntry",
    "TaskEntry",
    "WorkItem",
    "RawRecord",
    "normalize",
    "GitHubCollector",
    "FeishuCollector",
    "LocalGitCollector",
    "MockCollector",
]
