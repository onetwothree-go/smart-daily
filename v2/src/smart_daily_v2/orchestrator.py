"""Daily report orchestration.

Scope notes (☐ 待组内确认):
- K2：9 键、五态与 pushed 不变量依据架构师接口契约变更审核记录
  L19 / L107-119 定稿；push_status 是 504 退出码 3 的唯一来源，不另称为
  组内另行确认。
- 502：真实持久化由后续任务接入；本模块 _persist_report 仅提供可打桩调用点，
  默认打印占位信息，不建库、不执行数据库 IO，待 502 落地后接线。
- S5：identity.py 仅提供 normalize_key / normalize_members；显示名映射不在
  本任务验收范围。本层直接消费采集器已归一化的 item.member，不新增身份函数，
  不改 conftest.py。
- 应送达集合与明细：本层根据个人日报成员、团队群及已配置的外部收件人独立构造
  expected，不从分发回执反推分母；无收件人记 no_recipient，无通道记 no_channel，
  其余 error 为空串。不扩展 Config。
- K4 / G7：tasks.md L292 方案甲要求采集器产 RawRecord、归一化单点在 104；
  L300、L307-308 与已落地 fallback / 采集器接口则使用 WorkItem。本层遵循已落地
  协议消费 WorkItem，不调用 normalize()，此口径差异待确认，不改回 RawRecord。
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from datetime import date, datetime, time, timedelta

from smart_daily_v2.config import load_config
from smart_daily_v2.identity import display_name
from smart_daily_v2.models import LOCAL_TZ, WorkItem, local_date
from smart_daily_v2.notifiers.dispatch import all_delivered, dispatch
from smart_daily_v2.notifiers.members import load_member_emails, load_report_recipients
from smart_daily_v2.reports.generator import (
    build_personal_report,
    build_team_report,
    group_by_member,
)
from smart_daily_v2.sources.base import AllSourcesUnavailableError, WorkSource
from smart_daily_v2.sources.fallback import collect_with_fallback

# 第 4 周变更涟漪（TK-V2-902 / design §4-3 定案 A）：考勤源按 name 识别，
# 走独立支路、不进 collect_with_fallback 降级链（后者「首个非空源即停止」会吞掉考勤）。
ATTENDANCE_SOURCE_NAME = "feishu_attendance"


def _split_sources(
    sources: Sequence[WorkSource],
) -> tuple[list[WorkSource], list[WorkSource]]:
    """把考勤源从主链分出：返回 (主链源, 考勤源)，顺序保持稳定。"""
    main: list[WorkSource] = []
    attendance: list[WorkSource] = []
    for source in sources:
        if getattr(source, "name", None) == ATTENDANCE_SOURCE_NAME:
            attendance.append(source)
        else:
            main.append(source)
    return main, attendance


def _collect_attendance(
    attendance_sources: Sequence[WorkSource],
    *,
    since: datetime,
    until: datetime,
    reasons: list[str],
) -> list[WorkItem]:
    """考勤独立支路：逐源独立 try/except，失败留痕不中断，成功条目合流。"""
    items: list[WorkItem] = []
    for source in attendance_sources:
        try:
            rows = source.collect(since=since, until=until)
        except Exception as exc:  # 独立支路：任何失败只留痕，不拖垮主链
            reason = getattr(exc, "reason", None) or str(exc)
            reasons.append(f"{source.name}: {reason}")
            continue
        items.extend(rows)
    return items


def _persist_report(
    member: str,
    body: str,
    item_count: int,
    day: date,
    source: object,
) -> None:
    print(f"[502] {day.isoformat()} {member} {item_count} 条（后续任务接入）")


def run(day: date, *, sources: Sequence[WorkSource], notify: bool = True) -> dict:
    since = datetime.combine(day, time.min, tzinfo=LOCAL_TZ)
    until = datetime.combine(day + timedelta(days=1), time.min, tzinfo=LOCAL_TZ)

    # TK-V2-902（design §4-3 定案 A）：主链与考勤支路分离。
    # 主链为空（只跑考勤）时不调用 collect_with_fallback——它会对空源列表抛
    # AllSourcesUnavailableError，而考勤单跑属合法场景（验收③）。
    main_sources, attendance_sources = _split_sources(sources)
    main_error: AllSourcesUnavailableError | None = None
    if main_sources:
        try:
            collected_items, reasons = collect_with_fallback(main_sources, since=since, until=until)
        except AllSourcesUnavailableError as exc:
            # 主链全失败先记账；考勤支路若有产出则不判整次失败（验收②）。
            main_error = exc
            collected_items = []
            reasons = [f"{err.source}: {err.reason}" for err in exc.errors]
    else:
        collected_items, reasons = [], []

    attendance_items = _collect_attendance(
        attendance_sources, since=since, until=until, reasons=reasons
    )
    # 全部数据源失败才判整次失败：主链全失败且考勤无产出（验收②）。
    # 只跑考勤且全失败、或完全无源时同样抛（沿用 collect_with_fallback([]) 语义）。
    if main_error is not None and not attendance_items:
        raise main_error
    if not main_sources and not attendance_items and sources:
        raise AllSourcesUnavailableError([])

    collected_items = collected_items + attendance_items
    items: list[WorkItem] = [
        item for item in collected_items if local_date(item.occurred_at) == day
    ]
    # 范围外新增（☐ 待确认）：编排层一处把账号名映射为中文显示名，
    # 采集后、group_by_member 之前替换，下游分组/日报/落库/推送/查询自动生效。
    mapping_raw = load_config().member_display_names
    mapped: list[WorkItem] = []
    for raw_item in items:
        shown = display_name(raw_item.member, mapping_raw=mapping_raw)
        if shown == raw_item.member:
            # 未命中回落：显式告警，不静默丢弃、不抛异常（状态 ☐ 待确认）
            print(f"[显示名] 未映射，回落原账号名: {raw_item.member}")
            mapped.append(raw_item)
        else:
            mapped.append(replace(raw_item, member=shown))
    items = mapped
    groups = group_by_member(items)
    team_text = build_team_report(groups, day)

    personal: dict[str, str] = {}
    saved = 0
    for member, member_items in groups.items():
        text = build_personal_report(member, member_items, day)
        personal[member] = text
        _persist_report(member, text, len(member_items), day, reasons)
        saved += 1

    if not notify:
        push_status = "skipped"
        pushed = False
        push_detail = []
    else:
        report_recipients = load_report_recipients()
        results = dispatch(
            personal,
            team_text,
            no_notify=False,
            team_recipients=report_recipients,
        )
        expected = {f"personal:{member}" for member in personal} | {"team"}
        if report_recipients:
            expected.add("team:report_recipients")
        delivered = all_delivered(expected, results)
        if not results:
            push_status = "no_channel"
        elif delivered:
            push_status = "ok"
        elif any(results.values()):
            push_status = "partial"
        else:
            push_status = "failed"
        pushed = delivered if push_status == "ok" else False
        member_emails = load_member_emails()
        push_detail = []
        for scope in expected:
            ok = results.get(scope, False)
            error = ""
            if not ok and scope not in results:
                if scope.startswith("personal:"):
                    error = "no_recipient"
                elif scope == "team:report_recipients":
                    error = "no_recipient"
                elif scope == "team" and not load_config().feishu_webhook_url:
                    error = "no_channel"
            elif not ok and scope.startswith("personal:"):
                member = scope.removeprefix("personal:")
                if not member_emails.get(member):
                    error = "no_recipient"
            push_detail.append({"scope": scope, "ok": ok, "error": error})

    return {
        "date": day.isoformat(),
        "source": reasons,
        "members": len(groups),
        "items": len(items),
        "saved_reports": saved,
        "pushed": pushed,
        "push_status": push_status,
        "push_detail": push_detail,
        "team_report": team_text,
    }
