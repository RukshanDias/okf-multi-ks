from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

ConceptRef = tuple[str, str]  # (ks_label, relative/path.md)

EDGE_INTRA = "intra"
EDGE_ASSOCIATION = "association"


@dataclass(frozen=True)
class GraphEdge:
    target: ConceptRef
    kind: str  # EDGE_INTRA | EDGE_ASSOCIATION


@dataclass
class BrainConfig:
    label: str
    path: Path
    if_missing: str  # "error" | "skip_with_warning"
    available: bool = True


@dataclass
class WorkspaceConfig:
    root: Path
    brains: dict[str, BrainConfig]  # labeled Knowledge Systems
    link_search_order: list[str]  # unused by Separation resolver; kept for yaml compat


@dataclass
class LoadedConcept:
    brain: str
    path: Path
    rel_path: str
    concept_id: str  # path id (no .md) for Intra-KS link matching
    title: str
    description: str
    type: str
    tags: list[str]
    body: str
    link_targets: list[str] = field(default_factory=list)
    uuid: str | None = None  # frontmatter id when present
    missing_frontmatter: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class IndexWarning:
    code: str
    source: ConceptRef
    message: str
    target: ConceptRef | None = None
    unresolved_target: str | None = None


@dataclass(frozen=True)
class IndexError:
    code: str
    source: ConceptRef
    link_target: str
    message: str
    candidates: list[ConceptRef]


@dataclass
class IndexResult:
    success: bool
    warnings: list[IndexWarning] = field(default_factory=list)
    errors: list[IndexError] = field(default_factory=list)
    forward: dict[ConceptRef, list[GraphEdge]] = field(default_factory=dict)
    backlinks: dict[ConceptRef, list[GraphEdge]] = field(default_factory=dict)
    concepts: list[LoadedConcept] = field(default_factory=list)

