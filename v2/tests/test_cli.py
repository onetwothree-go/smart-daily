import inspect
from datetime import date
from pathlib import Path

import httpx
import pytest

from smart_daily_v2.sources.base import AllSourcesUnavailableError

DAY = date(2026, 11, 19)
EXIT_CODE_TABLE = """退出码 | 含义
0 | 成功
1 | 采集或落库失败
2 | 参数错误
3 | 推送存在失败项"""


def _result(day: date, *, push_status: str = "ok") -> dict:
    return {
        "date": day.isoformat(),
        "source": [],
        "members": 0,
        "items": 0,
        "saved_reports": 0,
        "pushed": push_status == "ok",
        "push_status": push_status,
        "push_detail": [],
        "team_report": "",
    }


def _patch_run(monkeypatch, cli, *, result=None, error=None):
    calls = []

    def fake_run(day, *, sources, notify=True):
        calls.append({"day": day, "sources": sources, "notify": notify})
        if error is not None:
            raise error
        return _result(day) if result is None else result

    monkeypatch.setattr(cli.orchestrator, "run", fake_run)
    return calls


def _patch_list(monkeypatch, cli, reports=()):
    calls = []

    def fake_list_reports(conn, day=None):
        calls.append((conn, day))
        return list(reports)

    monkeypatch.setattr(cli.storage, "list_reports", fake_list_reports)
    monkeypatch.setattr(cli.sqlite3, "connect", lambda *args, **kwargs: object())
    return calls


def test_main_signature_is_module_function() -> None:
    import smart_daily_v2.cli as cli

    assert inspect.isfunction(cli.main)
    parameters = inspect.signature(cli.main).parameters
    assert list(parameters) == ["argv"]
    assert parameters["argv"].default is None
    assert inspect.signature(cli.main).return_annotation in (int, "int")


def test_list_does_not_collect_and_returns_zero(monkeypatch) -> None:
    import smart_daily_v2.cli as cli

    calls = _patch_list(monkeypatch, cli)
    run_calls = _patch_run(monkeypatch, cli)
    http_calls = []
    monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: http_calls.append(args))

    assert cli.main(["--list"]) == 0
    assert calls and http_calls == []
    assert run_calls == []


def test_list_prints_metadata_sorted_by_report_date(capsys, monkeypatch) -> None:
    import smart_daily_v2.cli as cli
    from smart_daily_v2.storage import ReportMeta

    reports = [
        ReportMeta("2026-11-20", "甲", 5, "github", "2026-11-20T00:00:00+00:00"),
        ReportMeta("2026-11-19", "乙", 2, "feishu_task", "2026-11-19T00:00:00+00:00"),
    ]
    _patch_list(monkeypatch, cli, reports)
    _patch_run(monkeypatch, cli)

    assert cli.main(["--list"]) == 0
    output = capsys.readouterr().out
    assert output.index("2026-11-20") < output.index("2026-11-19")
    for expected in ("甲", "乙", "5", "2", "github", "feishu_task"):
        assert expected in output
    assert "2026-11-20T00:00:00+00:00" not in output


def test_list_with_day_filters_without_collect(monkeypatch) -> None:
    import smart_daily_v2.cli as cli

    calls = _patch_list(monkeypatch, cli)
    run_calls = _patch_run(monkeypatch, cli)

    assert cli.main(["--list", "--day", DAY.isoformat()]) == 0
    assert len(calls) == 1
    assert calls[0][1] == DAY
    assert run_calls == []


def test_day_sets_report_date(monkeypatch) -> None:
    import smart_daily_v2.cli as cli

    calls = _patch_run(monkeypatch, cli)

    assert cli.main(["--mock", "--day", DAY.isoformat()]) == 0
    assert len(calls) == 1
    assert calls[0]["day"] == DAY


def test_default_sources_include_attendance(monkeypatch) -> None:
    """22:00 自动日报默认源须含 feishu_attendance，否则真实考勤进不了老师日报。"""
    import smart_daily_v2.cli as cli

    monkeypatch.setenv("FEISHU_APP_ID", "fake-app-id")
    monkeypatch.setenv("FEISHU_APP_SECRET", "fake-app-secret")
    monkeypatch.setenv("FEISHU_ATTENDANCE_MEMBER_MAP", "ou-a:甲")

    args = cli._build_parser().parse_args([])
    names = [source.name for source in cli._sources(args)]

    assert names == ["github", "feishu_task", "feishu_chat", "feishu_attendance"]


def test_mock_and_source_select_single_source(monkeypatch) -> None:
    import smart_daily_v2.cli as cli

    calls = _patch_run(monkeypatch, cli)

    assert cli.main(["--mock"]) == 0
    assert cli.main(["--source", "github"]) == 0
    assert len(calls) == 2
    assert [source.name for source in calls[0]["sources"]] == ["mock"]
    assert [source.name for source in calls[1]["sources"]] == ["github"]


def test_no_notify_returns_zero_and_skipped(monkeypatch) -> None:
    import smart_daily_v2.cli as cli

    result = _result(DAY, push_status="skipped")
    calls = _patch_run(monkeypatch, cli, result=result)

    assert cli.main(["--mock", "--no-notify"]) == 0
    assert calls[0]["notify"] is False
    assert result["push_status"] == "skipped"


def test_push_status_maps_exit_code_three(monkeypatch) -> None:
    import smart_daily_v2.cli as cli

    for status in ("partial", "failed", "no_channel"):
        result = _result(DAY, push_status=status)
        _patch_run(monkeypatch, cli, result=result)
        assert cli.main(["--mock"]) == 3
        assert result["pushed"] is False

    result = _result(DAY, push_status="ok")
    _patch_run(monkeypatch, cli, result=result)
    assert cli.main(["--mock"]) == 0
    assert result["pushed"] is True


def test_collect_failure_returns_one_and_argparse_error_returns_two(capsys, monkeypatch) -> None:
    import smart_daily_v2.cli as cli

    _patch_run(
        monkeypatch,
        cli,
        error=AllSourcesUnavailableError([]),
    )
    assert cli.main(["--mock"]) == 1
    error_output = capsys.readouterr().err
    assert "Traceback" not in error_output

    with pytest.raises(SystemExit) as invalid_day:
        cli.main(["--day", "not-a-day"])
    assert invalid_day.value.code == 2

    with pytest.raises(SystemExit) as invalid_source:
        cli.main(["--source", "unknown-source"])
    assert invalid_source.value.code == 2


def test_help_exit_code_table_and_docstring_registration(capsys) -> None:
    import smart_daily_v2.cli as cli

    module_source = Path(cli.__file__).read_text(encoding="utf-8")
    assert EXIT_CODE_TABLE in module_source
    for anchor in ("待确认", "0", "1", "2", "3", "push_status", "--list", "argparse"):
        assert anchor in module_source
    assert "已裁定" not in module_source
    for forbidden in (
        "from smart_daily import",
        "ghp_",
        "xoxb-",
        "@qq.com",
        "@gmail.com",
        "https://open.feishu.cn",
    ):
        assert forbidden not in module_source

    with pytest.raises(SystemExit) as help_exit:
        cli.main(["--help"])
    assert help_exit.value.code == 0
    help_output = capsys.readouterr().out
    assert EXIT_CODE_TABLE in help_output
