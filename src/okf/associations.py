from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from okf.store import index_dir

Source = Literal["seed", "ingest", "ask", "manual"]

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class AssociationEndpoint:
    ks: str
    concept_id: str


@dataclass(frozen=True)
class Association:
    id: str
    a: AssociationEndpoint
    b: AssociationEndpoint
    source: str
    created_at: str
    note: str | None = None
    confidence: float | None = None


@dataclass(frozen=True)
class AssociationNeighbor:
    """One Cross-KS neighbor of a concept, for agent transfer-learning hops."""

    ks: str
    path: str
    concept_id: str
    association_id: str
    source: str
    note: str | None = None
    title: str = ""
    description: str = ""


def associations_path(workspace_root: Path) -> Path:
    return index_dir(workspace_root) / "associations.json"


def _endpoint_key(ep: AssociationEndpoint) -> str:
    return f"{ep.ks}:{ep.concept_id}"


def normalize_pair(
    a: AssociationEndpoint, b: AssociationEndpoint
) -> tuple[AssociationEndpoint, AssociationEndpoint]:
    if _endpoint_key(a) <= _endpoint_key(b):
        return a, b
    return b, a


def load_associations(workspace_root: Path) -> list[Association]:
    path = associations_path(workspace_root)
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("version") != 1:
        raise ValueError(f"Unsupported associations schema at {path}")
    out: list[Association] = []
    for raw in data.get("associations") or []:
        a = raw["a"]
        b = raw["b"]
        out.append(
            Association(
                id=str(raw["id"]),
                a=AssociationEndpoint(ks=str(a["ks"]), concept_id=str(a["concept_id"])),
                b=AssociationEndpoint(ks=str(b["ks"]), concept_id=str(b["concept_id"])),
                source=str(raw["source"]),
                created_at=str(raw["created_at"]),
                note=raw.get("note"),
                confidence=raw.get("confidence"),
            )
        )
    return out


def save_associations(workspace_root: Path, associations: list[Association]) -> Path:
    out_dir = index_dir(workspace_root)
    out_dir.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "version": 1,
        "associations": [
            {
                "id": assoc.id,
                "a": {"ks": assoc.a.ks, "concept_id": assoc.a.concept_id},
                "b": {"ks": assoc.b.ks, "concept_id": assoc.b.concept_id},
                "source": assoc.source,
                "created_at": assoc.created_at,
                **({"note": assoc.note} if assoc.note is not None else {}),
                **(
                    {"confidence": assoc.confidence}
                    if assoc.confidence is not None
                    else {}
                ),
            }
            for assoc in associations
        ],
    }
    path = associations_path(workspace_root)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def upsert_association(
    workspace_root: Path,
    *,
    a_ks: str,
    a_concept_id: str,
    b_ks: str,
    b_concept_id: str,
    source: Source,
    note: str | None = None,
    confidence: float | None = None,
) -> Association:
    if a_ks == b_ks and a_concept_id == b_concept_id:
        raise ValueError("Association endpoints must be distinct")
    a, b = normalize_pair(
        AssociationEndpoint(ks=a_ks, concept_id=a_concept_id),
        AssociationEndpoint(ks=b_ks, concept_id=b_concept_id),
    )
    existing = load_associations(workspace_root)
    for assoc in existing:
        if assoc.a == a and assoc.b == b:
            return assoc
    created = Association(
        id=str(uuid.uuid4()),
        a=a,
        b=b,
        source=source,
        created_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        note=note,
        confidence=confidence,
    )
    existing.append(created)
    save_associations(workspace_root, existing)
    return created


def prune_associations_to_configured_ks(
    workspace_root: Path, configured_ks: set[str]
) -> int:
    """Drop associations that touch a KS not in configured_ks."""
    existing = load_associations(workspace_root)
    kept = [
        a
        for a in existing
        if a.a.ks in configured_ks and a.b.ks in configured_ks
    ]
    removed = len(existing) - len(kept)
    if removed:
        save_associations(workspace_root, kept)
    return removed


def remove_associations_for_ks(workspace_root: Path, ks: str) -> int:
    existing = load_associations(workspace_root)
    keep_labels = {a.a.ks for a in existing} | {a.b.ks for a in existing}
    keep_labels.discard(ks)
    return prune_associations_to_configured_ks(workspace_root, keep_labels)


def _concept_id_locations(
    workspace_root: Path,
) -> dict[str, tuple[str, str, str, str]]:
    """Map stable concept UUID → (ks, rel_path, title, description)."""
    from okf.config import load_workspace_config
    from okf.identity import load_concept_map, resolve_stable_id

    config = load_workspace_config(workspace_root)
    concepts = load_concept_map(config)
    out: dict[str, tuple[str, str, str, str]] = {}
    for (ks, rel_path), concept in concepts.items():
        sid = resolve_stable_id(
            workspace_root, config, ks, rel_path, concepts=concepts
        )
        out[sid] = (ks, rel_path, concept.title, concept.description)
    return out


def associations_for_concept_id(
    workspace_root: Path, concept_id: str
) -> list[AssociationNeighbor]:
    """Return Cross-KS neighbors for one concept UUID (not the whole store)."""
    workspace_root = Path(workspace_root)
    concept_id = str(concept_id).strip()
    matched = [
        a
        for a in load_associations(workspace_root)
        if a.a.concept_id == concept_id or a.b.concept_id == concept_id
    ]
    if not matched:
        return []

    locations = _concept_id_locations(workspace_root)
    neighbors: list[AssociationNeighbor] = []
    for assoc in matched:
        other = assoc.b if assoc.a.concept_id == concept_id else assoc.a
        ks, path, title, description = locations.get(
            other.concept_id, (other.ks, "", "", "")
        )
        neighbors.append(
            AssociationNeighbor(
                ks=ks,
                path=path,
                concept_id=other.concept_id,
                association_id=assoc.id,
                source=assoc.source,
                note=assoc.note,
                title=title,
                description=description,
            )
        )
    neighbors.sort(key=lambda n: (n.ks, n.path, n.concept_id))
    return neighbors


def parse_concept_ref(ref: str) -> str | tuple[str, str]:
    """Parse a concept UUID or `ks:path` reference for association lookup."""
    ref = ref.strip()
    if _UUID_RE.match(ref):
        return ref
    if ":" not in ref:
        raise ValueError(f"Expected concept UUID or ks:path, got {ref!r}")
    ks, rel_path = ref.split(":", 1)
    ks = ks.strip()
    rel_path = rel_path.lstrip("./").replace("\\", "/").strip()
    if not ks or not rel_path:
        raise ValueError(f"Expected concept UUID or ks:path, got {ref!r}")
    return ks, rel_path


def associations_for_concept_ref(
    workspace_root: Path, ref: str
) -> list[AssociationNeighbor]:
    """Return Cross-KS neighbors for a concept UUID or `ks:path`."""
    parsed = parse_concept_ref(ref)
    if isinstance(parsed, str):
        return associations_for_concept_id(workspace_root, parsed)
    ks, rel_path = parsed
    from okf.config import load_workspace_config
    from okf.identity import resolve_stable_id

    config = load_workspace_config(workspace_root)
    concept_id = resolve_stable_id(workspace_root, config, ks, rel_path)
    return associations_for_concept_id(workspace_root, concept_id)
