"""Ingest a web URL into an OKF Learning using pipeline tools.

Uses fetch_url, write_concept_doc, and regenerate_indexes from reference_agent.
When GEMINI_API_KEY (or Vertex AI) is configured, summarizes the fetched page
with Gemini before writing. Otherwise writes a structured stub from fetch metadata.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

from reference_agent.bundle.index import regenerate_indexes
from reference_agent.sources.bundle import BundleSource
from reference_agent.tools.bundle_tools import write_concept_doc
from reference_agent.tools.context import clear_web_state, set_context, set_web_state
from reference_agent.tools.web_tools import fetch_url

_SUMMARY_PROMPT = """\
You are writing an Open Knowledge Format (OKF) learning document from a fetched web page.

Return ONLY valid markdown for the document body (no frontmatter). Structure:
1. One short intro paragraph.
2. ## sections for the main topics covered on the page.
3. Use bullet lists and tables where helpful.
4. End with a ## Citations section containing one markdown link to the source URL.
5. Omit ads, CTAs, navigation, and promotional content.
6. Be concrete and technical; preserve key terminology from the source.
7. Do NOT add See also / cross-links to documents/ or references/. Learning edges stay inside knowledge/ only (Learning→Learning). Outside concepts may link into this Learning later.

Source URL: {url}
Page title: {title}

Fetched page markdown:
---
{markdown}
---
"""


def _slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug or "learning"


def _summarize_with_gemini(url: str, title: str, markdown: str, model: str) -> str:
    from google import genai

    client = genai.Client()
    prompt = _SUMMARY_PROMPT.format(url=url, title=title or url, markdown=markdown[:30000])
    response = client.models.generate_content(model=model, contents=prompt)
    text = (getattr(response, "text", None) or "").strip()
    if not text:
        raise RuntimeError("Gemini returned empty body text")
    return text


def ingest_learning(
    *,
    url: str,
    bundle_root: Path,
    concept_id: str | None = None,
    title: str | None = None,
    model: str = "gemini-flash-latest",
) -> dict:
    bundle_root = Path(bundle_root)
    host = urlparse(url).netloc
    set_context(BundleSource(bundle_root), bundle_root)
    set_web_state({host}, max_pages=1, seeds=[url], max_depth=0)
    try:
        fetched = fetch_url(url)
        if "error" in fetched:
            raise RuntimeError(f"fetch_url failed: {fetched['error']}")

        page_title = title or fetched.get("title") or "Web Learning"
        slug = concept_id or f"knowledge/{_slugify(page_title)}"
        markdown = fetched.get("markdown") or ""

        try:
            body = _summarize_with_gemini(url, page_title, markdown, model)
        except Exception as exc:
            print(f"Gemini summarization unavailable ({exc}); using fetch excerpt.", file=sys.stderr)
            excerpt = "\n".join(line for line in markdown.splitlines() if line.strip())[:6000]
            body = (
                f"# {page_title}\n\n"
                f"This learning was ingested from a web page. Gemini summarization was "
                f"unavailable, so the excerpt below is taken directly from the fetched "
                f"markdown.\n\n"
                f"## Source excerpt\n\n{excerpt}\n\n"
                f"## Citations\n\n"
                f"* [{page_title}]({url})\n"
            )

        description = (
            f"Learning ingested from {urlparse(url).netloc}: "
            f"{page_title.rstrip('.')[:120]}."
        )
        frontmatter = {
            "type": "Learning",
            "title": page_title,
            "description": description,
            "resource": url,
            "tags": ["web-ingestion", "system-design", "message-queue"],
        }
        result = write_concept_doc(slug, frontmatter, body)
        if "error" in result:
            raise RuntimeError(result["error"])
    finally:
        clear_web_state()

    regenerate_indexes(bundle_root, model=model)
    return {"concept_id": slug, "path": result["path"], "bytes": result["bytes"]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest a web URL as an OKF Learning.")
    parser.add_argument("url", help="Seed URL to fetch")
    parser.add_argument("--out", required=True, type=Path, help="Bundle root directory")
    parser.add_argument("--concept-id", default=None, help="Concept id, e.g. knowledge/foo")
    parser.add_argument("--title", default=None, help="Override learning title")
    parser.add_argument("--model", default="gemini-flash-latest")
    args = parser.parse_args(argv)

    stats = ingest_learning(
        url=args.url,
        bundle_root=args.out,
        concept_id=args.concept_id,
        title=args.title,
        model=args.model,
    )
    print(
        f"Wrote {stats['concept_id']} → {stats['path']} ({stats['bytes']} bytes)",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
