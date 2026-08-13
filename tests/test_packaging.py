import json
import subprocess
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_mcpb_manifest_has_portable_uv_entrypoint():
    manifest = json.loads((ROOT / "manifest.json").read_text())
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())

    assert manifest["manifest_version"] == "0.4"
    assert manifest["version"] == project["project"]["version"]
    assert manifest["server"]["type"] == "uv"
    assert manifest["server"]["entry_point"] == "main.py"
    assert (ROOT / manifest["server"]["entry_point"]).is_file()

    config = manifest["server"]["mcp_config"]
    assert config["command"] == "uv"
    assert config["args"] == [
        "run",
        "--directory",
        "${__dirname}",
        "--frozen",
        "--no-dev",
        "python",
        "main.py",
    ]
    assert config["env"]["APTIBLE_TOKEN"] == "${user_config.aptible_token}"
    assert config["env"]["APTIBLE_MCP_CERTIFICATE_DIR"] == (
        "${user_config.certificate_directory}"
    )
    assert manifest["user_config"]["aptible_token"]["sensitive"] is True
    assert manifest["user_config"]["certificate_directory"]["type"] == "directory"


def test_mcpb_runtime_files_are_not_ignored():
    ignore_file = (ROOT / ".mcpbignore").read_text()

    for runtime_file in (
        "main.py",
        "api_client.py",
        "models/",
        "examples/",
        "pyproject.toml",
        "uv.lock",
        "scripts/",
    ):
        assert runtime_file not in ignore_file.splitlines()

    for excluded in (
        ".git/",
        ".agents/",
        ".specs/",
        ".security/",
        ".venv/",
        "tests/",
        ".env",
    ):
        assert excluded in ignore_file.splitlines()


def test_setup_script_is_valid_posix_shell_and_avoids_remote_installers():
    setup_script = ROOT / "scripts" / "setup.sh"
    contents = setup_script.read_text()

    subprocess.run(["sh", "-n", str(setup_script)], check=True)
    assert "uv sync" in contents
    assert "--locked" in contents
    assert "--no-dev" in contents
    assert "curl " not in contents
    assert "wget " not in contents
    assert "sudo " not in contents
    assert "eval " not in contents
