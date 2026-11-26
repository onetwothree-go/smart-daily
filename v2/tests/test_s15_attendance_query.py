"""S15 按人按月查考勤（演练用例，第 4 周现场改造靶子）。

需求条目：proposal 0.5-diff 0.5 S15（`--list` 之外新增 CLI 查询子命令）。
契约口径（演练结论，待 design 定案前不视为已定，开放问题 #11）：
- 参数：``--attendance`` 进入查询模式；``--member`` 与 ``--month`` 必填；
  ``--mock`` 走无凭证夹具，``--source`` 只接受 ``feishu_attendance``。
- 输出：TSV 五列「日期 / 成员 / 状态 / 时刻 / record_id」，按时刻升序。
- 退出码：沿用既有四值表（0 成功 / 1 采集失败 / 2 参数错误），不新增退出码。
- 隐私：只呈现打卡事实与 record_id，不输出定位、WiFi、设备信息（I30 / 裁决 2A 上限）。
"""

from datetime import date, datetime

import pytest

import smart_daily_v2.cli as cli
from smart_daily_v2.models import LOCAL_TZ, WorkItem, local_date
from smart_daily_v2.sources.base import SourceUnavailableError

HEADER = ["日期", "成员", "状态", "时刻", "record_id"]


def _run(capsys, argv: list[str]) -> tuple[int, str, str]:
    code = cli.main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def _rows(stdout: str) -> list[list[str]]:
    lines = [line for line in stdout.splitlines() if line.strip()]
    return [line.split("\t") for line in lines]


def test_lists_only_requested_member_records(cleared_env, capsys):
    code, out, _ = _run(capsys, ["--attendance", "--member", "甲", "--month", "2026-11", "--mock"])
    rows = _rows(out)
    assert code == 0
    assert rows[0] == HEADER
    assert [row[1] for row in rows[1:]] == ["甲"]
    assert [row[4] for row in rows[1:]] == ["mock-att-001"]
    assert "乙" not in out


def test_output_is_five_columns_without_privacy_fields(cleared_env, capsys):
    _, out, _ = _run(capsys, ["--attendance", "--member", "甲", "--month", "2026-11", "--mock"])
    body = _rows(out)[1:]
    assert body
    assert all(len(row) == 5 for row in body)
    for forbidden in ("WiFi", "wifi", "设备", "定位", "device"):
        assert forbidden not in out


def test_rows_ordered_by_time_ascending(cleared_env, capsys):
    _, out, _ = _run(capsys, ["--attendance", "--member", "甲", "--month", "2026-11", "--mock"])
    stamps = [row[3] for row in _rows(out)[1:]]
    assert stamps == sorted(stamps)


def test_member_without_records_exits_zero_and_says_so(cleared_env, capsys):
    code, out, err = _run(
        capsys, ["--attendance", "--member", "丁", "--month", "2026-11", "--mock"]
    )
    assert code == 0
    assert out.strip() == ""
    assert "无考勤记录" in err


def test_month_outside_records_exits_zero(cleared_env, capsys):
    code, out, err = _run(
        capsys, ["--attendance", "--member", "甲", "--month", "2026-12", "--mock"]
    )
    assert code == 0
    assert out.strip() == ""
    assert "无考勤记录" in err


@pytest.mark.parametrize(
    "argv",
    [
        ["--attendance", "--month", "2026-11", "--mock"],
        ["--attendance", "--member", "甲", "--mock"],
        ["--attendance", "--member", "甲", "--month", "2026-13", "--mock"],
        ["--attendance", "--member", "甲", "--month", "2026-11/", "--mock"],
    ],
)
def test_missing_or_bad_arguments_exit_two(cleared_env, capsys, argv):
    code, _, err = _run(capsys, argv)
    assert code == 2
    assert err.strip() != ""


def test_non_attendance_source_rejected(cleared_env, capsys):
    code, _, err = _run(
        capsys, ["--attendance", "--member", "甲", "--month", "2026-11", "--source", "github"]
    )
    assert code == 2
    assert "feishu_attendance" in err


def test_attendance_and_list_are_mutually_exclusive(cleared_env, capsys):
    code, _, err = _run(capsys, ["--attendance", "--list", "--member", "甲", "--month", "2026-11"])
    assert code == 2
    assert err.strip() != ""


def test_collect_failure_exits_one(cleared_env, monkeypatch, capsys):
    class _Boom:
        name = "feishu_attendance"
        member_map = {"u-1": "甲"}

        @classmethod
        def from_env(cls):
            return cls()

        def collect(self, *, since, until, author=None):
            raise SourceUnavailableError("feishu_attendance", "凭证未配置：FEISHU_APP_ID")

    monkeypatch.setattr(cli, "FeishuAttendanceSource", _Boom)
    code, _, err = _run(capsys, ["--attendance", "--member", "甲", "--month", "2026-11"])
    assert code == 1
    assert "采集失败" in err


