from __future__ import annotations

from okf.models import ConceptRef, GraphEdge


def compute_backlinks(
    forward: dict[ConceptRef, list[GraphEdge]],
) -> dict[ConceptRef, list[GraphEdge]]:
    backlinks: dict[ConceptRef, list[GraphEdge]] = {}
    for source, edges in forward.items():
        for edge in edges:
            backlinks.setdefault(edge.target, [])
            inbound = GraphEdge(target=source, kind=edge.kind)
            if inbound not in backlinks[edge.target]:
                backlinks[edge.target].append(inbound)
    for edges in backlinks.values():
        edges.sort(key=lambda e: (e.target[0], e.target[1], e.kind))
    return backlinks


def merge_edges(
    base: dict[ConceptRef, list[GraphEdge]],
    extra: dict[ConceptRef, list[GraphEdge]],
) -> dict[ConceptRef, list[GraphEdge]]:
    out: dict[ConceptRef, list[GraphEdge]] = {
        k: list(v) for k, v in base.items()
    }
    for source, edges in extra.items():
        bucket = out.setdefault(source, [])
        for edge in edges:
            if edge not in bucket:
                bucket.append(edge)
    return out
