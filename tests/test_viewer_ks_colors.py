from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

from okf.colors import KS_PALETTE
from okf.viewer import generate_workspace_visualization
from tests.conftest import write_concept


def _extract_bundle_data(html: str) -> dict:
    m = re.search(r"window\.BUNDLE\s*=\s*(\{.*?\});", html, re.DOTALL)
    assert m, "BUNDLE JSON not found in generated HTML"
    return json.loads(m.group(1))


def _build(dest: Path, *, personal_color: str | None) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    color_line = f'    color: "{personal_color}"\n' if personal_color else ""
    (dest / "okf.yaml").write_text(
        "version: 1\n"
        "ks:\n"
        "  personal:\n"
        "    path: ks/personal\n"
        f"{color_line}"
        "  work:\n"
        "    path: ks/work\n",
        encoding="utf-8",
    )
    write_concept(
        dest / "ks" / "personal" / "tracing.md",
        type_="Learning",
        title="Distributed Tracing",
        description="Tracing.",
        body="Personal note.\n",
    )
    write_concept(
        dest / "ks" / "work" / "relay.md",
        type_="Document",
        title="Event Relay",
        description="Relay.",
        body="Work note.\n",
    )


def _node_colors_by_ks(out: Path) -> dict[str, str]:
    data = _extract_bundle_data(out.read_text(encoding="utf-8"))
    return {n["data"]["ks"]: n["data"]["color"] for n in data["nodes"]}


def test_existing_color_is_used_and_missing_one_is_assigned(tmp_path: Path):
    dest = tmp_path / "ws"
    _build(dest, personal_color="#2563eb")
    out = tmp_path / "viz.html"
    generate_workspace_visualization(dest, out)

    by_ks = _node_colors_by_ks(out)
    assert by_ks["personal"] == "#2563eb"  # pre-set color preserved
    assert by_ks["work"] in KS_PALETTE  # missing color auto-assigned
    assert by_ks["work"] != by_ks["personal"]  # no repeats


def test_assigned_color_is_persisted_to_okf_yaml(tmp_path: Path):
    dest = tmp_path / "ws"
    _build(dest, personal_color=None)
    out = tmp_path / "viz.html"
    generate_workspace_visualization(dest, out)

    raw = yaml.safe_load((dest / "okf.yaml").read_text(encoding="utf-8"))
    persisted = {label: raw["ks"][label]["color"] for label in ("personal", "work")}
    assert persisted["personal"] in KS_PALETTE
    assert persisted["work"] in KS_PALETTE
    assert persisted["personal"] != persisted["work"]

    # Stable: a second run reuses the persisted colors (no reassignment).
    generate_workspace_visualization(dest, out)
    assert _node_colors_by_ks(out) == persisted
