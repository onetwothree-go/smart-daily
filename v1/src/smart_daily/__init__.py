"""智能日报生成器

四层架构：
    采集层 collectors/  —— 从 GitHub / 飞书 / 本地 Git 取工作痕迹
    生成层 push/generator.py —— 把痕迹拼成日报文本（纯函数）
    推送层 push/notifiers.py —— 邮件 / 飞书 Webhook 送出去
    主编排入口 orchestrator.py —— 串起三层，处理降级与幂等
"""

__version__ = "0.1.0"
