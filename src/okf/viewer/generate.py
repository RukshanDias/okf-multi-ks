from __future__ import annotations

import json
import os
import sys
from html import escape
from pathlib import Path
from typing import Any

import yaml

from okf.colors import DEFAULT_KS_COLOR, pick_ks_color
from okf.index import scan_workspace
from okf.models import EDGE_ASSOCIATION, ConceptRef, GraphEdge

# Viewer JS modules, concatenated in this order into the single output file
# (ADR-0007): core state first, boot last; renderers/detail define functions.
_VIZ_JS_FILES = [
    "viz-core.js",
    "viz-render-2d.js",
    "viz-render-3d.js",
    "viz-detail.js",
    "viz-chat.js",
    "viz-boot.js",
]


def _okf_cli_path() -> str:
    """CLI path baked into viz.html's regenerate command; the venv running
    this generator is the OKF system's, beside which `okf` is installed."""
    exe = "okf.exe" if os.name == "nt" else "okf"
    cand = Path(sys.executable).parent / exe
    return cand.as_posix() if cand.exists() else "okf"


def _offboard_rows(okf_cli: str, labels: list[str]) -> str:
    """Actions-panel Off-board group, one labeled row per configured KS
    (ADR-0006, amended): the copied command includes --yes so one paste
    executes; drop the flag by hand for a dry-run summary."""
    if not labels:
        return ""
    rows = ['<div class="actions-group">Off-board</div>']
    for label in labels:
        cmd = escape(f'& "{okf_cli}" offboard {label} --yes', quote=False)
        safe_label = escape(label)
        rows.append(
            '<div class="actions-row">'
            f'<span class="offboard-ks">{safe_label}</span>'
            f'<code class="offboard-cmd">{cmd}</code>'
            '<button type="button" class="offboard-copy">Copy</button>'
            f'<button type="button" class="offboard-live" data-ks="{safe_label}" hidden>Off-board now</button>'
            "</div>"
        )
    return "".join(rows)


def _ref_key(ks: str, path: str) -> str:
    return f"{ks}:{path.replace(chr(92), '/')}"


def _ensure_ks_colors(workspace_root: Path) -> dict[str, str]:
    """Return {KS label -> color}, assigning a random color to any KS that
    lacks one and persisting it back to okf.yaml. Colors are stable once set."""
    config_path = workspace_root / "okf.yaml"
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    ks_map = raw.get("ks")
    if ks_map is None:
        ks_map = raw.get("brains") or {}

    colors: dict[str, str] = {}
    used = {
        v["color"] for v in ks_map.values() if isinstance(v, dict) and v.get("color")
    }
    dirty = False
    for label, entry in ks_map.items():
        if not isinstance(entry, dict):
            continue
        color = entry.get("color")
        if not color:
            color = pick_ks_color(used)
            entry["color"] = color
            used.add(color)
            dirty = True
        colors[label] = color

    if dirty:
        config_path.write_text(
            yaml.safe_dump(raw, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
    return colors


def generate_workspace_visualization(
    workspace_root: Path,
    out_path: Path,
    *,
    name: str | None = None,
) -> dict[str, int]:
    """Build multi-KS HTML graph from live markdown scan + Association store.

    Does not read or write .okf/index.json. Single output file; KS filter is
    client-side in the viewer.
    """
    workspace_root = Path(workspace_root)
    result = scan_workspace(workspace_root)

    ks_colors = _ensure_ks_colors(workspace_root)

    concepts_by_key: dict[str, dict[str, Any]] = {}
    bodies: dict[str, str] = {}
    source_dirs: dict[str, str] = {}
    projected: dict[str, list[dict[str, str]]] = {}

    for concept in result.concepts:
        key = _ref_key(concept.brain, concept.rel_path)
        color = ks_colors.get(concept.brain, DEFAULT_KS_COLOR)
        concepts_by_key[key] = {
            "id": key,
            "label": concept.title,
            "type": concept.type,
            "description": concept.description,
            "resource": "",
            "tags": concept.tags,
            "color": color,
            "size": 30 + min(60, len(concept.body) // 200),
            "ks": concept.brain,
        }
        bodies[key] = concept.body
        source_dirs[key] = concept.path.resolve().parent.as_uri() + "/"

    nodes = [{"data": data} for data in concepts_by_key.values()]
    edges: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()

    forward: dict[ConceptRef, list[GraphEdge]] = result.forward
    for source_ref, graph_edges in forward.items():
        source_key = _ref_key(source_ref[0], source_ref[1])
        for edge in graph_edges:
            target_key = _ref_key(edge.target[0], edge.target[1])
            kind = edge.kind
            if source_key not in concepts_by_key or target_key not in concepts_by_key:
                continue
            if kind == EDGE_ASSOCIATION:
                tgt = concepts_by_key[target_key]
                projected.setdefault(source_key, []).append(
                    {
                        "id": target_key,
                        "label": tgt["label"],
                        "ks": tgt["ks"],
                    }
                )
                a, b = sorted((source_key, target_key))
                triple = (a, b, kind)
                if triple in seen:
                    continue
                seen.add(triple)
                edges.append(
                    {
                        "data": {
                            "id": f"{a}__{b}__{kind}",
                            "source": a,
                            "target": b,
                            "kind": kind,
                        },
                        "classes": "association",
                    }
                )
                continue

            triple = (source_key, target_key, kind)
            if triple in seen:
                continue
            seen.add(triple)
            edges.append(
                {
                    "data": {
                        "id": f"{source_key}__{target_key}__{kind}",
                        "source": source_key,
                        "target": target_key,
                        "kind": kind,
                    },
                    "classes": "intra",
                }
            )

    ks_labels = sorted({n["data"]["ks"] for n in nodes if n["data"].get("ks")})
    graph = {
        "nodes": nodes,
        "edges": edges,
        "bodies": bodies,
        "sourceDirs": source_dirs,
        "projected": projected,
        "types": sorted({n["data"]["type"] for n in nodes}),
        "knowledgeSystems": ks_labels,
        "ksColors": ks_colors,
    }

    template = (Path(__file__).parent / "templates" / "viz.html").read_text(
        encoding="utf-8"
    )
    static_dir = Path(__file__).parent / "static"
    css = (static_dir / "viz.css").read_text(encoding="utf-8")
    # Concatenated into one <script>; order is load-bearing for top-level
    # statements (core state before chat/boot), function declarations hoist.
    js = "\n".join(
        (static_dir / name).read_text(encoding="utf-8") for name in _VIZ_JS_FILES
    )
    js = "(function () {\n" + js + "\n})();"
    display_name = name or workspace_root.resolve().name
    okf_cli = _okf_cli_path()

    html = (
        template.replace("/*__VIZ_CSS__*/", css)
        .replace("/*__VIZ_JS__*/", js)
        .replace("__BUNDLE_NAME__", json.dumps(display_name))
        .replace("__BUNDLE_DATA__", json.dumps(graph))
        .replace("<!--__OKF_OFFBOARD_ROWS__-->", _offboard_rows(okf_cli, list(ks_colors)))
        .replace("__OKF_CLI__", json.dumps(okf_cli))
        .replace("__OKF_WORKSPACE__", json.dumps(workspace_root.resolve().as_posix()))
    )
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    return {
        "concepts": len(nodes),
        "edges": len(edges),
        "bytes": len(html.encode("utf-8")),
    }
