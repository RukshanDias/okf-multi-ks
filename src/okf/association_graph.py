from __future__ import annotations

from pathlib import Path

from okf.associations import load_associations
from okf.id_overlay import load_id_overlay, overlay_key
from okf.models import (
    EDGE_ASSOCIATION,
    ConceptRef,
    GraphEdge,
    IndexWarning,
    LoadedConcept,
)


def _cref(ks: str, rel_path: str) -> ConceptRef:
    return (ks, rel_path.replace("\\", "/"))


def build_uuid_to_ref(
    concepts: list[LoadedConcept],
    workspace_root: Path,
) -> dict[str, ConceptRef]:
    overlay = load_id_overlay(workspace_root)
    mapping: dict[str, ConceptRef] = {}
    for concept in concepts:
        ref = _cref(concept.brain, concept.rel_path)
        if concept.uuid:
            mapping[concept.uuid] = ref
        key = overlay_key(concept.brain, concept.rel_path)
        if key in overlay:
            mapping[overlay[key]] = ref
    return mapping


def associations_to_edges(
    workspace_root: Path,
    concepts: list[LoadedConcept],
) -> tuple[dict[ConceptRef, list[GraphEdge]], list[IndexWarning]]:
    associations = load_associations(workspace_root)
    uuid_to_ref = build_uuid_to_ref(concepts, workspace_root)
    forward: dict[ConceptRef, list[GraphEdge]] = {}
    warnings: list[IndexWarning] = []

    for assoc in associations:
        left = uuid_to_ref.get(assoc.a.concept_id)
        right = uuid_to_ref.get(assoc.b.concept_id)
        if left is None or right is None:
            missing = []
            if left is None:
                missing.append(f"{assoc.a.ks}:{assoc.a.concept_id}")
            if right is None:
                missing.append(f"{assoc.b.ks}:{assoc.b.concept_id}")
            warnings.append(
                IndexWarning(
                    code="stale_association",
                    source=left or ("", ""),
                    message=(
                        f"Association {assoc.id} has unresolved endpoint(s): "
                        + ", ".join(missing)
                    ),
                )
            )
            continue
        forward.setdefault(left, []).append(
            GraphEdge(target=right, kind=EDGE_ASSOCIATION)
        )
        forward.setdefault(right, []).append(
            GraphEdge(target=left, kind=EDGE_ASSOCIATION)
        )
    return forward, warnings
