"""成员账号名→中文显示名映射的 TDD 红/绿用例（范围外新增，状态 ☐ 待确认）。

映射落编排层：orchestrator.run() 采集后、group_by_member 前替换 item.member，
下游分组/日报/落库/推送/查询自动生效。本文件只描述契约，不裁定组内口径。
"""

from datetime import date, datetime, time
from pathlib import Path

import smart_daily_v2.orchestrator as orchestrator_module
from smart_daily_v2.models import LOCAL_TZ, WorkItem, local_date

DAY = date(2026, 11, 19)
MAPPING = "fh0709:方赫,yjy120:杨佳莹,yuyue117:于悦,zhaorui715:赵蕊"
ZH_NAMES = ("方赫", "杨佳莹", "于悦", "赵蕊")
ACCOUNTS = ("fh0709", "yjy120", "yuyue117", "zhaorui715")


def _item(record_id: str, member: str, *, hour: int = 9) -> WorkItem:
    occurred_at = datetime.combine(DAY, time(hour), tzinfo=LOCAL_TZ)
    return WorkItem(
        record_id=record_id,
        source="github",
        member=member,
        kind="commit",
        title=f"t-{record_id}",
        detail="",
        occurred_at=occurred_at,
        local_day=local_date(occurred_at),
    )


def _source(items: list[WorkItem]):
    class FakeSource:
        name = "fake"

        def collect(self, *, since, until, author=None):
            return items

    return FakeSource()


def _capture_persist(monkeypatch) -> list[tuple[str, str]]:
    seen: list[tuple[str, str]] = []

    def fake_persist(member, body, item_count, day, source):
        seen.append((member, body))

    monkeypatch.setattr(orchestrator_module, "_persist_report", fake_persist)
    return seen


def test_display_name_team_report_and_personal_use_chinese(monkeypatch):
    monkeypatch.setenv("MEMBER_DISPLAY_NAMES", MAPPING)
    seen = _capture_persist(monkeypatch)
    items = [_item(f"r{index}", acc, hour=index) for index, acc in enumerate(ACCOUNTS)]
    result = orchestrator_module.run(DAY, sources=[_source(items)], notify=False)

    team = result["team_report"]
    for zh in ZH_NAMES:
        assert zh in team, f"团队日报缺中文名 {zh}"
    for acc in ACCOUNTS:
        assert acc not in team, f"团队日报仍含账号名 {acc}"

    assert result["members"] == 4
    assert {member for member, _ in seen} == set(ZH_NAMES)
    for member, body in seen:
        assert member in body.splitlines()[0], f"个人日报标题未用中文名: {member}"


def test_display_name_case_and_space_insensitive(monkeypatch):
    monkeypatch.setenv("MEMBER_DISPLAY_NAMES", MAPPING)
    seen = _capture_persist(monkeypatch)
    result = orchestrator_module.run(
        DAY, sources=[_source([_item("r1", " FH0709 ")])], notify=False
    )
    assert "方赫" in result["team_report"]
    assert {member for member, _ in seen} == {"方赫"}


def test_display_name_unmapped_falls_back_with_warning(monkeypatch, capsys):
    monkeypatch.setenv("MEMBER_DISPLAY_NAMES", MAPPING)
    seen = _capture_persist(monkeypatch)
    result = orchestrator_module.run(
        DAY, sources=[_source([_item("r1", "unknown_login")])], notify=False
    )
    assert result["items"] == 1
    assert "unknown_login" in result["team_report"]
    assert {member for member, _ in seen} == {"unknown_login"}
    assert "未映射" in capsys.readouterr().out, "未命中应产生可观测告警"


def test_display_name_guard_source_layout():
    root = Path(orchestrator_module.__file__).parent
    identity_src = (root / "identity.py").read_text(encoding="utf-8")
    orchestrator_src = (root / "orchestrator.py").read_text(encoding="utf-8")

    # 检查串拼接构造，规避自检自指（602/可用性/author 批次的坑）
    fn_def = "def " + "display_name"
    fn_call = "display_name" + "("
    banned = (
        "lookup" + "_display_name",
        "ghp" + "_",
        "xoxb" + "-",
        "@qq" + ".com",
        "@gmail" + ".com",
        "open.feishu" + ".cn",
    )
    assert fn_def in identity_src, "identity.py 应有 display_name 定义"
    assert fn_call in orchestrator_src, "orchestrator.py 应调用 display_name"
    for token in banned:
        assert token not in identity_src, f"identity.py 含敏感字面量: {token}"
        assert token not in orchestrator_src, f"orchestrator.py 含敏感字面量: {token}"
    assert "待确认" in identity_src and "待确认" in orchestrator_src
    assert "已裁定" not in identity_src and "已裁定" not in orchestrator_src


def test_display_name_no_mapping_keeps_accounts(monkeypatch):
    monkeypatch.delenv("MEMBER_DISPLAY_NAMES", raising=False)
    seen = _capture_persist(monkeypatch)
    items = [_item(f"r{index}", acc, hour=index) for index, acc in enumerate(ACCOUNTS)]
    result = orchestrator_module.run(DAY, sources=[_source(items)], notify=False)

    team = result["team_report"]
    for acc in ACCOUNTS:
        assert acc in team, f"无映射配置时仍应保留账号名 {acc}"
    assert {member for member, _ in seen} == set(ACCOUNTS)
