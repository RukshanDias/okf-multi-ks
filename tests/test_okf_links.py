from __future__ import annotations

import pytest

from okf.links import extract_link_targets, normalize_link_key, resolve_same_brain


def test_extract_link_targets_ignores_external():
    body = "See [doc](local.md) and [web](https://example.com/x.md)."
    assert extract_link_targets(body) == ["local.md"]


def test_normalize_link_key_strips_parent_segments():
    assert normalize_link_key("../Knowledge/foo.md") == "Knowledge/foo"


def test_resolve_same_brain_root_absolute(tmp_path):
    root = tmp_path / "brain"
    doc_dir = root
    target = root / "queues.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("---\ntype: X\ntitle: Q\ndescription: d\ntimestamp: t\n---\n", encoding="utf-8")
    assert resolve_same_brain("/queues.md", doc_dir, root) == "queues"
