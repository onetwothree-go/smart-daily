"""推送层 —— 生成日报并送到人手里

包含：
    generator.py  —— 纯函数生成日报文本（无副作用，易测）
    notifiers.py  —— 推送通道：SMTP 邮件 / 飞书 Webhook，可替换
"""

from .generator import (
    build_personal_report,
    build_team_report,
    group_by_member,
    summarize_counts,
)
from .notifiers import (
    EmailNotifier,
    FeishuWebhookNotifier,
    MultiNotifier,
    Notifier,
)

__all__ = [
    "build_personal_report",
    "build_team_report",
    "group_by_member",
    "summarize_counts",
    "EmailNotifier",
    "FeishuWebhookNotifier",
    "MultiNotifier",
    "Notifier",
]
