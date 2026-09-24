"""Backward-compatible wrapper — prefer scripts/ingest_okf_concept.py."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ingest_okf_concept import ingest_okf_concept  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    if not argv and len(sys.argv) > 1:
        argv = sys.argv[1:]
    if not argv or argv[0].startswith("-"):
        print("usage: ingest_web_concept.py URL --out OUT --type TYPE ...", file=sys.stderr)
        return 2
    url = argv[0]
    rest = argv[1:]
    # Rewrite as ingest_okf_concept args
    new_argv = ["--url", url, *rest]
    if "--title" not in new_argv:
        print("--title is required; use scripts/ingest_okf_concept.py", file=sys.stderr)
        return 2
    if "--body-file" not in new_argv:
        print("--body-file is required; use scripts/ingest_okf_concept.py", file=sys.stderr)
        return 2

    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--url")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--type", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--concept-id", default=None)
    parser.add_argument("--description", default=None)
    parser.add_argument("--tag", action="append", default=None)
    parser.add_argument("--body-file", required=True, type=Path)
    parser.add_argument("--model", default="gemini-flash-latest")
    args = parser.parse_args(new_argv)

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
