from smart_daily_v2.models import WorkItem


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
