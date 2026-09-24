from __future__ import annotations

import uuid
from pathlib import Path
from typing import Literal

import pytest

from reference_agent.bundle.document import OKFDocument


def write_concept(
    path: Path,
    *,
    type_: str,
    title: str,
    description: str,
    body: str,
    id_: str | None | Literal[False] = None,
) -> None:
    """Write a concept file. Default mints a UUID `id`. Pass id_=False to omit it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    frontmatter = {
        "type": type_,
        "title": title,
        "description": description,
        "timestamp": "2026-07-01T00:00:00+00:00",
    }
    if id_ is False:
        pass
    elif id_ is None:
        frontmatter["id"] = str(uuid.uuid4())
    else:
        frontmatter["id"] = id_
    doc = OKFDocument(
        frontmatter=frontmatter,
        body=body,
    )
    path.write_text(doc.serialize(), encoding="utf-8")


def cref(brain: str, path: str) -> tuple[str, str]:
    return (brain, path.replace("\\", "/"))


def edge_targets(edges) -> set[tuple[str, str]]:
    return {e.target for e in edges}


def edges_by_kind(edges, kind: str) -> set[tuple[str, str]]:
    return {e.target for e in edges if e.kind == kind}


def _write_okf_yaml(dest: Path, content: str) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "okf.yaml").write_text(content, encoding="utf-8")


def _build_personal_only(dest: Path) -> None:
    _write_okf_yaml(
        dest,
        """version: 1
brains:
  personal:
    path: brains/personal
    role: personal
link_search_order:
  - personal
""",
    )
    root = dest / "brains" / "personal"
    write_concept(
        root / "tracing.md",
        type_="Learning",
        title="Distributed Tracing",
        description="OpenTelemetry tracing fundamentals.",
        body="See [Message Queues](/queues.md) for async patterns.\n",
    )
    write_concept(
        root / "queues.md",
        type_="Learning",
        title="Message Queues",
        description="Queue-based messaging patterns.",
        body="Foundation for event-driven systems.\n",
    )


def _build_personal_and_work(dest: Path) -> None:
    _write_okf_yaml(
        dest,
        """version: 1
brains:
  personal:
    path: brains/personal
    role: personal
  work:
    path: brains/work
    role: work
link_search_order:
  - personal
  - work
""",
    )
    personal = dest / "brains" / "personal"
    tracing_id = "11111111-1111-1111-1111-111111111111"
    relay_id = "22222222-2222-2222-2222-222222222222"
    write_concept(
        personal / "tracing.md",
        type_="Learning",
        title="Distributed Tracing",
        description="OpenTelemetry tracing fundamentals.",
        body="See [Message Queues](/queues.md) for async patterns.\n",
        id_=tracing_id,
    )
    write_concept(
        personal / "queues.md",
        type_="Learning",
        title="Message Queues",
        description="Queue-based messaging patterns.",
        body="Foundation for event-driven systems.\n",
    )
    work = dest / "brains" / "work"
    write_concept(
        work / "event-relay.md",
        type_="Document",
        title="Configure Event Relay",
        description="Acme Event Relay setup.",
        body="See also [Mock CloudEvents](mock-events.md).\n",
        id_=relay_id,
    )
    write_concept(
        work / "mock-events.md",
        type_="Document",
        title="Mock CloudEvents",
        description="Produce mock events for testing.",
        body="Companion to event relay testing.\n",
    )
    from okf.associations import Association, AssociationEndpoint, save_associations

    save_associations(
        dest,
        [
            Association(
                id="33333333-3333-3333-3333-333333333333",
                a=AssociationEndpoint(ks="personal", concept_id=tracing_id),
                b=AssociationEndpoint(ks="work", concept_id=relay_id),
                source="manual",
                created_at="2026-07-01T00:00:00Z",
            )
        ],
    )


def _build_policy_violation(dest: Path) -> None:
    _write_okf_yaml(
        dest,
        """version: 1
brains:
  personal:
    path: brains/personal
    role: personal
  work:
    path: brains/work
    role: work
link_search_order:
  - personal
  - work
""",
    )
    personal = dest / "brains" / "personal"
    write_concept(
        personal / "public-roadmap.md",
        type_="Learning",
        title="Public Roadmap",
        description="Publishable planning notes.",
        body="Draft reference to [Secret Runbook](../work/secret-runbook.md).\n",
    )
    write_concept(
        personal / "safe-topic.md",
        type_="Learning",
        title="Safe Topic",
        description="Publishable note without forbidden links.",
        body="Standalone publishable content.\n",
    )
    write_concept(
        dest / "brains" / "work" / "secret-runbook.md",
        type_="Document",
        title="Secret Runbook",
        description="Internal incident response.",
        body="Confidential procedures.\n",
    )


def _build_ambiguous_link(dest: Path) -> None:
    _write_okf_yaml(
        dest,
        """version: 1
brains:
  personal:
    path: brains/personal
    role: personal
link_search_order:
  - personal
""",
    )
    personal = dest / "brains" / "personal"
    write_concept(
        personal / "roadmap.md",
        type_="Learning",
        title="Roadmap",
        description="Planning doc with ambiguous link.",
        body="TODO: unify [Relay Setup](relay-setup.md).\n",
    )
    write_concept(
        personal / "vendor-a" / "relay-setup.md",
        type_="Learning",
        title="Relay Setup A",
        description="Vendor A relay configuration.",
        body="Vendor A setup.\n",
    )
    write_concept(
        personal / "vendor-b" / "relay-setup.md",
        type_="Learning",
        title="Relay Setup B",
        description="Vendor B relay configuration.",
        body="Vendor B setup.\n",
    )


def _build_dangling_link(dest: Path) -> None:
    _write_okf_yaml(
        dest,
        """version: 1
brains:
  personal:
    path: brains/personal
    role: personal
link_search_order:
  - personal
""",
    )
    personal = dest / "brains" / "personal"
    write_concept(
        personal / "tracing.md",
        type_="Learning",
        title="Distributed Tracing",
        description="OpenTelemetry tracing fundamentals.",
        body="Tracing basics.\n",
    )
    write_concept(
        personal / "future-plans.md",
        type_="Learning",
        title="Future Plans",
        description="Links to not-yet-written concepts.",
        body="When ready, see [Service Mesh Guide](/service-mesh-guide.md).\n",
    )


_BUILDERS = {
    "personal_only": _build_personal_only,
    "personal_and_work": _build_personal_and_work,
    "policy_violation": _build_policy_violation,
    "ambiguous_link": _build_ambiguous_link,
    "dangling_link": _build_dangling_link,
}


@pytest.fixture
def workspace_root(tmp_path: Path, request: pytest.FixtureRequest) -> Path:
    name = request.param
    dest = tmp_path / "workspace"
    _BUILDERS[name](dest)
    return dest


@pytest.fixture
def indexed_workspace(workspace_root: Path):
    """Legacy name: live-scan workspace (no index.json)."""
    from okf.index import scan_workspace

    result = scan_workspace(workspace_root)
    return workspace_root, result
