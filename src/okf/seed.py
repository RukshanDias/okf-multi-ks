from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from okf.config import load_workspace_config
from okf.identity import load_concept_map, resolve_stable_id
from okf.loader import load_brain
from okf.models import LoadedConcept
from okf.store import index_dir

DEFAULT_SEED_CAP = 25
_TOKEN_RE = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class SeedCandidate:
    a_ks: str
    a_path: str
    b_ks: str
    b_path: str
    similarity_score: int
    reason: str


def _tokens(*parts: str) -> set[str]:
    text = " ".join(parts).lower()
    return {t for t in _TOKEN_RE.findall(text) if len(t) > 2}


def _similarity_score_pair(a: LoadedConcept, b: LoadedConcept) -> tuple[int, str]:
    ta = _tokens(a.title, a.description, *a.tags, a.concept_id)
    tb = _tokens(b.title, b.description, *b.tags, b.concept_id)
    overlap = ta & tb
    if not overlap:
        return 0, ""
    similarity_score = len(overlap) * 10
    # Prefer overlapping title tokens
    title_overlap = _tokens(a.title) & _tokens(b.title)
    similarity_score += len(title_overlap) * 15
    reason = "shared: " + ", ".join(sorted(overlap)[:6])
    return similarity_score, reason


def propose_seed_pack(
    workspace_root: Path,
    *,
    new_ks: str,
    cap: int = DEFAULT_SEED_CAP,
) -> list[SeedCandidate]:
    config = load_workspace_config(workspace_root)
    if new_ks not in config.brains:
        raise ValueError(f"Unknown KS {new_ks!r}")
    new_brain = config.brains[new_ks]
    if not new_brain.available:
        raise ValueError(f"KS {new_ks!r} path missing: {new_brain.path}")

    new_concepts = load_brain(new_brain)
    others: list[LoadedConcept] = []
    for label, brain in config.brains.items():
        if label == new_ks or not brain.available:
            continue
        others.extend(load_brain(brain))

    ranked: list[SeedCandidate] = []
    for a in new_concepts:
        for b in others:
            similarity_score, reason = _similarity_score_pair(a, b)
            if similarity_score <= 0:
                continue
            ranked.append(
                SeedCandidate(
                    a_ks=a.brain,
                    a_path=a.rel_path,
                    b_ks=b.brain,
                    b_path=b.rel_path,
                    similarity_score=similarity_score,
                    reason=reason,
                )
            )
    ranked.sort(
        key=lambda c: (-c.similarity_score, c.a_path, c.b_ks, c.b_path)
    )
    return ranked[: max(0, cap)]


def seed_pack_path(workspace_root: Path) -> Path:
    return index_dir(workspace_root) / "seed-pack.json"


def write_seed_pack(
    workspace_root: Path,
    candidates: list[SeedCandidate],
    *,
    new_ks: str,
    path: Path | None = None,
) -> Path:
    out = path or seed_pack_path(workspace_root)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "new_ks": new_ks,
        "cap": len(candidates),
        "candidates": [asdict(c) for c in candidates],
    }
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out


def load_seed_pack(path: Path) -> list[SeedCandidate]:
    data = json.loads(path.read_text(encoding="utf-8"))
    out: list[SeedCandidate] = []
    for raw in data.get("candidates") or []:
        if "similarity_score" not in raw:
            raise ValueError(
                "seed candidate missing similarity_score; re-run `okf seed propose`"
            )
        out.append(
            SeedCandidate(
                a_ks=str(raw["a_ks"]),
                a_path=str(raw["a_path"]),
                b_ks=str(raw["b_ks"]),
                b_path=str(raw["b_path"]),
                similarity_score=int(raw["similarity_score"]),
                reason=str(raw.get("reason") or ""),
            )
        )
    return out


def accept_seed_pack(
    workspace_root: Path,
    candidates: list[SeedCandidate],
    *,
    indexes: set[int] | None = None,
) -> int:
    """Write accepted candidates into Association store. indexes are 1-based."""
    from okf.associations import upsert_association

    config = load_workspace_config(workspace_root)
    concepts = load_concept_map(config)
    accepted = 0
    for i, cand in enumerate(candidates, start=1):
        if indexes is not None and i not in indexes:
            continue
        upsert_association(
            workspace_root,
            a_ks=cand.a_ks,
            a_concept_id=resolve_stable_id(
                workspace_root, config, cand.a_ks, cand.a_path, concepts=concepts
            ),
            b_ks=cand.b_ks,
            b_concept_id=resolve_stable_id(
                workspace_root, config, cand.b_ks, cand.b_path, concepts=concepts
            ),
            source="seed",
            note=cand.reason or None,
            confidence=min(1.0, cand.similarity_score / 100.0),
        )
        accepted += 1
    return accepted
