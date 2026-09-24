from __future__ import annotations

from pathlib import Path

from okf.config import WorkspaceConfig
from okf.id_overlay import ensure_overlay_id
from okf.loader import load_brain
from okf.models import LoadedConcept

ConceptKey = tuple[str, str]  # (ks, rel_path)


def load_concept_map(config: WorkspaceConfig) -> dict[ConceptKey, LoadedConcept]:
    out: dict[ConceptKey, LoadedConcept] = {}
    for brain in config.brains.values():
        if not brain.available:
            continue
        for concept in load_brain(brain):
            out[(concept.brain, concept.rel_path)] = concept
    return out


def resolve_stable_id(
    workspace_root: Path,
    config: WorkspaceConfig,
    ks: str,
    rel_path: str,
    *,
    concepts: dict[ConceptKey, LoadedConcept] | None = None,
) -> str:
    """Frontmatter id if present; else Id overlay."""
    rel = rel_path.replace("\\", "/")
    key = (ks, rel)
    concept = (concepts or load_concept_map(config)).get(key)
    if concept is None:
        raise LookupError(f"Unknown concept {ks}:{rel}")
    if concept.uuid:
        return concept.uuid
    uid, _ = ensure_overlay_id(workspace_root, ks, rel)
    return uid
