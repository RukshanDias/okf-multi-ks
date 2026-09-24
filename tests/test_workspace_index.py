from __future__ import annotations

from pathlib import Path

import pytest

from okf.index import scan_workspace
from okf.models import EDGE_ASSOCIATION, EDGE_INTRA
from okf.store import index_dir
from tests.conftest import cref, edge_targets, edges_by_kind


@pytest.mark.parametrize("workspace_root", ["personal_only"], indirect=True)
def test_personal_only_scan_clean(indexed_workspace):
    _, result = indexed_workspace
    assert result.success is True
    assert result.errors == []
    assert not any(w.code == "dangling_link" for w in result.warnings)


@pytest.mark.parametrize("workspace_root", ["personal_only"], indirect=True)
def test_personal_only_same_brain_link(indexed_workspace):
    _, result = indexed_workspace
    edges = result.forward[cref("personal", "tracing.md")]
    assert edge_targets(edges) == {cref("personal", "queues.md")}
    assert all(e.kind == EDGE_INTRA for e in edges)


@pytest.mark.parametrize("workspace_root", ["personal_only"], indirect=True)
def test_personal_only_backlinks(indexed_workspace):
    _, result = indexed_workspace
    edges = result.backlinks[cref("personal", "queues.md")]
    assert edge_targets(edges) == {cref("personal", "tracing.md")}


@pytest.mark.parametrize("workspace_root", ["personal_and_work"], indirect=True)
def test_work_intra_and_association(indexed_workspace):
    _, result = indexed_workspace
    edges = result.forward[cref("work", "event-relay.md")]
    assert edges_by_kind(edges, EDGE_INTRA) == {cref("work", "mock-events.md")}
    assert edges_by_kind(edges, EDGE_ASSOCIATION) == {
        cref("personal", "tracing.md")
    }


@pytest.mark.parametrize("workspace_root", ["personal_and_work"], indirect=True)
def test_backlinks_via_association(indexed_workspace):
    _, result = indexed_workspace
    edges = result.backlinks[cref("personal", "tracing.md")]
    assert cref("work", "event-relay.md") in edge_targets(edges)
    assert any(
        e.target == cref("work", "event-relay.md") and e.kind == EDGE_ASSOCIATION
        for e in edges
    )


@pytest.mark.parametrize("workspace_root", ["personal_and_work"], indirect=True)
def test_remove_work_ks_prunes_associations(workspace_root: Path):
    from okf.config import load_workspace_config

    load_workspace_config(workspace_root)
    yaml_path = workspace_root / "okf.yaml"
    yaml_path.write_text(
        "version: 1\n"
        "brains:\n"
        "  personal:\n"
        "    path: brains/personal\n"
        "    role: personal\n"
        "link_search_order:\n"
        "  - personal\n",
        encoding="utf-8",
    )
    result = scan_workspace(workspace_root)
    assert not any(c.brain == "work" for c in result.concepts)
    back = result.backlinks.get(cref("personal", "tracing.md"), [])
    assert cref("work", "event-relay.md") not in edge_targets(back)
    from okf.associations import load_associations

    assert load_associations(workspace_root) == []
    assert any(w.code == "associations_pruned" for w in result.warnings)


@pytest.mark.parametrize("workspace_root", ["policy_violation"], indirect=True)
def test_cross_ks_markdown_warns_on_scan(indexed_workspace):
    _, result = indexed_workspace
    assert result.success is True
    codes = {w.code for w in result.warnings}
    assert "cross_ks_markdown_link" in codes


@pytest.mark.parametrize("workspace_root", ["ambiguous_link"], indirect=True)
def test_ambiguous_link_fails_scan(workspace_root: Path):
    result = scan_workspace(workspace_root)
    assert result.success is False
    assert len(result.errors) == 1
    assert result.errors[0].code == "ambiguous_link"
    assert set(result.errors[0].candidates) == {
        cref("personal", "vendor-a/relay-setup.md"),
        cref("personal", "vendor-b/relay-setup.md"),
    }


@pytest.mark.parametrize("workspace_root", ["dangling_link"], indirect=True)
def test_dangling_link_warns(indexed_workspace):
    _, result = indexed_workspace
    assert result.success is True
    assert any(w.code == "dangling_link" for w in result.warnings)


@pytest.mark.parametrize("workspace_root", ["dangling_link"], indirect=True)
def test_dangling_link_no_edge(indexed_workspace):
    _, result = indexed_workspace
    assert cref("personal", "future-plans.md") not in result.forward


@pytest.mark.parametrize("workspace_root", ["personal_only"], indirect=True)
def test_scan_does_not_write_index_json(workspace_root: Path):
    scan_workspace(workspace_root)
    assert not (index_dir(workspace_root) / "index.json").is_file()
    assert not (workspace_root / "brains" / "personal" / ".okf").exists()
