"""CLI usability regression tests (☐ 待确认).

C5 落库接线 uses G6 placeholders and temporary databases only.
"""

import inspect
import sqlite3
import subprocess
import sys
from datetime import date
from pathlib import Path

DAY = date(2026, 11, 19)
MEMBERS = ("甲", "乙", "丙", "丁")


def _configure_real_run(monkeypatch, cli, items=None):
    from datetime import timedelta

    import smart_daily_v2.orchestrator as orchestrator
    from smart_daily_v2.models import local_date
    from smart_daily_v2.sources.mock import load_fixture_items

    selected_items = load_fixture_items() if items is None else items
    if items is None:
        selected_items = [
            type(item)(
                record_id=item.record_id,
                source=item.source,
                member=item.member,
                kind=item.kind,
                title=item.title,
                detail=item.detail,
                occurred_at=item.occurred_at + timedelta(days=1),
                local_day=local_date(item.occurred_at + timedelta(days=1)),
            )
            for item in selected_items
        ]
    monkeypatch.setattr(
        orchestrator,
        "collect_with_fallback",
        lambda sources, *, since, until, author=None: (selected_items, []),
    )
    monkeypatch.setattr(
        orchestrator,
        "dispatch",
        lambda personal, team, *, no_notify=False, team_recipients=(): {},
    )
    return selected_items


def _database_path(monkeypatch, tmp_path: Path) -> Path:
    db_path = tmp_path / "daily-report.db"
    monkeypatch.setenv("DB_PATH", str(db_path))
    return db_path


def test_usability_module_main_guard() -> None:
    import smart_daily_v2.cli as cli

    source = Path(cli.__file__).read_text(encoding="utf-8")
    assert 'if __name__ == "__main__"' in source
    assert "raise SystemExit(main())" in source
    parameters = inspect.signature(cli.main).parameters
    assert list(parameters) == ["argv"]
    assert parameters["argv"].default is None


