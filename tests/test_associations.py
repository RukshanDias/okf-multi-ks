from __future__ import annotations

from pathlib import Path

from okf.association_graph import associations_to_edges
from okf.associations import (
    Association,
    AssociationEndpoint,
    associations_for_concept_id,
    associations_for_concept_ref,
    load_associations,
    remove_associations_for_ks,
    save_associations,
    upsert_association,
)
from okf.id_overlay import ensure_overlay_id, load_id_overlay, overlay_key
from okf.loader import load_brain
from okf.models import EDGE_ASSOCIATION, BrainConfig
from tests.conftest import cref, write_concept


def test_associations_for_concept_id_returns_neighbors_with_path(tmp_path: Path):
    """Per-node lookup: UUID in → Cross-KS neighbor ks+path out (not whole store)."""
    personal = tmp_path / "brains" / "personal"
    work = tmp_path / "brains" / "work"
    tid = "11111111-1111-1111-1111-111111111111"
    rid = "22222222-2222-2222-2222-222222222222"
    (tmp_path / "okf.yaml").write_text(
        """version: 1
brains:
  personal:
    path: brains/personal
  work:
    path: brains/work
""",
        encoding="utf-8",
    )
    write_concept(
        personal / "tracing.md",
        type_="Learning",
        title="Tracing",
        description="d",
        body="x\n",
        id_=tid,
    )
    write_concept(
        work / "relay.md",
        type_="Document",
        title="Relay",
        description="d",
        body="x\n",
        id_=rid,
    )
    upsert_association(
        tmp_path,
        a_ks="personal",
        a_concept_id=tid,
        b_ks="work",
        b_concept_id=rid,
        source="manual",
        note="transfer",
    )

    neighbors = associations_for_concept_id(tmp_path, tid)
    assert len(neighbors) == 1
    assert neighbors[0].ks == "work"
    assert neighbors[0].path == "relay.md"
    assert neighbors[0].concept_id == rid
    assert neighbors[0].note == "transfer"
    assert neighbors[0].description == "d"


def test_associations_for_unknown_concept_id_is_empty(tmp_path: Path):
    assert associations_for_concept_id(tmp_path, "99999999-9999-9999-9999-999999999999") == []


def test_associations_for_concept_ref_by_ks_path(tmp_path: Path):
    personal = tmp_path / "brains" / "personal"
    work = tmp_path / "brains" / "work"
    tid = "11111111-1111-1111-1111-111111111111"
    rid = "22222222-2222-2222-2222-222222222222"
    (tmp_path / "okf.yaml").write_text(
        """version: 1
brains:
  personal:
    path: brains/personal
  work:
    path: brains/work
""",
        encoding="utf-8",
    )
    write_concept(
        personal / "tracing.md",
        type_="Learning",
        title="Tracing",
        description="d",
        body="x\n",
        id_=tid,
    )
    write_concept(
        work / "relay.md",
        type_="Document",
        title="Relay",
        description="d",
        body="x\n",
        id_=rid,
    )
    upsert_association(
        tmp_path,
        a_ks="personal",
        a_concept_id=tid,
        b_ks="work",
        b_concept_id=rid,
        source="manual",
    )

    neighbors = associations_for_concept_ref(tmp_path, "personal:tracing.md")
    assert len(neighbors) == 1
    assert neighbors[0].path == "relay.md"


def test_association_roundtrip(tmp_path: Path):
    assoc = Association(
        id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        a=AssociationEndpoint(ks="personal", concept_id="11111111-1111-1111-1111-111111111111"),
        b=AssociationEndpoint(ks="work", concept_id="22222222-2222-2222-2222-222222222222"),
        source="manual",
        created_at="2026-07-01T00:00:00Z",
        note="related",
    )
    save_associations(tmp_path, [assoc])
    loaded = load_associations(tmp_path)
    assert len(loaded) == 1
    assert loaded[0].id == assoc.id
    assert loaded[0].note == "related"


def test_upsert_is_idempotent_for_undirected_pair(tmp_path: Path):
    first = upsert_association(
        tmp_path,
        a_ks="personal",
        a_concept_id="11111111-1111-1111-1111-111111111111",
        b_ks="work",
        b_concept_id="22222222-2222-2222-2222-222222222222",
        source="seed",
    )
    again = upsert_association(
        tmp_path,
        a_ks="work",
        a_concept_id="22222222-2222-2222-2222-222222222222",
        b_ks="personal",
        b_concept_id="11111111-1111-1111-1111-111111111111",
        source="ask",
    )
    assert again.id == first.id
    assert len(load_associations(tmp_path)) == 1


def test_remove_associations_for_ks(tmp_path: Path):
    save_associations(
        tmp_path,
        [
            Association(
                id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                a=AssociationEndpoint(ks="personal", concept_id="1"),
                b=AssociationEndpoint(ks="work", concept_id="2"),
                source="manual",
                created_at="2026-07-01T00:00:00Z",
            ),
            Association(
                id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
                a=AssociationEndpoint(ks="personal", concept_id="1"),
                b=AssociationEndpoint(ks="other", concept_id="3"),
                source="manual",
                created_at="2026-07-01T00:00:00Z",
            ),
        ],
    )
    removed = remove_associations_for_ks(tmp_path, "work")
    assert removed == 1
    remaining = load_associations(tmp_path)
    assert len(remaining) == 1
    assert remaining[0].id == "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"


def test_id_overlay_persists(tmp_path: Path):
    uid, created = ensure_overlay_id(tmp_path, "personal", "queues.md")
    assert created is True
    again, created_again = ensure_overlay_id(tmp_path, "personal", "queues.md")
    assert created_again is False
    assert uid == again
    overlay = load_id_overlay(tmp_path)
    assert overlay[overlay_key("personal", "queues.md")] == uid


def test_associations_to_edges_uses_frontmatter_id(tmp_path: Path):
    personal = tmp_path / "personal"
    work = tmp_path / "work"
    tid = "11111111-1111-1111-1111-111111111111"
    rid = "22222222-2222-2222-2222-222222222222"
    write_concept(
        personal / "tracing.md",
        type_="Learning",
        title="Tracing",
        description="d",
        body="x\n",
        id_=tid,
    )
    write_concept(
        work / "relay.md",
        type_="Document",
        title="Relay",
        description="d",
        body="x\n",
        id_=rid,
    )
    save_associations(
        tmp_path,
        [
            Association(
                id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                a=AssociationEndpoint(ks="personal", concept_id=tid),
                b=AssociationEndpoint(ks="work", concept_id=rid),
                source="manual",
                created_at="2026-07-01T00:00:00Z",
            )
        ],
    )
    concepts = []
    concepts.extend(
        load_brain(
            BrainConfig(
                label="personal",
                path=personal,
                if_missing="error",
            )
        )
    )
    concepts.extend(
        load_brain(
            BrainConfig(
                label="work",
                path=work,
                if_missing="error",
            )
        )
    )
    forward, warnings = associations_to_edges(tmp_path, concepts)
    assert warnings == []
    edges = forward[cref("work", "relay.md")]
    assert len(edges) == 1
    assert edges[0].target == cref("personal", "tracing.md")
    assert edges[0].kind == EDGE_ASSOCIATION
