from datetime import date

from smart_daily_v2.models import LOCAL_TZ, WorkItem

_KIND_LABELS = {"commit": "提交", "task": "任务", "message": "消息"}


def format_item(item: WorkItem) -> str:
    occurred_at = item.occurred_at
    if occurred_at.tzinfo is not None:
        occurred_at = occurred_at.astimezone(LOCAL_TZ)

    label = _KIND_LABELS.get(item.kind, item.kind)
    rendered = f"- [{occurred_at:%H:%M}] （{label}）{item.title}"
    if item.detail:
        rendered += f" —— {item.detail}"
    return rendered


def build_personal_report(member: str, items: list[WorkItem], day: date) -> str:
    lines = [f"# 个人日报 {day:%Y-%m-%d} · {member}"]
    if items:
        lines.extend(format_item(item) for item in items)
    else:
        lines.append("今日无工作记录")
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
