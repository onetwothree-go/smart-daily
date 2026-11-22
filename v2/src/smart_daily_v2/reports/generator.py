import re
from collections.abc import Mapping
from datetime import date

from smart_daily_v2.models import LOCAL_TZ, WorkItem

_KIND_LABELS = {"commit": "提交", "task": "任务", "message": "消息"}
_CONVENTIONAL_TYPE = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*)\s*:")


def _type_badge(item: WorkItem) -> str:
    """优先取 conventional commit 的 type 前缀（fix:/docs:/feat: …），否则回落 kind 中文标签。"""
    match = _CONVENTIONAL_TYPE.match(item.title)
    if match:
        return match.group(1)
    return _KIND_LABELS.get(item.kind, item.kind)


def _clean(text: str) -> str:
    """压成单行并转义竖线，避免多行 commit message 撑破 Markdown 表格。"""
    return " ".join(text.split()).replace("|", "\\|")


def _headline(item: WorkItem) -> str:
    """内容列标题：去掉已经在类型列出现过的 conventional 前缀。"""
    title = _clean(item.title)
    match = _CONVENTIONAL_TYPE.match(title)
    if match:
        stripped = title[match.end() :].strip()
        if stripped:
            return stripped
    return title


def _supplement(item: WorkItem) -> str:
    """详情只在确实带来新信息时追加；GitHub 的 detail==title 不再重复印一遍。"""
    title = _clean(item.title)
    detail = _clean(item.detail or "")
    if not detail or detail == title:
        return ""
    if detail.startswith(title):
        return detail[len(title) :].lstrip(" —-:：")
    return detail


def format_item(item: WorkItem) -> str:
    """单条工作痕迹 → 表格数据行，个人/团队日报共用（C4 逐字一致的单一来源）。"""
    occurred_at = item.occurred_at
    if occurred_at.tzinfo is not None:
        occurred_at = occurred_at.astimezone(LOCAL_TZ)

    badge = _clean(_type_badge(item))
    content = _headline(item)
    extra = _supplement(item)
    if extra:
        content = f"{content} —— {extra}"
    return f"| {occurred_at:%H:%M} | `{badge}` | {content} |"


def build_personal_report(member: str, items: list[WorkItem], day: date) -> str:
    lines = [f"# 个人日报 · {day:%Y-%m-%d} · {member}", ""]
    lines.append(f"> 今日共 **{len(items)} 条**工作记录 ｜ 由系统自动生成，手工编写 0 条")
    lines.append("")
    lines.append("| 时间 | 类型 | 内容 |")
    lines.append("| :---: | :---: | :--- |")
    if items:
        lines.extend(format_item(item) for item in items)
    else:
        lines.append("| — | — | 今日无工作记录 |")
    lines.extend(["", "---", "", "> 数据来源：真实工作记录 ｜ 本日报由系统自动汇总"])
    return "\n".join(lines)


def build_team_report(groups: Mapping[str, list[WorkItem]], day: date) -> str:
    total_items = sum(len(items) for items in groups.values())
    lines = [f"# 团队日报 · {day:%Y-%m-%d}", ""]
    lines.append(
        f"> **{len(groups)} 位成员** ｜ **{total_items} 条工作记录** ｜ "
        "由系统从真实工作数据自动生成，手工编写 0 条"
    )
    lines.append("")
    lines.append("## 今日贡献一览")
    lines.append("")
    lines.append("| 成员 | 记录数 | 占比 | 分布 |")
    lines.append("| :--- | ---: | ---: | :--- |")
    ordered = sorted(groups.items(), key=lambda group: -len(group[1]))
    for member, items in ordered:
        share = (len(items) / total_items * 100) if total_items else 0.0
        bars = "█" * round(share / 10) if share else ""
        lines.append(f"| {member} | {len(items)} | {share:.1f}% | {bars} |")
    lines.extend(["", "---"])

    for member, items in ordered:
        lines.append("")
        lines.append(f"### {member} · {len(items)} 条")
        lines.append("")
        lines.append("| 时间 | 类型 | 内容 |")
        lines.append("| :---: | :---: | :--- |")
        if items:
            lines.extend(format_item(item) for item in items)
        else:
            lines.append("| — | — | 今日无工作记录 |")
    lines.extend(["", "---", "", "> 数据来源：真实工作记录 ｜ 本日报由系统自动汇总，手工编写 0 条"])
    return "\n".join(lines)


def group_by_member(items: list[WorkItem]) -> dict[str, list[WorkItem]]:
    groups: dict[str, list[WorkItem]] = {}
    for item in items:
        groups.setdefault(item.member, []).append(item)

    for member, member_items in groups.items():
        groups[member] = sorted(
            member_items,
            key=lambda item: item.occurred_at,
            reverse=True,
        )

    return groups
