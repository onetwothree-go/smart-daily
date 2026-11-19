from pathlib import Path

import pytest

from smart_daily_v2.identity import normalize_key, normalize_members


def test_case_whitespace_variants_merge_to_one_group(identity_harness):
    outcome = identity_harness()

    assert len(outcome.groups) == 1
    assert list(outcome.groups) == [normalize_key("MemberA")]
    assert outcome.groups[normalize_key("MemberA")] == [
        "MemberA",
        " memberA ",
        "MEMBERA",
    ]
    assert len(outcome.groups[normalize_key("MemberA")]) == 3


def test_record_ids_disjoint_and_no_merge_loss(identity_harness):
    outcome = identity_harness()
    team_entry_lines = [line for line in outcome.team.splitlines() if line.startswith("- [")]

    assert len(outcome.record_ids) == 3
    assert len(set(outcome.record_ids)) == 3
    assert len(outcome.member_groups) == 1
    assert len(next(iter(outcome.member_groups.values()))) == 3
    assert len(team_entry_lines) == 3


def test_different_people_not_merged(identity_harness):
    outcome = identity_harness(["MemberA", "memberb", " MEMBERA "])

    assert len(outcome.groups) == 2
    assert outcome.groups["membera"] == ["MemberA", " MEMBERA "]
    assert outcome.groups["memberb"] == ["memberb"]


def test_none_identity_raises_type_error(identity_harness):
    outcome = identity_harness()

    assert len(outcome.groups) == 1
    with pytest.raises(TypeError):
        normalize_key(None)
    with pytest.raises(TypeError):
        normalize_members(["MemberA", None])


def test_empty_and_whitespace_not_silently_dropped(identity_harness):
    outcome = identity_harness(["", "   ", "MemberA"])

    assert "" in outcome.groups
    assert len(outcome.groups[""]) == 2
    assert sum(len(identities) for identities in outcome.groups.values()) == 3
    assert len(outcome.items) == 3


def test_unmapped_identity_warns_and_not_dropped(identity_harness):
    outcome = identity_harness(extra_unmapped=("ghost_login",))

    assert outcome.resolved["ghost_login"] == "ghost_login"
    assert "ghost_login" in outcome.all_logins
    assert len(outcome.warnings) == 1
    assert "身份未映射" in outcome.warnings[0]
    assert outcome.resolved["MemberA"] == "甲"


def test_mapped_identity_does_not_warn(identity_harness):
    outcome = identity_harness()

    assert outcome.warnings == []
    assert set(outcome.resolved.values()) == {"甲"}
    assert len(outcome.resolved) == 3


def test_fixture_reconciliation_and_scope_registration(identity_harness):
    first = identity_harness()
    second = identity_harness()
    conftest_text = (Path(__file__).parent / "conftest.py").read_text(encoding="utf-8")

    assert first.record_ids == second.record_ids
    assert first.normalized_keys == [normalize_key(identity) for identity in first.raw_identities]
    assert "501" in conftest_text
    assert "端到端复验" in conftest_text
    assert "lookup_display_name" in conftest_text
