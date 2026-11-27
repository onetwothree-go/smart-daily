"""Command-line entry point for daily report runs and history.

Exit codes (the same table is shown by --help):
退出码 | 含义
0 | 成功
1 | 采集或落库失败
2 | 参数错误
3 | 推送存在失败项

Scope registrations (☐ 待确认，组内):
- C5 / G6 persistence wiring temporarily forwards _persist_report at the CLI boundary;
  orchestrator remains storage-independent. ☐ 待确认：落库接线落点
- The default DB_PATH value comes from configuration and remains unresolved.
  ☐ 待确认：db_path 默认值
- source_name stores joined fallback reasons, or "orchestrated" when empty.
  ☐ 待确认：source_name 拼接规则
- Delivery expectations use run()'s current result; the additional K6 recipient
  channel is not wired by this CLI. ☐ 待确认：K6 送达 6 条未注入
- --source accepts github, feishu_task, feishu_chat, feishu_attendance, or mock;
  the final source set remains unresolved. ☐ 待组内确认
- TK-V2-902：feishu_attendance 为第五源（design §4-4），--mock 样例含考勤条目；
  考勤在 orchestrator 走独立支路（design §4-3），失败留痕不中断。
- The exit-code table is documented here and shown verbatim in --help; the intended
  external documentation location remains unresolved. ☐ 待组内确认
- K8 is inherited: AllSourcesUnavailableError derives from SourceUnavailableError.
- S15（演练，开放问题 #11 待 design 定案）：``--attendance`` 新增「按人按月查考勤」
  查询子命令，与 ``--list``（历史日报）并列且互斥。查询口径：``--member`` +
  ``--month`` 必填；默认走 feishu_attendance，``--mock`` 走无凭证夹具；输出 TSV
  五列「日期/成员/状态/时刻/record_id」按时刻升序；无记录 exit 0 并在 stderr 提示。
  沿用既有四值退出码表，不新增退出码；只呈现打卡事实，不输出定位/WiFi/设备（I30）。
"""

from __future__ import annotations

import argparse
import re
import sqlite3
import sys
from collections.abc import Sequence
from datetime import date, datetime, timedelta

from smart_daily_v2 import orchestrator, storage
from smart_daily_v2.config import load_config
from smart_daily_v2.identity import normalize_key
from smart_daily_v2.models import LOCAL_TZ
from smart_daily_v2.sources.attendance import FeishuAttendanceSource
from smart_daily_v2.sources.base import SourceUnavailableError
from smart_daily_v2.sources.feishu_chat import FeishuChatSource
from smart_daily_v2.sources.feishu_tasks import FeishuTaskSource
from smart_daily_v2.sources.github import GithubSource
from smart_daily_v2.sources.mock import MockSource

EXIT_CODE_TABLE = """退出码 | 含义
0 | 成功
1 | 采集或落库失败
2 | 参数错误
3 | 推送存在失败项"""

SOURCE_TYPES = {
    "github": GithubSource,
    "feishu_task": FeishuTaskSource,
    "feishu_chat": FeishuChatSource,
    "mock": MockSource,
    # TK-V2-902（design §4-4 定案）：第五源，可用 --source 单独跑考勤。
    "feishu_attendance": FeishuAttendanceSource,
}

