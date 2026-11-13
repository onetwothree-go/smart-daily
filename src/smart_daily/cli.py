"""命令行入口

用法：
    uv run --env-file .env python -m smart_daily.cli             # 正常跑
    uv run --env-file .env python -m smart_daily.cli --mock      # 用演示数据源
    uv run --env-file .env python -m smart_daily.cli --no-notify # 只生成不推送
    uv run --env-file .env python -m smart_daily.cli --source mock
"""

# --- 答辩口径 · 命令行入口（四层架构第 4 层，见答辩稿 2.6.1）---
# 参数：--day / --no-notify / --source / --mock / --list
# 退出码四态：0 成功或只查询、1 采集或落库失败、2 参数格式错（argparse）、3 推送失败
# 依据 specs/design.md 3.4：22:00 计划任务靠退出码判断成败，推送失败绝不能返回 0；
# --no-notify 只生成不推送，现场演示一律用它，避免把测试日报发到群里。

from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import date, datetime, timezone

from .collectors.base import SourceUnavailableError
from .collectors.mock import MockCollector
from .orchestrator import DailyReportOrchestrator


def _day_arg(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"日期格式应为 YYYY-MM-DD：{value}") from exc


_PUSH_FAIL = {"partial", "failed", "no_channel"}


def _exit_code(push_status: str) -> int:
    """按 design 3.4 四码表把 push_status 映射为进程退出码（0 / 3）。"""
    return 3 if push_status in _PUSH_FAIL else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="smart_daily",
        description="智能日报生成器 —— 采集 → 生成 → 推送",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="强制使用演示数据源（不依赖任何凭证，用于演示与测试）",
    )
    parser.add_argument(
        "--source",
        choices=["mock", "local-git"],
        help="指定数据源。不指定则按 GitHub → 飞书 → 本地 Git 的顺序自动降级",
    )
    parser.add_argument(
        "--no-notify",
        action="store_true",
        help="只生成日报并落库，不做任何推送",
    )
    parser.add_argument(
        "--day",
        type=_day_arg,
        help="报告日期，格式 YYYY-MM-DD。默认取数据中最新一条的时间",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="列出已保存的日报历史，不执行采集",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    # ---- 历史查询模式 ----
    if args.list:
        orch = DailyReportOrchestrator.__new__(DailyReportOrchestrator)
        orch.db_path = __import__("pathlib").Path(
            __import__("os").getenv("DB_PATH", "data/daily_report.db")
        )
        rows = orch.list_reports(args.day)
        if not rows:
            print("尚无已保存的日报记录")
            return 0
        print(f"{'日期':<12}{'成员':<12}{'条目':<6}{'数据源':<12}{'保存时间'}")
        print("-" * 66)
        for r in rows:
            print(
                f"{r['report_date']:<12}{r['member']:<12}{r['item_count']:<6}"
                f"{str(r['source_name'] or ''):<12}{r['created_at'][:19]}"
            )
        return 0

    # ---- 组装数据源 ----
    sources = None
    if args.mock or args.source == "mock":
        sources = [MockCollector()]
        print("[source] 使用演示数据源（mock）")
    elif args.source == "local-git":
        from pathlib import Path

        from .collectors.local_git import LocalGitCollector

        sources = [LocalGitCollector(Path.cwd())]
        print("[source] 使用本地 Git 数据源")

    orch = DailyReportOrchestrator(sources=sources)

    try:
        result = orch.run(day=args.day, notify=not args.no_notify)
    except (SourceUnavailableError, OSError, sqlite3.Error) as exc:
        print(f"[error] 采集或落库失败：{exc}")
        return 1

    print("\n" + "=" * 60)
    print(f"数据源    : {result['source']}")
    print(f"报告日期  : {result['date']}")
    print(f"成员数    : {result['members']}")
    print(f"条目数    : {result['items']}")
    print(f"已保存    : {result['saved_reports']} 份")
    print(f"已推送    : {result['pushed']}")
    print(f"推送状态  : {result['push_status']}")
    print("=" * 60)

    detail = result.get("push_detail") or []
    if detail:
        print("推送明细：")
        for d in detail:
            flag = "OK " if d.get("ok") else "FAIL"
            print(f"  [{flag}] {d.get('channel')} -> {d.get('scope')}")
        print("-" * 60)

    print(result["team_report"])

    if args.no_notify:
        return 0
    return _exit_code(result["push_status"])


if __name__ == "__main__":
    sys.exit(main())
