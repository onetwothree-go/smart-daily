"""身份映射 —— 把各种登录名 / 别名统一归并到团队显示名

为什么需要这个模块：
    同一个人在仓库里可能留下多种写法（GitHub 登录名、Gitee 登录名、git user.name 自由文本），
    日报按显示名分组，若不归并就会被拆成多个人、多份日报。

    design.md 2.2【本期约定】规定映射解析**收敛到唯一实现**：本模块。
    采集链路（GitHub / 本地 Git）与实时通道（scripts/notify_push.py）都调用这里，
    不得各写一套解析循环，否则两条链路的匹配口径会漂移（RT-06）。

配置来源（environment variable）：
    MEMBER_DISPLAY_NAMES=登录名:显示名,登录名:显示名
    键可写 GitHub 登录名、Gitee 登录名、邮箱本地部分或 git user.name，均可；
    归属键是「登录名 + 提交者姓名」双查，键写哪一种都能命中。

匹配语义（design.md 2.2 / 3.5 契约 2）：
    strip() 去首尾空白 + casefold() 大小写不敏感。
"""

from __future__ import annotations

import os

#: 存放映射的环境变量名（design.md 5.2：可入库级配置）
ENV_KEY = "MEMBER_DISPLAY_NAMES"


def parse_mapping(mapping_raw: str) -> dict[str, str]:
    """解析 ``登录名:显示名,登录名:显示名`` 格式，返回 ``{归一化键: 显示名}``。

    非法片段（无冒号、键或值空白）静默跳过 —— 映射是配置，写错一项不应让整条流程崩掉。
    """
    mapping: dict[str, str] = {}
    for pair in mapping_raw.split(","):
        pair = pair.strip()
        if ":" not in pair:
            continue
        key, value = pair.split(":", 1)
        key, value = key.strip(), value.strip()
        if key and value:
            mapping[key.casefold()] = value
    return mapping


def lookup_display_name(*candidates: str | None, mapping_raw: str | None = None) -> str | None:
    """按候选键依次查显示名，返回首个命中的显示名；全部未命中返回 ``None``。

    Args:
        candidates: 候选键，按优先级排列。例如本地 Git 采集传「邮箱本地部分、提交者姓名」，
            GitHub 采集传「登录名、提交者姓名」。
        mapping_raw: 映射原文；缺省读环境变量 ``MEMBER_DISPLAY_NAMES``。

    Returns:
        命中的显示名；未命中为 ``None`` —— 未命中的**行为**由调用方决定
        （采集链路回落原始名，实时通道回落并打告警），本函数不打印任何东西。
    """
    if mapping_raw is None:
        mapping_raw = os.getenv(ENV_KEY, "")
    mapping = parse_mapping(mapping_raw)
    for cand in candidates:
        if not cand:
            continue
        hit = mapping.get(cand.strip().casefold())
        if hit:
            return hit
    return None
