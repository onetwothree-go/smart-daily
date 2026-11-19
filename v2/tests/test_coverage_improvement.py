"""测试用例以改进覆盖率"""

import os
from unittest.mock import patch

import pytest

from smart_daily_v2.config import require_credential
from smart_daily_v2.models import CommitEntry, WorkItem, normalize


def test_require_credential_missing():
    """测试 require_credential 在缺少凭证时抛出异常"""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match="Missing required credential"):
            require_credential("GITHUB_TOKEN")


def test_normalize_workitem_passthrough():
    """测试 normalize 函数对 WorkItem 输入的原样放行（G7 幂等）"""
    workitem = WorkItem(
        record_id="test-123",
        source="github",
        member="testuser",
        kind="commit",
        title="Test commit",
        detail="Test detail",
        occurred_at="2026-11-19T10:00:00Z",
        local_day="2026-11-19",
    )

    result = normalize([workitem])
    assert len(result) == 1
    assert result[0] is workitem  # 应该是同一个对象


def test_normalize_mixed_input():
    """测试 normalize 函数处理混合输入"""
    from datetime import datetime

    commit = CommitEntry(
        record_id="commit-123",
        member="testuser",
        title="Test commit",
        detail="Test commit message",
        occurred_at=datetime(2026, 11, 19, 10, 0, 0),
    )

    workitem = WorkItem(
        record_id="work-123",
        source="github",
        member="testuser",
        kind="commit",
        title="Test work",
        detail="Test detail",
        occurred_at=datetime(2026, 11, 19, 11, 0, 0),
        local_day="2026-11-19",
    )

    # 按时间排序，workitem 应该在前
    result = normalize([commit, workitem])
    assert len(result) == 2
    assert result[0].record_id == "work-123"
    assert result[1].record_id == "commit-123"