def test_usability_python_m_help_works() -> None:
    v2_dir = Path(__file__).parents[1]
    result = subprocess.run(
        [sys.executable, "-m", "smart_daily_v2.cli", "--help"],
        cwd=v2_dir,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    for line in (
        "0 | 成功",
        "1 | 采集或落库失败",
        "2 | 参数错误",
        "3 | 推送存在失败项",
    ):
        assert line in result.stdout


def test_usability_readme_has_run_section() -> None:
    readme = Path(__file__).parents[1] / "README.md"
    source = readme.read_text(encoding="utf-8")

    for required in (
        "运行方式",
        "--mock",
        "--list",
        "0 | 成功",
        "1 | 采集或落库失败",
        "2 | 参数错误",
        "3 | 推送存在失败项",
        "GITHUB_TOKEN",
        "DB_PATH",
    ):
        assert required in source
    assert "@" + "qq.com" not in source
    assert "@gmail" + ".com" not in source
    assert "gh" + "p_" not in source


def test_usability_mock_run_writes_reports(monkeypatch, tmp_path, cleared_env):
    import smart_daily_v2.cli as cli
    import smart_daily_v2.storage as storage

    db_path = _database_path(monkeypatch, tmp_path)
    items = _configure_real_run(monkeypatch, cli)
    assert cli.main(["--mock", "--no-notify", "--day", DAY.isoformat()]) == 0

    conn = sqlite3.connect(db_path)
    try:
        reports = storage.list_reports(conn, day=DAY)
        assert len(reports) == 4
        assert {report.member for report in reports} == set(MEMBERS)
        by_member = {report.member: report for report in reports}
        for member in MEMBERS:
            member_items = [item for item in items if item.member == member]
            assert by_member[member].item_count == len(member_items)
            assert any(
                item.title
                in conn.execute(
                    "SELECT content FROM daily_reports WHERE report_date = ? AND member = ?",
                    (DAY.isoformat(), member),
                ).fetchone()[0]
                for item in member_items
            )
    finally:
        conn.close()


def test_usability_persist_via_run_restores_original(monkeypatch, tmp_path, cleared_env):
    import smart_daily_v2.cli as cli

    _database_path(monkeypatch, tmp_path)
    _configure_real_run(monkeypatch, cli)
    original = cli.orchestrator._persist_report
    observed = []
    real_run = cli.orchestrator.run

    def check_hook_during_run(*args, **kwargs):
        observed.append(cli.orchestrator._persist_report is not original)
        return real_run(*args, **kwargs)

    monkeypatch.setattr(cli.orchestrator, "run", check_hook_during_run)
    assert cli.main(["--mock", "--no-notify", "--day", DAY.isoformat()]) == 0
    assert observed == [True]
    assert cli.orchestrator._persist_report is original


def test_usability_list_reads_persisted_rows(monkeypatch, tmp_path, cleared_env, capsys):
    import smart_daily_v2.cli as cli

    _database_path(monkeypatch, tmp_path)
    _configure_real_run(monkeypatch, cli)
    assert cli.main(["--mock", "--no-notify", "--day", DAY.isoformat()]) == 0
    capsys.readouterr()

    assert cli.main(["--list", "--day", DAY.isoformat()]) == 0
    output = capsys.readouterr().out
    rows = [line for line in output.splitlines() if line.strip()]
    assert len(rows) == len(MEMBERS)
    for row, member in zip(rows, MEMBERS, strict=True):
        fields = row.split("\t")
        assert fields[0] == DAY.isoformat()
        assert fields[1] == member
        assert fields[2].isdigit()


def test_usability_repeat_run_is_idempotent(monkeypatch, tmp_path, cleared_env):
    import smart_daily_v2.cli as cli
    import smart_daily_v2.storage as storage

    db_path = _database_path(monkeypatch, tmp_path)
    items = _configure_real_run(monkeypatch, cli)
    assert cli.main(["--mock", "--no-notify", "--day", DAY.isoformat()]) == 0
    items[:] = [item for item in items if item.member != MEMBERS[0]] + [
        type(items[0])(
            record_id="rec-usability-new",
            source="mock",
            member=MEMBERS[0],
            kind="commit",
            title="最新占位条目",
            detail="最新正文",
            occurred_at=items[0].occurred_at,
            local_day=DAY,
        )
    ]
    assert cli.main(["--mock", "--no-notify", "--day", DAY.isoformat()]) == 0

    conn = sqlite3.connect(db_path)
    try:
        reports = storage.list_reports(conn, day=DAY)
        assert len(reports) == 4
        assert any(item.title == "最新占位条目" for item in items if item.member == MEMBERS[0])
        content = conn.execute(
            "SELECT content FROM daily_reports WHERE report_date = ? AND member = ?",
            (DAY.isoformat(), MEMBERS[0]),
        ).fetchone()[0]
        assert "最新占位条目" in content
    finally:
        conn.close()


def test_usability_persist_failure_returns_one(monkeypatch, tmp_path, cleared_env):
    import smart_daily_v2.cli as cli

    _database_path(monkeypatch, tmp_path)
    _configure_real_run(monkeypatch, cli)
    monkeypatch.setattr(
        cli.storage,
        "save_report",
        lambda *args, **kwargs: (_ for _ in ()).throw(sqlite3.OperationalError("db locked")),
    )

    assert cli.main(["--mock", "--no-notify", "--day", DAY.isoformat()]) == 1


def test_usability_orchestrator_source_untouched() -> None:
    import smart_daily_v2.orchestrator as orchestrator

    source = Path(orchestrator.__file__).read_text(encoding="utf-8")
    for forbidden in ("sqlite3", "storage", "save_report", "from smart_daily" + " import"):
        assert forbidden not in source
    assert "待确认" in source


def test_usability_no_v1_copy_and_registration() -> None:
    import smart_daily_v2.cli as cli

    source = Path(__file__).read_text(encoding="utf-8")
    cli_source = Path(cli.__file__).read_text(encoding="utf-8")
    cli_docstring = inspect.getdoc(cli) or ""
    assert "v1" + "/src" not in source
    assert "smart_daily" + " import" not in source
    for anchor in ("C5", "落库接线", "☐ 待确认", "G6"):
        assert anchor in cli_docstring
    assert "已裁定" not in cli_docstring
    for forbidden in (
        "gh" + "p_",
        "xox" + "b-",
        "@" + "qq.com",
        "@" + "gmail.com",
        "example" + ".com",
    ):
        assert forbidden not in source
        assert forbidden not in cli_source