def test_missing_member_map_exits_one_instead_of_faking_empty(cleared_env, monkeypatch, capsys):
    """映射为空时接口必返空集：不能把配置缺失伪装成「无考勤记录」（exit 0）。"""

    class _NoMap:
        name = "feishu_attendance"
        member_map: dict[str, str] = {}

        @classmethod
        def from_env(cls):
            return cls()

        def collect(self, *, since, until, author=None):
            raise AssertionError("映射为空时不应发起采集")

    monkeypatch.setattr(cli, "FeishuAttendanceSource", _NoMap)
    code, out, err = _run(capsys, ["--attendance", "--member", "甲", "--month", "2026-11"])
    assert code == 1
    assert out.strip() == ""
    assert "FEISHU_ATTENDANCE_MEMBER_MAP" in err
    assert "无考勤记录" not in err


def test_member_not_in_map_exits_two(cleared_env, monkeypatch, capsys):
    class _MapOnlyJia:
        name = "feishu_attendance"
        member_map = {"u-1": "甲"}

        @classmethod
        def from_env(cls):
            return cls()

        def collect(self, *, since, until, author=None):
            raise AssertionError("映射未命中成员时不应发起采集")

    monkeypatch.setattr(cli, "FeishuAttendanceSource", _MapOnlyJia)
    code, _, err = _run(capsys, ["--attendance", "--member", "戊", "--month", "2026-11"])
    assert code == 2
    assert "映射表内" in err


def test_default_source_is_attendance_source(cleared_env, monkeypatch, capsys):
    """不给 --mock / --source 时默认走真实考勤源（from_env），不是四源默认链。"""
    calls: list[tuple[datetime, datetime]] = []

    class _Stub:
        name = "feishu_attendance"
        member_map = {"u-x": "甲"}

        @classmethod
        def from_env(cls):
            calls.append(("from_env", None))
            return cls()

        def collect(self, *, since, until, author=None):
            calls.append((since, until))
            occurred = datetime(2026, 11, 20, 9, 0, tzinfo=LOCAL_TZ)
            return [
                WorkItem(
                    record_id="real-001",
                    source="feishu_attendance",
                    member="甲",
                    kind="attendance",
                    title="考勤：正常",
                    detail="出勤状态：正常\nrecord_id: real-001",
                    occurred_at=occurred,
                    local_day=local_date(occurred),
                )
            ]

    monkeypatch.setattr(cli, "FeishuAttendanceSource", _Stub)
    code, out, _ = _run(capsys, ["--attendance", "--member", "甲", "--month", "2026-11"])
    assert code == 0
    assert calls[0] == ("from_env", None)
    since, until = calls[1]
    assert since == datetime(2026, 11, 1, 0, 0, tzinfo=LOCAL_TZ)
    assert until == datetime(2026, 11, 30, 23, 59, 59, 999999, tzinfo=LOCAL_TZ)
    assert _rows(out)[1] == ["2026-11-20", "甲", "正常", "09:00", "real-001"]


def test_status_and_time_extracted_for_real_nested_record(cleared_env, capsys):
    """真实格式的 title 前缀固定「考勤：」，状态直取；时刻按东八区格式化。"""
    code, out, _ = _run(capsys, ["--attendance", "--member", "丙", "--month", "2026-11", "--mock"])
    rows = _rows(out)
    assert code == 0
    assert rows[1] == ["2026-11-18", "丙", "正常", "09:02", "mock-att-002"]


def test_query_does_not_touch_report_history(cleared_env, monkeypatch, capsys):
    """查询模式不得读写日报历史表（与 --list 分属两类查询）。"""

    def _boom(*args, **kwargs):
        raise AssertionError("--attendance 不应触碰日报历史")

    monkeypatch.setattr(cli, "_list_reports", _boom)
    code, _, _ = _run(capsys, ["--attendance", "--member", "甲", "--month", "2026-11", "--mock"])
    assert code == 0


def test_month_boundaries_are_inclusive(cleared_env, monkeypatch, capsys):
    """月初 00:00 与月末 23:59:59 的记录都要算入当月。"""
    from smart_daily_v2.sources.mock import MockSource

    first = datetime(2026, 11, 1, 0, 0, tzinfo=LOCAL_TZ)
    last = datetime(2026, 11, 30, 23, 59, 59, tzinfo=LOCAL_TZ)
    items = [
        WorkItem(
            "b-1",
            "feishu_attendance",
            "甲",
            "attendance",
            "考勤：正常",
            "x",
            first,
            date(2026, 11, 1),
        ),
        WorkItem(
            "b-2",
            "feishu_attendance",
            "甲",
            "attendance",
            "考勤：迟到",
            "x",
            last,
            date(2026, 11, 30),
        ),
    ]

    def collect(self, *, since, until, author=None):
        return [
            item
            for item in items
            if since <= item.occurred_at <= until and (author is None or item.member == author)
        ]

    monkeypatch.setattr(MockSource, "collect", collect)
    code, out, _ = _run(capsys, ["--attendance", "--member", "甲", "--month", "2026-11", "--mock"])
    assert code == 0
    assert [row[4] for row in _rows(out)[1:]] == ["b-1", "b-2"]
