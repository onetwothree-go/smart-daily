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


def format_item(item: WorkItem) -> str:
    """单条工作痕迹 → 表格数据行，个人/团队日报共用（C4 逐字一致的单一来源）。"""
    occurred_at = item.occurred_at
    if occurred_at.tzinfo is not None:
        occurred_at = occurred_at.astimezone(LOCAL_TZ)

    rendered = f"| {occurred_at:%H:%M} | {_type_badge(item)} | {item.title}"
    if item.detail:
        rendered += f" —— {item.detail}"
    return rendered + " |"


def build_personal_report(member: str, items: list[WorkItem], day: date) -> str:
    lines = [f"# 个人日报 {day:%Y-%m-%d} · {member}", ""]
    lines.append("| 时间 | 类型 | 内容 |")
    lines.append("| :---: | :---: | :--- |")
    if items:
        lines.extend(format_item(item) for item in items)
    else:
        lines.append("| — | — | 今日无工作记录 |")
    return "\n".join(lines)


def build_team_report(groups: Mapping[str, list[WorkItem]], day: date) -> str:
    total_items = sum(len(items) for items in groups.values())
    lines = [f"# 团队日报 {day:%Y-%m-%d} · 成员 {len(groups)} 人 · 条目 {total_items} 条", ""]

    # 贡献一览表：按条数降序、占比按总数计算（全 0 时占比记 0.0%）
    lines.append("## 今日贡献一览")
    lines.append("")
    lines.append("| 成员 | 记录数 | 占比 | 分布 |")
    lines.append("| :--- | ---: | ---: | :--- |")
    ordered = sorted(groups.items(), key=lambda group: -len(group[1]))
    for member, items in ordered:
        share = (len(items) / total_items * 100) if total_items else 0.0
        bars = "█" * round(share / 10) if share else ""
        lines.append(f"| {member} | {len(items)} | {share:.1f}% | {bars} |")

    for member, items in ordered:
        lines.append("")
        lines.append(f"## {member}（{len(items)} 条）")
        lines.append("")
        lines.append("| 时间 | 类型 | 内容 |")
        lines.append("| :---: | :---: | :--- |")
        if items:
            lines.extend(format_item(item) for item in items)
        else:
            lines.append("| — | — | 今日无工作记录 |")
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