# S15 查询输出列：只呈现打卡事实与 record_id，不呈现定位/WiFi/设备信息（I30）。
ATTENDANCE_HEADER: tuple[str, ...] = ("日期", "成员", "状态", "时刻", "record_id")
_MONTH_PATTERN = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def _parse_day(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("日期格式应为 YYYY-MM-DD") from exc


def _month_bounds(value: str) -> tuple[datetime, datetime]:
    """YYYY-MM → 当月东八区闭区间 [月初 00:00:00, 月末 23:59:59.999999]。

    月末用「次月月初 − 1 微秒」，避免手工写 28/29/30/31 与闰年分支。
    """
    if not _MONTH_PATTERN.match(value):
        raise ValueError("月份格式应为 YYYY-MM")
    year, month = (int(part) for part in value.split("-"))
    since = datetime(year, month, 1, tzinfo=LOCAL_TZ)
    next_month = (
        datetime(year + 1, 1, 1, tzinfo=LOCAL_TZ)
        if month == 12
        else datetime(year, month + 1, 1, tzinfo=LOCAL_TZ)
    )
    return since, next_month - timedelta(microseconds=1)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=EXIT_CODE_TABLE,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    source_options = parser.add_mutually_exclusive_group()
    source_options.add_argument("--mock", action="store_true", help="使用无凭证演示数据")
    source_options.add_argument(
        "--source",
        choices=tuple(SOURCE_TYPES),
        help="只使用指定数据源",
    )
    parser.add_argument("--no-notify", action="store_true", help="运行日报但不推送")
    parser.add_argument("--day", type=_parse_day, help="日报日期（YYYY-MM-DD）")
    parser.add_argument("--list", action="store_true", help="查询历史日报")
    parser.add_argument(
        "--attendance",
        action="store_true",
        help="按人按月查询考勤记录（S15，需 --member 与 --month）",
    )
    parser.add_argument("--member", help="考勤查询的成员姓名（配合 --attendance）")
    parser.add_argument("--month", help="考勤查询的月份 YYYY-MM（配合 --attendance）")
    return parser


def _sources(args: argparse.Namespace) -> list[object]:
    if args.mock:
        # TK-V2-902 验收④：--mock 样例含考勤条目（默认 MockSource 行为不变）。
        return [MockSource(include_attendance=True)]
    if args.source is not None:
        source_type = SOURCE_TYPES[args.source]
        return [source_type() if args.source == "mock" else source_type.from_env()]
    # 默认源含考勤：22:00 自动日报（run_daily.ps1 不带 --source）因此能在报告中
    # 出现「考勤」行；凭证/映射未齐时考勤走 orchestrator 独立支路降级留痕，不中断主流程。
    return [
        GithubSource.from_env(),
        FeishuTaskSource.from_env(),
        FeishuChatSource.from_env(),
        FeishuAttendanceSource.from_env(),
    ]


def _print_reports(reports) -> None:
    member_order = {member: index for index, member in enumerate(("甲", "乙", "丙", "丁"))}
    ordered_reports = sorted(
        reports,
        key=lambda report: (
            -date.fromisoformat(report.report_date).toordinal(),
            member_order.get(report.member, len(member_order)),
            report.member,
        ),
    )
    for report in ordered_reports:
        print(
            f"{report.report_date}\t{report.member}\t{report.item_count}\t"
            f"{report.source_name or ''}"
        )


def _list_reports(day: date | None) -> int:
    try:
        conn = sqlite3.connect(load_config().db_path)
        try:
            _print_reports(storage.list_reports(conn, day=day))
        finally:
            close = getattr(conn, "close", None)
            if callable(close):
                close()
    except sqlite3.OperationalError as exc:
        if "no such table: daily_reports" in str(exc):
            return 0
        print(f"查询历史失败：{exc}", file=__import__("sys").stderr)
        return 1
    except sqlite3.Error as exc:
        print(f"查询历史失败：{exc}", file=__import__("sys").stderr)
        return 1
    return 0


def _attendance_status(item) -> str:
    """出勤状态：优先取 title「考勤：X」前缀，回退 detail 的「出勤状态：X」行。"""
    title = item.title
    if title.startswith("考勤："):
        return title.removeprefix("考勤：")
    for line in item.detail.splitlines():
        if line.startswith("出勤状态："):
            return line.removeprefix("出勤状态：")
    return ""


def _attendance_query(args: argparse.Namespace) -> int:
    """S15 按人按月查考勤（只读查询，不落库、不碰日报历史表）。"""
    if args.member is None or args.month is None:
        print("参数错误：--attendance 需同时给出 --member 与 --month", file=sys.stderr)
        return 2
    try:
        since, until = _month_bounds(args.month)
    except ValueError:
        print("参数错误：--month 格式应为 YYYY-MM", file=sys.stderr)
        return 2
    if args.source is not None and args.source != "feishu_attendance":
        print(
            "参数错误：--attendance 只接受 --source feishu_attendance 或 --mock",
            file=sys.stderr,
        )
        return 2

    target = normalize_key(args.member)
    source = MockSource(include_attendance=True) if args.mock else FeishuAttendanceSource.from_env()
    if not args.mock:
        # 真实源按 user_ids 批量查询，空映射会让接口返回空集——若直接输出「无考勤记录」
        # 会把配置缺失伪装成业务结论（演练发现的坑，契约待定项之一）。
        member_map = getattr(source, "member_map", None) or {}
        if not member_map:
            print(
                "采集失败：FEISHU_ATTENDANCE_MEMBER_MAP 未配置，无法按人查询考勤",
                file=sys.stderr,
            )
            return 1
        if not any(normalize_key(name) == target for name in member_map.values()):
            print(
                f"参数错误：{args.member} 不在 FEISHU_ATTENDANCE_MEMBER_MAP 映射表内",
                file=sys.stderr,
            )
            return 2

    try:
        items = source.collect(since=since, until=until, author=args.member)
    except SourceUnavailableError as exc:
        print(f"采集失败：{exc}", file=sys.stderr)
        return 1

    # 采集器的 author 形参不保证被消费（FeishuAttendanceSource 当前忽略它），
    # 查询层按 normalize_key 再过滤一次，避免把全组考勤当成某人的记录。
    rows = [
        item for item in items if item.kind == "attendance" and normalize_key(item.member) == target
    ]
    if not rows:
        print(f"{args.month} 该成员无考勤记录", file=sys.stderr)
        return 0

    print("\t".join(ATTENDANCE_HEADER))
    for item in sorted(rows, key=lambda row: row.occurred_at):
        stamp = item.occurred_at.astimezone(LOCAL_TZ)
        print(
            "\t".join(
                (
                    item.local_day.isoformat(),
                    item.member,
                    _attendance_status(item),
                    stamp.strftime("%H:%M"),
                    item.record_id,
                )
            )
        )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.attendance and args.list:
        print("参数错误：--attendance 与 --list 不能同时使用", file=sys.stderr)
        return 2
    if args.attendance:
        return _attendance_query(args)
    if args.list:
        return _list_reports(args.day)

    day = args.day or datetime.now(LOCAL_TZ).date()
    try:
        conn = sqlite3.connect(load_config().db_path)
    except sqlite3.Error as exc:
        print(f"采集或落库失败：{exc}", file=__import__("sys").stderr)
        return 1

    original_persist = orchestrator._persist_report

    def _persisting(member, text, item_count, report_day, source):
        source_name = (
            ", ".join(source)
            if isinstance(source, (list, tuple))
            else str(source or "orchestrated")
        )
        storage.save_report(conn, report_day, member, text, item_count, source_name)

    orchestrator._persist_report = _persisting
    try:
        result = orchestrator.run(
            day,
            sources=_sources(args),
            notify=not args.no_notify,
        )
        conn.commit()
    except SourceUnavailableError as exc:
        print(f"采集或落库失败：{exc}", file=__import__("sys").stderr)
        return 1
    except sqlite3.Error as exc:
        print(f"采集或落库失败：{exc}", file=__import__("sys").stderr)
        return 1
    finally:
        orchestrator._persist_report = original_persist
        conn.close()

    if args.no_notify:
        return 0
    if result["push_status"] in {"partial", "failed", "no_channel"}:
        return 3
    if result["push_status"] in {"ok", "skipped"}:
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
