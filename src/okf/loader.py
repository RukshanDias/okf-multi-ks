from __future__ import annotations

from pathlib import Path
from urllib.parse import unquote, urlsplit

from reference_agent.bundle.document import OKFDocument, OKFDocumentError

from okf.links import extract_image_refs, extract_link_targets
from okf.models import BrainConfig, IndexWarning, LoadedConcept

_INDEX_NAME = "index.md"
_REQUIRED = ("type", "title", "description", "id")


def load_brain(brain: BrainConfig) -> list[LoadedConcept]:
    if not brain.available:
        return []

    concepts: list[LoadedConcept] = []
    root = brain.path
    for md_path in sorted(root.rglob("*.md")):
        if md_path.name == _INDEX_NAME:
            continue
        rel = md_path.relative_to(root)
        rel_path = rel.as_posix()
        concept_id = rel.with_suffix("").as_posix()
        try:
            doc = OKFDocument.parse(md_path.read_text(encoding="utf-8"))
        except OKFDocumentError:
            continue
        fm = doc.frontmatter or {}
        tags = fm.get("tags") or []
        if not isinstance(tags, list):
            tags = [str(tags)]
        raw_id = fm.get("id")
        uuid = str(raw_id).strip() if raw_id else None
        if not uuid:
            uuid = None

        missing: list[str] = []
        for name in _REQUIRED:
            if name == "id":
                if uuid is None:
                    missing.append("id")
                continue
            value = fm.get(name)
            if value is None or (isinstance(value, str) and not str(value).strip()):
                missing.append(name)

        concepts.append(
            LoadedConcept(
                brain=brain.label,
                path=md_path,
                rel_path=rel_path,
                concept_id=concept_id,
                title=str(fm.get("title") or concept_id),
                description=str(fm.get("description") or ""),
                type=str(fm.get("type") or "Unknown"),
                tags=[str(t) for t in tags],
                body=doc.body or "",
                link_targets=extract_link_targets(doc.body or ""),
                uuid=uuid,
                missing_frontmatter=missing,
            )
        )
    return concepts


def frontmatter_warnings(concepts: list[LoadedConcept]) -> list[IndexWarning]:
    out: list[IndexWarning] = []
    for concept in concepts:
        if not concept.missing_frontmatter:
            continue
        source = (concept.brain, concept.rel_path)
        out.append(
            IndexWarning(
                code="missing_required_frontmatter",
                source=source,
                message=(
                    f"{source[0]}:{source[1]} missing required frontmatter: "
                    + ", ".join(concept.missing_frontmatter)
                ),
            )
        )
    return out


def image_warnings(concepts: list[LoadedConcept]) -> list[IndexWarning]:
    out: list[IndexWarning] = []
    for concept in concepts:
        source = (concept.brain, concept.rel_path)
        ks_root = concept.path.parents[len(Path(concept.rel_path).parts) - 1]
        assets_root = (ks_root / "assets").resolve()
        for alt, target in extract_image_refs(concept.body):
            if not alt.strip():
                out.append(
                    IndexWarning(
                        code="missing_image_alt",
                        source=source,
                        message=(
                            f"{source[0]}:{source[1]} image {target!r} "
                            "has blank alt text"
                        ),
                    )
                )
            parsed = urlsplit(target)
            if parsed.scheme in {"http", "https"}:
                continue
            candidate = (concept.path.parent / unquote(parsed.path)).resolve()
            try:
                candidate.relative_to(assets_root)
            except ValueError:
                out.append(
                    IndexWarning(
                        code="image_outside_assets",
                        source=source,
                        message=(
                            f"{source[0]}:{source[1]} local image {target!r} "
                            "must be stored under the KS assets/ directory"
                        ),
                    )
                )
    return out
