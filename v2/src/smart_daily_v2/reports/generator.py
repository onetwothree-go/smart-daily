import re
from collections.abc import Mapping
from datetime import date

from smart_daily_v2.models import LOCAL_TZ, WorkItem

_KIND_LABELS = {
    "commit": "提交",
    "task": "任务",
    "message": "消息",
    # TK-V2-903（design §5-2）：考勤条目 badge 中文标签。
    "attendance": "考勤",
}
_CONVENTIONAL_TYPE = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*)\s*:")


def _type_badge(item: WorkItem) -> str:
    """优先取 conventional commit 的 type 前缀（fix:/docs:/feat: …），否则回落 kind 中文标签。

    TK-V2-903（design §5-2）：kind=attendance 强制返回「考勤」，
    避免标题含 `xxx:` 时被 conventional 前缀抢先显示为英文徽标。
    """
    if item.kind == "attendance":
        return _KIND_LABELS["attendance"]
    match = _CONVENTIONAL_TYPE.match(item.title)
    if match:
        return match.group(1)
    return _KIND_LABELS.get(item.kind, item.kind)


def _clean(text: str) -> str:
    """压成单行并转义竖线，避免多行 commit message 撑破 Markdown 表格。"""
    return " ".join(text.split()).replace("|", "\\|")


def _headline(item: WorkItem) -> str:
    """内容列标题：去掉已经在类型列出现过的 conventional 前缀。

    考勤条目只展示「已打卡」这一事实，不把飞书的出勤状态判定（早退/迟到等）
    渲染到日报正文：打卡时间、record_id 均保留，C11 逐条对账所需的状态仍完整
    留在 WorkItem.detail 内，仅不在面向读者的表格里披露。
    """
    if item.kind == "attendance":
        return "已打卡"
    title = _clean(item.title)
    match = _CONVENTIONAL_TYPE.match(title)
    if match:
        stripped = title[match.end() :].strip()
        if stripped:
            return stripped
    return title


def _supplement(item: WorkItem) -> str:
    """详情只在确实带来新信息时追加；GitHub 的 detail==title 不再重复印一遍。"""
    if item.kind == "attendance":
        # 只把 record_id 原样带进日报供对账溯源；出勤状态留在 detail、不进正文。
        # 兼容采集源 `record_id: xxx` 与集成用例 `record_id=xxx` 两种内嵌写法。
        detail = _clean(item.detail or "")
        match = re.search(r"record_id[:=]\s*[\w-]+", detail)
        return match.group(0) if match else ""
    title = _clean(item.title)
    detail = _clean(item.detail or "")
    if not detail or detail == title:
        return ""
    if detail.startswith(title):
        return detail[len(title) :].lstrip(" —-:：")
    return detail


def _local_hhmm(item: WorkItem) -> str:
    """条目归属时区的 HH:MM；format_item 与个人日报列表块共用同一取时口径。"""
    occurred_at = item.occurred_at
    if occurred_at.tzinfo is not None:
        occurred_at = occurred_at.astimezone(LOCAL_TZ)
    return f"{occurred_at:%H:%M}"


def _content_with_extra(item: WorkItem) -> str:
    """内容 = 标题 +（确有新增信息时）详情；表格行与双块列表行共用。"""
    content = _headline(item)
    extra = _supplement(item)
    return f"{content} —— {extra}" if extra else content


def format_item(item: WorkItem) -> str:
    """单条工作痕迹 → 表格数据行。

    design 0.7-diff 0.6/0.7 §5-1 先后把个人日报、团队日报各成员明细改为双块，
    两路日报均已不走本函数；保留本函数供 badge / 脱敏 / 1:1 对账的既有断言复用，
    输出逐字不动（既有 format_item 相关护栏不失效）。
    """
    badge = _clean(_type_badge(item))
    return f"| {_local_hhmm(item)} | `{badge}` | {_content_with_extra(item)} |"


