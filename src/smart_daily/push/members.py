"""成员邮箱映射 —— 把日报归属人对应到收件邮箱

为什么需要这个模块：
    生成层产出的是「成员 -> 个人日报文本」，推送层需要的是「邮箱 -> 收件人」。
    两者之间的映射是配置，不是代码 —— 所以放在环境变量里，由配置管理员维护。

配置格式（.env，本地维护、不进仓库）：
    MEMBER_EMAILS=杨佳莹:jy@example.com,于悦:yy@example.com,方赫:fh@example.com,赵蕊:zr@example.com

    说明：成员名必须与采集到的 author_name 一致（mock 数据源里即为四名成员真名）；
    真实邮箱映射只写在本地 .env（被 .gitignore 保护），本文件示例一律用 example.com 占位，
    避免把成员真实邮箱推进公开仓库。

设计要点：
  1. 映射表是可选的 —— 没配就跳过邮件推送，不影响其他通道。
  2. 支持多邮箱 —— 同一个成员可以配多个邮箱（逗号分隔）。
  3. 未知成员不报错 —— 只在日志里提示，避免一个拼写错误让整条流程崩掉。
"""

from __future__ import annotations

import os


def load_member_emails() -> dict[str, list[str]]:
    """从环境变量 MEMBER_EMAILS 读取成员邮箱映射。

    Returns:
        {成员标识: [邮箱, ...]}；未配置时返回空字典。
    """
    raw = os.getenv("MEMBER_EMAILS", "").strip()
    if not raw:
        return {}

    mapping: dict[str, list[str]] = {}
    for pair in raw.split(","):
        pair = pair.strip()
        if not pair or ":" not in pair:
            continue
        member, emails = pair.split(":", 1)
        member = member.strip()
        addr_list = [e.strip() for e in emails.split(";") if e.strip()]
        if member and addr_list:
            mapping.setdefault(member, []).extend(addr_list)
    return mapping


def resolve_recipients(member: str, mapping: dict[str, list[str]] | None = None) -> list[str]:
    """查某个成员的收件邮箱。

    匹配规则：先精确匹配，再尝试用邮箱前缀匹配 Git 登录名
    （GitHub 登录名常是邮箱前缀，这样配置更省事）。
    """
    if mapping is None:
        mapping = load_member_emails()
    if not mapping:
        return []

    if member in mapping:
        return list(mapping[member])

    # 退化匹配：member 形如 name@example.com，用前缀找
    prefix = member.split("@")[0].strip()
    if prefix in mapping:
        return list(mapping[prefix])

    # 后缀匹配：配置里写的是邮箱，成员名是登录名
    for key, emails in mapping.items():
        if key.split("@")[0] == prefix:
            return list(emails)
    return []
