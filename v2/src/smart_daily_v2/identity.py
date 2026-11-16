"""身份归并函数。\n\n归属键统一 strip()+casefold()，单点归一化，下游禁止二次归一化。\n"""


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