def build_personal_report(member: str, items: list[WorkItem], day: date) -> str:
    """个人日报 → `今日考勤` 独立块 + `工作记录` 列表块（S11 乙案 / TK-V2-905）。

    design 0.7-diff 0.6 §5-1 局部翻案：个人日报不再用 `| HH:MM | badge | 内容 |`
    表格行与提交混排、不出现表格分隔行。考勤块仅列打卡事实（`HH:MM` + 「已打卡」
    + `record_id`），工作记录块以列表逐条列工作内容。①a 脱敏不变（状态只留 detail），
    计数口径、1:1 对账、推送链、团队日报均不受影响。
    """
    lines = [f"# 个人日报 · {day:%Y-%m-%d} · {member}", ""]
    lines.append(f"> 今日共 **{len(items)} 条**工作记录 ｜ 由系统自动生成，手工编写 0 条")
    lines.append("")

    attendance = [item for item in items if item.kind == "attendance"]
    work = [item for item in items if item.kind != "attendance"]

    if attendance:
        lines.append("## 今日考勤")
        lines.append("")
        lines.extend(f"- {_local_hhmm(item)} {_content_with_extra(item)}" for item in attendance)
        lines.append("")

    lines.append("## 工作记录")
    lines.append("")
    if work:
        for item in work:
            badge = _clean(_type_badge(item))
            lines.append(f"- {_local_hhmm(item)} `{badge}` {_content_with_extra(item)}")
    else:
        lines.append("- 今日无工作记录")

    lines.extend(["", "---", "", "> 数据来源：真实工作记录 ｜ 本日报由系统自动汇总"])
    return "\n".join(lines)


def build_team_report(groups: Mapping[str, list[WorkItem]], day: date) -> str:
    """团队日报 → 顶部汇总表原样 + 每个成员名下 `今日考勤` / `工作记录` 双块。

    design 0.7-diff 0.7 §5-1（TK-V2-907，issue #25）：仅成员明细由表格行改为双块，
    与个人日报 S11 乙案同口径；顶部「今日贡献一览」汇总表（记录数/占比/分布、
    含全部考勤条目）逐字不动。①a 脱敏、1:1 对账、1A 计数、推送链均不变；
    S12 团队出勤一览、S14 缺卡提醒仍 ☐ 未纳本轮。
    """
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
        attendance = [item for item in items if item.kind == "attendance"]
        work = [item for item in items if item.kind != "attendance"]
        if attendance:
            lines.append("#### 今日考勤")
            lines.append("")
            lines.extend(
                f"- {_local_hhmm(item)} {_content_with_extra(item)}" for item in attendance
            )
            lines.append("")
        lines.append("#### 工作记录")
        lines.append("")
        if work:
            for item in work:
                badge = _clean(_type_badge(item))
                lines.append(f"- {_local_hhmm(item)} `{badge}` {_content_with_extra(item)}")
        else:
            lines.append("- 今日无工作记录")
    lines.extend(["", "---", "", "> 数据来源：真实工作记录 ｜ 本日报由系统自动汇总，手工编写 0 条"])
    return "\n".join(lines)


def group_by_member(items: list[WorkItem]) -> dict[str, list[WorkItem]]:
    groups: dict[str, list[WorkItem]] = {}
    for item in items:
        groups.setdefault(item.member, []).append(item)

    for member, member_items in groups.items():
        # 考勤条目按用户反馈（2026-11-26 截图）须独立于工作记录、不得夹在提交之间。
        # 采用「考勤置顶、其余按时间倒序」：考勤排在该成员最前，工作记录仍按时间倒序。
        # 两路日报（个人 / 团队）共用本函数，改一处即同时生效；无考勤成员排序完全不变。
        attendance = [item for item in member_items if item.kind == "attendance"]
        work = [item for item in member_items if item.kind != "attendance"]
        work.sort(key=lambda item: item.occurred_at, reverse=True)
        groups[member] = attendance + work

    return groups
