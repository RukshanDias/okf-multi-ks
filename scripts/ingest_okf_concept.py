"""Ingest knowledge into an OKF concept using pipeline tools.

Modes:
- URL: --url + optional --body-file (fetch_url validates the page)
- Conversation: --body-file + --title (no fetch; Cursor-authored content)

Always ends with write_concept_doc + regenerate_indexes.
"""
from __future__ import annotations

import argparse
import re
import sys
import uuid
from pathlib import Path
from urllib.parse import urlparse

from reference_agent.bundle.index import regenerate_indexes
from reference_agent.sources.bundle import BundleSource
from reference_agent.tools.bundle_tools import write_concept_doc
from reference_agent.tools.context import clear_web_state, set_context, set_web_state
from reference_agent.tools.web_tools import fetch_url


def _slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug or "concept"


def _default_concept_id(okf_type: str, title: str) -> str:
    folder = {
        "learning": "knowledge",
        "document": "documents",
        "reference": "references",
    }.get(okf_type.lower(), "references")
    return f"{folder}/{_slugify(title)}"


def ingest_okf_concept(
    *,
    bundle_root: Path,
    okf_type: str,
    title: str,
    body_file: Path,
    url: str | None = None,
    concept_id: str | None = None,
    description: str | None = None,
    tags: list[str] | None = None,
    model: str = "gemini-flash-latest",
) -> dict:
    bundle_root = Path(bundle_root)
    body = Path(body_file).read_text(encoding="utf-8")
    cid = concept_id or _default_concept_id(okf_type, title)

    set_context(BundleSource(bundle_root), bundle_root)

    if url:
        host = urlparse(url).netloc
        set_web_state({host}, max_pages=1, seeds=[url], max_depth=0)
        try:
            fetched = fetch_url(url)
            if "error" in fetched:
                raise RuntimeError(f"fetch_url failed: {fetched['error']}")
        finally:
            clear_web_state()
        source_tag = "web-ingestion"
        desc = description or (
            f"{okf_type} ingested from {urlparse(url).netloc}: "
            f"{title.rstrip('.')[:120]}."
        )
        frontmatter: dict = {
            "type": okf_type,
            "title": title,
            "description": desc,
            "resource": url,
        }
    else:
        desc = description or (
            f"{okf_type} curated from conversation: {title.rstrip('.')[:120]}."
        )
        source_tag = "conversation"
        frontmatter = {
            "type": okf_type,
            "title": title,
            "description": desc,
        }

    tag_list = list(tags or [])
    if source_tag not in tag_list:
        tag_list.insert(0, source_tag)
    frontmatter["tags"] = tag_list
    if not frontmatter.get("id"):
        frontmatter["id"] = str(uuid.uuid4())

    result = write_concept_doc(cid, frontmatter, body)
    if "error" in result:
        raise RuntimeError(result["error"])

    regenerate_indexes(bundle_root, model=model)
    return {"concept_id": cid, "path": result["path"], "bytes": result["bytes"]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Ingest knowledge into an OKF concept (pipeline tools)."
    )
    parser.add_argument("--url", default=None, help="Seed URL to fetch (optional)")
    parser.add_argument("--out", required=True, type=Path, help="Bundle root directory")
    parser.add_argument(
        "--type",
        required=True,
        help="OKF frontmatter type (e.g. Learning, Document, Reference)",
    )
    parser.add_argument("--title", required=True, help="Concept title")
    parser.add_argument("--concept-id", default=None, help="Concept id, e.g. knowledge/foo")
    parser.add_argument("--description", default=None, help="Override one-line description")
    parser.add_argument("--tag", action="append", default=None, help="Frontmatter tag (repeatable)")
    parser.add_argument(
        "--body-file",
        required=True,
        type=Path,
        help="Agent-curated markdown body (required)",
    )
    parser.add_argument("--model", default="gemini-flash-latest")
    args = parser.parse_args(argv)

    stats = ingest_okf_concept(
        url=args.url,
        bundle_root=args.out,
        okf_type=args.type,
        title=args.title,
        concept_id=args.concept_id,
        description=args.description,
        tags=args.tag,
        body_file=args.body_file,
        model=args.model,
    )
    print(
        f"Wrote {stats['concept_id']} -> {stats['path']} ({stats['bytes']} bytes)",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
