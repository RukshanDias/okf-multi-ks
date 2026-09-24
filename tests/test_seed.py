from __future__ import annotations

import json
from pathlib import Path

import pytest

from okf.associations import load_associations
from okf.cli import main
from okf.seed import DEFAULT_SEED_CAP, propose_seed_pack
from okf.viewer.generate import generate_workspace_visualization
from tests.conftest import write_concept


def _bundle_from_html(html: str) -> dict:
    marker = "window.BUNDLE = "
    idx = html.index(marker) + len(marker)
    data, _ = json.JSONDecoder().raw_decode(html[idx:])
    return data


@pytest.mark.parametrize("workspace_root", ["personal_and_work"], indirect=True)
def test_seed_propose_respects_cap(workspace_root: Path):
    # Add overlapping tokens so ranking produces candidates
    write_concept(
        workspace_root / "brains" / "work" / "tracing-ops.md",
        type_="Document",
        title="Tracing Ops",
        description="OpenTelemetry tracing in production.",
        body="Ops notes.\n",
    )
    candidates = propose_seed_pack(workspace_root, new_ks="work", cap=2)
    assert len(candidates) <= 2
    assert DEFAULT_SEED_CAP == 25


@pytest.mark.parametrize("workspace_root", ["personal_and_work"], indirect=True)
def test_seed_propose_accept_cli(workspace_root: Path):
    write_concept(
        workspace_root / "brains" / "work" / "queue-ops.md",
        type_="Document",
        title="Message Queues Ops",
        description="Queue-based messaging operations.",
        body="Ops.\n",
    )
    assert (
        main(
            [
                "--workspace",
                str(workspace_root),
                "seed",
                "propose",
                "--ks",
                "work",
                "--cap",
                "5",
            ]
        )
        == 0
    )
    pack = json.loads(
        (workspace_root / ".okf" / "seed-pack.json").read_text(encoding="utf-8")
    )
    assert pack["candidates"]
    assert "similarity_score" in pack["candidates"][0]
    assert "score" not in pack["candidates"][0]
    before = len(load_associations(workspace_root))
    assert (
        main(
            [
                "--workspace",
                str(workspace_root),
                "seed",
                "accept",
                "--all",
            ]
        )
        == 0
    )
    assert len(load_associations(workspace_root)) >= before


@pytest.mark.parametrize("workspace_root", ["personal_and_work"], indirect=True)
def test_associate_cli(workspace_root: Path):
    before = len(load_associations(workspace_root))
    rc = main(
        [
            "--workspace",
            str(workspace_root),
            "associate",
            "work",
            "mock-events.md",
            "personal",
            "queues.md",
            "--source",
            "ingest",
            "--note",
            "related foundation",
        ]
    )
    assert rc == 0
    assert len(load_associations(workspace_root)) == before + 1


@pytest.mark.parametrize("workspace_root", ["personal_and_work"], indirect=True)
def test_viz_writes_html_without_index_json(workspace_root: Path):
    out = workspace_root / ".okf" / "viz.html"
    assert main(["--workspace", str(workspace_root), "viz", "--out", str(out)]) == 0
    html = out.read_text(encoding="utf-8")
    assert "association" in html
    assert "Cross-KS relationships" in html
    assert 'target-arrow-shape": "none"' in html
    assert 'id="filter-ks"' in html
    assert "knowledgeSystems" in html
    assert not (workspace_root / ".okf" / "index.json").is_file()


@pytest.mark.parametrize("workspace_root", ["personal_and_work"], indirect=True)
def test_viz_association_edges_are_undirected_singles(workspace_root: Path):
    out = workspace_root / ".okf" / "viz.html"
    generate_workspace_visualization(workspace_root, out)
    graph = _bundle_from_html(out.read_text(encoding="utf-8"))
    assert set(graph["knowledgeSystems"]) == {"personal", "work"}
    assoc = [e for e in graph["edges"] if e.get("classes") == "association"]
    pairs = {
        tuple(sorted((e["data"]["source"], e["data"]["target"]))) for e in assoc
    }
    assert len(assoc) == len(pairs)
    assert ("personal:tracing.md", "work:event-relay.md") in pairs
    assert len(assoc) == 1
