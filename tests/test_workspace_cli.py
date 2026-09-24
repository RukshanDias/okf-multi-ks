from __future__ import annotations

import subprocess
import sys

import pytest

from okf.cli import main


@pytest.mark.parametrize(
    "argv",
    [
        ["search", "OpenTelemetry"],
        ["backlinks", "personal", "tracing.md"],
        ["index"],
    ],
)
def test_cli_rejects_removed_retrieval_commands(argv):
    """Agent-facing Derived-index retrieval is gone: no search/backlinks/index."""
    with pytest.raises(SystemExit) as excinfo:
        main(["--workspace", ".", *argv])
    assert excinfo.value.code != 0


@pytest.mark.parametrize("workspace_root", ["policy_violation"], indirect=True)
def test_cli_check_smoke(workspace_root):
    assert main(["--workspace", str(workspace_root), "check"]) != 0


def test_cli_defaults_to_user_okf_home(tmp_path, monkeypatch, capsys):
    """Without --workspace the CLI resolves ~/.okf, never the cwd (ADR-0004)."""
    from pathlib import Path

    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.chdir(tmp_path)  # no okf.yaml here either; cwd must not matter
    assert main(["check"]) != 0
    err = capsys.readouterr().err
    assert (tmp_path / ".okf").as_posix() in err.replace("\\", "/")


@pytest.mark.parametrize("workspace_root", ["personal_and_work"], indirect=True)
def test_cli_associations_by_concept_uuid(workspace_root, capsys):
    tid = "11111111-1111-1111-1111-111111111111"
    assert (
        main(["--workspace", str(workspace_root), "associations", tid]) == 0
    )
    out = capsys.readouterr().out
    assert "work:event-relay.md" in out
    assert "Configure Event Relay" in out
    assert "Acme Event Relay setup." in out
    assert "22222222-2222-2222-2222-222222222222" in out


@pytest.mark.parametrize("workspace_root", ["personal_and_work"], indirect=True)
def test_cli_associations_by_ks_path(workspace_root, capsys):
    assert (
        main(
            [
                "--workspace",
                str(workspace_root),
                "associations",
                "personal:tracing.md",
            ]
        )
        == 0
    )
    out = capsys.readouterr().out
    assert "work:event-relay.md" in out
    assert "Configure Event Relay" in out
    assert "Acme Event Relay setup." in out
    assert "22222222-2222-2222-2222-222222222222" in out


@pytest.mark.parametrize("workspace_root", ["personal_and_work"], indirect=True)
def test_cli_associations_unknown_ks_path_errors(workspace_root, capsys):
    assert (
        main(
            [
                "--workspace",
                str(workspace_root),
                "associations",
                "personal:missing.md",
            ]
        )
        == 1
    )
    assert "error:" in capsys.readouterr().err


@pytest.mark.parametrize("workspace_root", ["personal_and_work"], indirect=True)
def test_cli_associations_unknown_uuid_prints_none(workspace_root, capsys):
    assert (
        main(
            [
                "--workspace",
                str(workspace_root),
                "associations",
                "99999999-9999-9999-9999-999999999999",
            ]
        )
        == 0
    )
    assert "no associations" in capsys.readouterr().out


def test_module_entry_point():
    proc = subprocess.run(
        [sys.executable, "-m", "okf", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    for removed in ("search", "backlinks", "index"):
        assert removed not in proc.stdout
    assert "check" in proc.stdout
    assert "associations" in proc.stdout
    assert "viz" in proc.stdout
