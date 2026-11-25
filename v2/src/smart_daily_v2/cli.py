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
"""

from __future__ import annotations

import argparse
import sqlite3
from collections.abc import Sequence
from datetime import date, datetime

from smart_daily_v2 import orchestrator, storage
from smart_daily_v2.config import load_config
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


def _parse_day(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("日期格式应为 YYYY-MM-DD") from exc


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
    return parser


def _sources(args: argparse.Namespace) -> list[object]:
    if args.mock:
        # TK-V2-902 验收④：--mock 样例含考勤条目（默认 MockSource 行为不变）。
        return [MockSource(include_attendance=True)]
    if args.source is not None:
        source_type = SOURCE_TYPES[args.source]
        return [source_type() if args.source == "mock" else source_type.from_env()]
    return [GithubSource.from_env(), FeishuTaskSource.from_env(), FeishuChatSource.from_env()]


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


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
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
