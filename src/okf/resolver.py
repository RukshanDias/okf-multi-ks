from __future__ import annotations

from okf.links import (
    concept_matches_key,
    normalize_link_key,
    path_escapes_ks,
    resolve_same_brain,
)
from okf.models import (
    EDGE_INTRA,
    ConceptRef,
    GraphEdge,
    IndexError,
    IndexWarning,
    LoadedConcept,
    WorkspaceConfig,
)


def _cref(brain: str, rel_path: str) -> ConceptRef:
    return (brain, rel_path.replace("\\", "/"))


def _concept_index(
    concepts: list[LoadedConcept],
) -> dict[str, dict[str, LoadedConcept]]:
    by_brain: dict[str, dict[str, LoadedConcept]] = {}
    for c in concepts:
        by_brain.setdefault(c.brain, {})[c.concept_id] = c
    return by_brain


def _find_same_ks_candidates(
    key: str,
    by_brain: dict[str, dict[str, LoadedConcept]],
    ks: str,
) -> list[ConceptRef]:
    candidates: list[ConceptRef] = []
    for concept_id, concept in by_brain.get(ks, {}).items():
        if concept_matches_key(concept_id, key):
            candidates.append(_cref(ks, concept.rel_path))
    return candidates


def resolve_links(
    config: WorkspaceConfig,
    concepts: list[LoadedConcept],
) -> tuple[
    dict[ConceptRef, list[GraphEdge]],
    list[IndexWarning],
    list[IndexError],
]:
    """Resolve markdown links as Intra-KS only (Separation rule)."""
    by_brain = _concept_index(concepts)
    forward: dict[ConceptRef, list[GraphEdge]] = {}
    warnings: list[IndexWarning] = []
    errors: list[IndexError] = []

    for concept in concepts:
        source_ref = _cref(concept.brain, concept.rel_path)
        targets: list[GraphEdge] = []
        ks_root = config.brains[concept.brain].path
        doc_dir = concept.path.parent

        for link_target in concept.link_targets:
            if path_escapes_ks(link_target, doc_dir, ks_root):
                warnings.append(
                    IndexWarning(
                        code="cross_ks_markdown_link",
                        source=source_ref,
                        unresolved_target=link_target,
                        message=(
                            f"Cross-KS markdown link {link_target!r} in {source_ref}; "
                            "use Association store instead"
                        ),
                    )
                )
                continue

            same_id = resolve_same_brain(link_target, doc_dir, ks_root)
            if same_id is not None:
                target_concept = by_brain[concept.brain].get(same_id)
                if target_concept is None:
                    warnings.append(
                        IndexWarning(
                            code="dangling_link",
                            source=source_ref,
                            unresolved_target=link_target,
                            message=f"Dangling link {link_target!r} in {source_ref}",
                        )
                    )
                    continue
                targets.append(
                    GraphEdge(
                        target=_cref(concept.brain, target_concept.rel_path),
                        kind=EDGE_INTRA,
                    )
                )
                continue

            key = normalize_link_key(link_target)
            candidates = _find_same_ks_candidates(key, by_brain, concept.brain)
            if len(candidates) > 1:
                errors.append(
                    IndexError(
                        code="ambiguous_link",
                        source=source_ref,
                        link_target=link_target,
                        message=f"Ambiguous link {link_target!r} in {source_ref}",
                        candidates=candidates,
                    )
                )
                continue
            if len(candidates) == 0:
                warnings.append(
                    IndexWarning(
                        code="dangling_link",
                        source=source_ref,
                        unresolved_target=link_target,
                        message=f"Dangling link {link_target!r} in {source_ref}",
                    )
                )
                continue

            targets.append(GraphEdge(target=candidates[0], kind=EDGE_INTRA))

        if targets:
            forward[source_ref] = targets

    return forward, warnings, errors
