from __future__ import annotations

import re
from pathlib import Path

_LINK_RE = re.compile(r"\]\(([^)\s]+\.md)(?:#[A-Za-z0-9_\-]*)?\)")
_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)\)")


def extract_link_targets(body: str) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for m in _LINK_RE.finditer(body):
        target = m.group(1)
        if "://" in target:
            continue
        if target not in seen:
            seen.add(target)
            out.append(target)
    return out


def extract_image_refs(body: str) -> list[tuple[str, str]]:
    return [(m.group(1), m.group(2)) for m in _IMAGE_RE.finditer(body)]


def normalize_link_key(target: str) -> str:
    key = target.split("#", 1)[0]
    if key.endswith(".md"):
        key = key[:-3]
    key = key.lstrip("/")
    while key.startswith("../"):
        key = key[3:]
    while key.startswith("./"):
        key = key[2:]
    return key


def concept_matches_key(concept_id: str, key: str) -> bool:
    if concept_id == key or concept_id.endswith("/" + key):
        return True
    basename = key.rsplit("/", 1)[-1]
    if basename != key:
        if concept_id == basename or concept_id.endswith("/" + basename):
            return True
    return False


def resolve_link_path(target: str, doc_dir: Path, ks_root: Path) -> Path | None:
    """Absolute filesystem path for a .md link, or None for URLs."""
    if "://" in target:
        return None
    if target.startswith("/"):
        return (ks_root / target.lstrip("/")).resolve()
    return (doc_dir / target).resolve()


def path_escapes_ks(target: str, doc_dir: Path, ks_root: Path) -> bool:
    """True when a relative/absolute .md path resolves outside the KS root."""
    candidate = resolve_link_path(target, doc_dir, ks_root)
    if candidate is None:
        return False
    try:
        candidate.relative_to(ks_root.resolve())
        return False
    except ValueError:
        return True


def resolve_same_brain(
    target: str, doc_dir: Path, brain_root: Path
) -> str | None:
    """Return concept id (no .md) if target resolves inside brain_root."""
    candidate = resolve_link_path(target, doc_dir, brain_root)
    if candidate is None:
        return None
    brain_root_resolved = brain_root.resolve()
    try:
        resolved = candidate.relative_to(brain_root_resolved)
    except ValueError:
        return None
    rel = resolved.as_posix()
    if not rel.endswith(".md"):
        return None
    if not (brain_root / rel).is_file():
        return None
    return rel[:-3]
