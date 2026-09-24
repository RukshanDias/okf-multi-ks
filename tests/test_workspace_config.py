from __future__ import annotations

from pathlib import Path

import pytest

from okf.config import load_workspace_config
from okf.loader import load_brain
from tests.conftest import write_concept


@pytest.mark.parametrize("workspace_root", ["personal_only"], indirect=True)
def test_load_workspace_config_ks_count(workspace_root: Path):
    config = load_workspace_config(workspace_root)
    assert list(config.brains) == ["personal"]
    assert config.brains["personal"].path.is_dir()


@pytest.mark.parametrize("workspace_root", ["personal_and_work"], indirect=True)
def test_personal_and_work_labels(workspace_root: Path):
    config = load_workspace_config(workspace_root)
    assert set(config.brains) == {"personal", "work"}


def test_ks_key_without_role(tmp_path: Path):
    root = tmp_path / "ws"
    root.mkdir()
    (root / "okf.yaml").write_text(
        "version: 1\n"
        "ks:\n"
        "  notes:\n"
        "    path: ks/notes\n",
        encoding="utf-8",
    )
    notes = root / "ks" / "notes"
    write_concept(
        notes / "a.md",
        type_="Learning",
        title="A",
        description="a",
        body="x\n",
    )
    config = load_workspace_config(root)
    assert list(config.brains) == ["notes"]
    assert config.brains["notes"].path.is_dir()


def test_ks_library_resolves_relative_ks_paths(tmp_path: Path):
    home = tmp_path / "notebook-home"
    home.mkdir()
    library = tmp_path / "ks-library"
    (home / "okf.yaml").write_text(
        "version: 1\n"
        f"ks_library: {library.as_posix()}\n"
        "ks:\n"
        "  notes:\n"
        "    path: notes\n",
        encoding="utf-8",
    )
    write_concept(
        library / "notes" / "a.md",
        type_="Learning",
        title="A",
        description="a",
        body="x\n",
    )
    config = load_workspace_config(home)
    assert config.brains["notes"].path == (library / "notes").resolve()
    assert config.brains["notes"].available


def test_absolute_ks_path_wins_over_ks_library(tmp_path: Path):
    home = tmp_path / "notebook-home"
    home.mkdir()
    elsewhere = tmp_path / "elsewhere" / "notes"
    (home / "okf.yaml").write_text(
        "version: 1\n"
        f"ks_library: {(tmp_path / 'ks-library').as_posix()}\n"
        "ks:\n"
        "  notes:\n"
        f"    path: {elsewhere.as_posix()}\n",
        encoding="utf-8",
    )
    write_concept(
        elsewhere / "a.md",
        type_="Learning",
        title="A",
        description="a",
        body="x\n",
    )
    config = load_workspace_config(home)
    assert config.brains["notes"].path == elsewhere.resolve()
    assert config.brains["notes"].available


def test_fresh_notebook_with_football_example_loads(tmp_path: Path):
    """install.sh registers the bundled football KS in a fresh notebook."""
    root = tmp_path / "home-okf"
    root.mkdir()
    library = tmp_path / "ks-library"
    (root / "okf.yaml").write_text(
        "version: 1\n"
        f"ks_library: {library.as_posix()}\n"
        "ks:\n"
        "  football:\n"
        "    path: football\n"
        "    if_missing: error\n"
        "link_search_order:\n"
        "  - football\n",
        encoding="utf-8",
    )
    write_concept(
        library / "football" / "competition.md",
        type_="Competition",
        title="Competition",
        description="A football competition.",
        body="# Competition\n",
    )
    config = load_workspace_config(root)
    assert list(config.brains) == ["football"]
    assert config.brains["football"].available
    assert config.link_search_order == ["football"]


def test_overlay_flat_in_notebook_home(tmp_path: Path):
    """A workspace root itself named .okf gets a flat overlay (no .okf/.okf)."""
    from okf.store import index_dir

    home_ws = tmp_path / ".okf"
    assert index_dir(home_ws) == home_ws
    assert index_dir(tmp_path / "ws") == tmp_path / "ws" / ".okf"


def test_ks_library_must_be_string(tmp_path: Path):
    root = tmp_path / "ws"
    root.mkdir()
    (root / "okf.yaml").write_text(
        "version: 1\n"
        "ks_library: [nope]\n"
        "ks:\n"
        "  notes:\n"
        "    path: notes\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="ks_library"):
        load_workspace_config(root)


@pytest.mark.parametrize("workspace_root", ["personal_only"], indirect=True)
def test_loader_discovers_concepts(workspace_root: Path):
    config = load_workspace_config(workspace_root)
    concepts = load_brain(config.brains["personal"])
    paths = {c.rel_path for c in concepts}
    assert paths == {"tracing.md", "queues.md"}
