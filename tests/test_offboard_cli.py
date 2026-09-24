"""CLI tests for `okf offboard <label>` (ADR-0006: deregister-only)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from okf.associations import load_associations, upsert_association
from okf.cli import main
from okf.config import load_workspace_config
from okf.id_overlay import load_id_overlay, save_id_overlay
from okf.seed import SeedCandidate, write_seed_pack
from tests.conftest import write_concept


def _snapshot(root: Path) -> dict[str, str]:
    """Text contents of every notebook state file that offboard may touch."""
    files = [root / "okf.yaml", *sorted((root / ".okf").glob("*.json"))]
    return {
        str(p.relative_to(root)): p.read_text(encoding="utf-8")
        for p in files
        if p.is_file()
    }


@pytest.mark.parametrize("argv", [["offboard"], ["offboard", "a", "b"]])
def test_offboard_requires_exactly_one_label(argv):
    with pytest.raises(SystemExit) as excinfo:
        main(["--workspace", ".", *argv])
    assert excinfo.value.code != 0


def _build_ks_library_workspace(dest: Path) -> None:
    """Two-KS notebook using the modern `ks` key plus `ks_library`."""
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "okf.yaml").write_text(
        "version: 1\n"
        "ks_library: ks\n"
        "ks:\n"
        "  personal:\n"
        "    path: personal\n"
        "  work:\n"
        "    path: work\n"
        "link_search_order:\n"
        "  - personal\n"
        "  - work\n",
        encoding="utf-8",
    )
    write_concept(
        dest / "ks" / "personal" / "note.md",
        type_="Learning",
        title="Note",
        description="A note.",
        body="Body.\n",
    )
    write_concept(
        dest / "ks" / "work" / "task.md",
        type_="Document",
        title="Task",
        description="A task.",
        body="Body.\n",
    )


@pytest.mark.parametrize("workspace_root", ["personal_and_work"], indirect=True)
def test_offboard_unknown_label_errors_and_modifies_nothing(
    workspace_root, capsys
):
    before = _snapshot(workspace_root)
    assert (
        main(["--workspace", str(workspace_root), "offboard", "nope"]) == 1
    )
    err = capsys.readouterr().err
    assert "error:" in err
    assert "personal" in err
    assert "work" in err
    assert _snapshot(workspace_root) == before


@pytest.mark.parametrize("workspace_root", ["personal_and_work"], indirect=True)
def test_offboard_without_yes_prints_summary_and_modifies_nothing(
    workspace_root, capsys
):
    save_id_overlay(
        workspace_root,
        {
            "work:legacy-a.md": "44444444-4444-4444-4444-444444444444",
            "work:legacy-b.md": "55555555-5555-5555-5555-555555555555",
            "personal:legacy-c.md": "66666666-6666-6666-6666-666666666666",
        },
    )
    write_seed_pack(
        workspace_root,
        [
            SeedCandidate(
                a_ks="work",
                a_path="event-relay.md",
                b_ks="personal",
                b_path="tracing.md",
                similarity_score=10,
                reason="shared: relay",
            )
        ],
        new_ks="work",
    )
    before = _snapshot(workspace_root)
    assert (
        main(["--workspace", str(workspace_root), "offboard", "work"]) == 1
    )
    out = capsys.readouterr().out
    assert "1 association(s)" in out
    assert "2 overlay entr" in out
    assert "work" in out
    assert "okf.yaml" in out
    assert "seed-pack.json" in out
    assert "--yes" in out
    assert _snapshot(workspace_root) == before


def test_offboard_yes_drops_ks_entry_from_okf_yaml(tmp_path):
    dest = tmp_path / "workspace"
    _build_ks_library_workspace(dest)
    main(["--workspace", str(dest), "offboard", "work", "--yes"])
    raw = yaml.safe_load((dest / "okf.yaml").read_text(encoding="utf-8"))
    assert raw["version"] == 1
    assert raw["ks_library"] == "ks"
    assert set(raw["ks"]) == {"personal"}
    assert raw["ks"]["personal"]["path"] == "personal"
    assert raw["link_search_order"] == ["personal"]


@pytest.mark.parametrize("workspace_root", ["personal_and_work"], indirect=True)
def test_offboard_yes_removes_associations_touching_label_only(workspace_root):
    upsert_association(
        workspace_root,
        a_ks="personal",
        a_concept_id="11111111-1111-1111-1111-111111111111",
        b_ks="personal",
        b_concept_id="77777777-7777-7777-7777-777777777777",
        source="manual",
    )
    main(["--workspace", str(workspace_root), "offboard", "work", "--yes"])
    remaining = load_associations(workspace_root)
    assert len(remaining) == 1
    assert {remaining[0].a.ks, remaining[0].b.ks} == {"personal"}


@pytest.mark.parametrize("workspace_root", ["personal_and_work"], indirect=True)
def test_offboard_yes_removes_overlay_entries_for_label_only(workspace_root):
    save_id_overlay(
        workspace_root,
        {
            "work:legacy-a.md": "44444444-4444-4444-4444-444444444444",
            "personal:legacy-c.md": "66666666-6666-6666-6666-666666666666",
        },
    )
    main(["--workspace", str(workspace_root), "offboard", "work", "--yes"])
    assert load_id_overlay(workspace_root) == {
        "personal:legacy-c.md": "66666666-6666-6666-6666-666666666666"
    }


@pytest.mark.parametrize("workspace_root", ["personal_and_work"], indirect=True)
def test_offboard_yes_deletes_seed_pack_referencing_label(workspace_root):
    pack = write_seed_pack(
        workspace_root,
        [
            SeedCandidate(
                a_ks="work",
                a_path="event-relay.md",
                b_ks="personal",
                b_path="tracing.md",
                similarity_score=10,
                reason="shared: relay",
            )
        ],
        new_ks="work",
    )
    main(["--workspace", str(workspace_root), "offboard", "work", "--yes"])
    assert not pack.exists()


@pytest.mark.parametrize("workspace_root", ["personal_and_work"], indirect=True)
def test_offboard_yes_keeps_seed_pack_not_referencing_label(workspace_root):
    pack = write_seed_pack(
        workspace_root,
        [
            SeedCandidate(
                a_ks="personal",
                a_path="tracing.md",
                b_ks="personal",
                b_path="queues.md",
                similarity_score=10,
                reason="shared: queue",
            )
        ],
        new_ks="personal",
    )
    before = pack.read_text(encoding="utf-8")
    main(["--workspace", str(workspace_root), "offboard", "work", "--yes"])
    assert pack.read_text(encoding="utf-8") == before


@pytest.mark.parametrize("workspace_root", ["personal_and_work"], indirect=True)
def test_offboard_yes_regenerates_viz_and_reports_folder_remains(
    workspace_root, capsys
):
    assert (
        main(["--workspace", str(workspace_root), "offboard", "work", "--yes"])
        == 0
    )
    out = capsys.readouterr().out
    assert "remains on disk" in out
    assert (workspace_root / ".okf" / "viz.html").is_file()
    assert (workspace_root / "brains" / "work" / "event-relay.md").is_file()


@pytest.mark.parametrize("workspace_root", ["personal_and_work"], indirect=True)
def test_offboard_viz_failure_keeps_offboard_and_reports_both(
    workspace_root, capsys
):
    # A directory at the viz output path makes the regenerate write fail.
    (workspace_root / ".okf" / "viz.html").mkdir(parents=True)
    assert (
        main(["--workspace", str(workspace_root), "offboard", "work", "--yes"])
        != 0
    )
    captured = capsys.readouterr()
    assert "offboarded work" in captured.out
    assert "viz" in captured.err
    raw = yaml.safe_load(
        (workspace_root / "okf.yaml").read_text(encoding="utf-8")
    )
    assert "work" not in raw["brains"]  # no rollback


@pytest.mark.parametrize("workspace_root", ["personal_only"], indirect=True)
def test_offboard_last_ks_leaves_valid_empty_notebook(workspace_root):
    assert (
        main(
            ["--workspace", str(workspace_root), "offboard", "personal", "--yes"]
        )
        == 0
    )
    config = load_workspace_config(workspace_root)
    assert config.brains == {}
    assert (workspace_root / ".okf" / "viz.html").is_file()
