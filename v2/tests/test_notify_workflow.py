import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "notify.yml"


def _workflow_text() -> str:
    return WORKFLOW_PATH.read_text(encoding="utf-8")


def test_workflow_runs_v2_module():
    workflow_text = _workflow_text()

    assert "python -m " + "smart_daily_v2.notify_push" in workflow_text
    legacy_command = "python " + "v1/" + "scripts/" + "notify_push.py"
    assert legacy_command not in workflow_text
    assert "已归属 v2 实时提醒通道" in workflow_text


def test_workflow_installs_v2_package():
    workflow_text = _workflow_text()
    run_lines = re.findall(r"^\s*run:\s*(.+)$", workflow_text, re.MULTILINE)
    install_commands = [line for line in run_lines if "pip install" in line]

    assert any("./v2" in command for command in install_commands)
    assert not any(command.strip() == "pip install httpx" for command in install_commands)


def test_workflow_single_channel():
    workflow_text = _workflow_text()
    workflow_files = sorted((ROOT / ".github" / "workflows").glob("notify*.yml"))

    assert "push:" in workflow_text
    assert [path.name for path in workflow_files] == ["notify.yml"]


def test_workflow_branches_and_permissions():
    workflow_text = _workflow_text()

    assert "branches: [main, dev]" in workflow_text
    assert "permissions:" in workflow_text
    assert "contents: read" in workflow_text


def test_workflow_env_contract():
    workflow_text = _workflow_text()
    env_items = dict(
        re.findall(
            r"^\s*(FEISHU_WEBHOOK_URL|FEISHU_WEBHOOK_SECRET|ACTOR|MEMBER_DISPLAY_NAMES):\s*(.*?)\s*$",
            workflow_text,
            re.MULTILINE,
        )
    )

    assert set(env_items) == {
        "FEISHU_WEBHOOK_URL",
        "FEISHU_WEBHOOK_SECRET",
        "ACTOR",
        "MEMBER_DISPLAY_NAMES",
    }
    assert env_items["FEISHU_WEBHOOK_URL"] == "${{ secrets.FEISHU_WEBHOOK_URL }}"
    assert env_items["FEISHU_WEBHOOK_SECRET"] == "${{ secrets.FEISHU_WEBHOOK_SECRET }}"
    credential_prefix = "https://" + "open.feishu.cn/" + "open-apis/" + "bot/" + "v2/" + "hook/"
    assert credential_prefix not in workflow_text


def test_workflow_python_313():
    workflow_text = _workflow_text()

    assert "actions/setup-python@" in workflow_text
    assert 'python-version: "3.13"' in workflow_text


def test_workflow_scope_guard():
    workflow_text = _workflow_text()
    test_source = Path(__file__).read_text(encoding="utf-8")
    notify_source = (ROOT / "v2" / "src" / "smart_daily_v2" / "notify_push.py").read_text(
        encoding="utf-8"
    )
    v1_import = re.compile(r"(?:from|import)\s+smart_daily(?:\.|\s|$)")
    credential_prefix = "https://" + "open.feishu.cn/" + "open-apis/" + "bot/" + "v2/" + "hook/"

    assert credential_prefix not in workflow_text
    assert not v1_import.search(test_source)
    assert credential_prefix not in test_source
    assert not v1_import.search(notify_source)
