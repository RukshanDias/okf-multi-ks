from __future__ import annotations

from pathlib import Path
from typing import Any

from reference_agent.bundle.document import OKFDocument
from reference_agent.bundle.paths import concept_id_to_path
from reference_agent.sources.base import ConceptRef, Source

_INDEX_NAME = "index.md"


class BundleSource(Source):
    """Read concepts from an existing OKF bundle on disk."""

    name = "bundle"

    def __init__(self, bundle_root: Path):
        self.bundle_root = Path(bundle_root)

    def list_concepts(self) -> list[ConceptRef]:
        refs: list[ConceptRef] = []
        if not self.bundle_root.exists():
            return refs
        for md_path in sorted(self.bundle_root.rglob("*.md")):
            if md_path.name == _INDEX_NAME:
                continue
            rel = md_path.relative_to(self.bundle_root).with_suffix("")
            try:
                doc = OKFDocument.parse(md_path.read_text(encoding="utf-8"))
            except Exception:
                continue
            fm = doc.frontmatter or {}
            resource = fm.get("resource")
            refs.append(
                ConceptRef(
                    id=tuple(rel.parts),
                    type=str(fm.get("type") or "Unknown"),
                    resource=str(resource) if resource else None,
                    hint={"path": str(rel).replace("\\", "/")},
                )
            )
        return refs

    def read_concept(self, ref: ConceptRef) -> dict[str, Any]:
        path = concept_id_to_path(self.bundle_root, ref.id)
        if not path.exists():
            raise ValueError(f"Concept file not found: {ref.id_str}")
        doc = OKFDocument.parse(path.read_text(encoding="utf-8"))
        return {
            "frontmatter": doc.frontmatter,
            "body": doc.body,
            "path": str(path.relative_to(self.bundle_root)),
        }
