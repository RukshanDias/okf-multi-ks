from __future__ import annotations

from pathlib import Path

import pytest

from okf.index import scan_workspace
from okf.links import concept_matches_key
from tests.conftest import cref, write_concept


def test_concept_matches_key_with_directory_prefix():
    assert concept_matches_key(
        "message-queue-system-design", "Knowledge/message-queue-system-design"
    )


@pytest.mark.parametrize("workspace_root", ["personal_and_work"], indirect=True)
def test_cross_ks_relative_path_rejected(workspace_root: Path):
    write_concept(
        workspace_root / "brains" / "work" / "relay-prefix.md",
        type_="Document",
        title="Relay Prefix",
        description="Uses Knowledge-prefixed cross link.",
        body="See [Queues](../personal/queues.md).",
    )
    result = scan_workspace(workspace_root)
    assert cref("personal", "queues.md") not in {
        e.target for e in result.forward.get(cref("work", "relay-prefix.md"), [])
    }
    assert any(
        w.code == "cross_ks_markdown_link"
        and w.source == cref("work", "relay-prefix.md")
        for w in result.warnings
    )
