"""身份归并函数。\n\n归属键统一 strip()+casefold()，单点归一化，下游禁止二次归一化。\n"""

import os


def display_name(raw: str, mapping_raw: str | None = None) -> str:
    """账号名→中文显示名（范围外新增，状态 ☐ 待确认）。

    映射原文格式 `登录名:显示名,登录名:显示名`，键与值 strip、键 casefold，
    大小写/空格不敏感；非法片段静默跳过；未命中回落原账号名、不丢条目。
    mapping_raw 缺省时读环境变量 MEMBER_DISPLAY_NAMES。
    """
    if mapping_raw is None:
        mapping_raw = os.environ.get("MEMBER_DISPLAY_NAMES", "")
    mapping: dict[str, str] = {}
    for segment in mapping_raw.split(","):
        if ":" not in segment:
            continue
        key, value = segment.split(":", 1)
        key, value = key.strip().casefold(), value.strip()
        if key and value:
            mapping[key] = value
    return mapping.get(raw.strip().casefold(), raw)


def normalize_key(raw: str) -> str:
    """单一身份键的 strip+casefold。"""
    if raw is None:
        raise TypeError("identity key cannot be None")
    return raw.strip().casefold()


def normalize_members(raws: list[str]) -> dict[str, list[str]]:
    """批量归并：不同原始身份→同一键时合并列表。"""
    if any(r is None for r in raws):
        raise TypeError("member list contains None")
    result: dict[str, list[str]] = {}
    for raw in raws:
        key = raw.strip().casefold()
        result.setdefault(key, []).append(raw)
    return result
