"""Smoke checks for Multi-KS viz Actions UI (ADR-0003)."""

from __future__ import annotations

import re
from pathlib import Path

from okf.viewer import generate_workspace_visualization
from tests.conftest import write_concept


def _workspace(dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "okf.yaml").write_text(
        "version: 1\n"
        "ks:\n"
        "  personal:\n"
        "    path: ks/personal\n",
        encoding="utf-8",
    )
    write_concept(
        dest / "ks" / "personal" / "note.md",
        type_="Learning",
        title="Note",
        description="A note.",
        body="Body.\n",
    )


def _workspace_two_ks(dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "okf.yaml").write_text(
        "version: 1\n"
        "ks:\n"
        "  personal:\n"
        "    path: ks/personal\n"
        "  work:\n"
        "    path: ks/work\n",
        encoding="utf-8",
    )
    write_concept(
        dest / "ks" / "personal" / "note.md",
        type_="Learning",
        title="Note",
        description="A note.",
        body="Body.\n",
    )
    write_concept(
        dest / "ks" / "work" / "doc.md",
        type_="Document",
        title="Doc",
        description="A doc.",
        body="Body.\n",
    )


def test_generated_viz_includes_actions_ui(tmp_path: Path):
    dest = tmp_path / "ws"
    _workspace(dest)
    out = dest / ".okf" / "viz.html"
    generate_workspace_visualization(dest, out)
    html = out.read_text(encoding="utf-8")

    assert 'id="actions"' in html
    assert ">Actions<" in html
    assert 'id="actions-dialog"' in html
    assert 'id="actions-cmd"' in html
    assert 'id="actions-copy"' in html
    assert '--workspace "${workspace}" viz' in html
    assert "const okfCli = " in html
    assert "__OKF_CLI__" not in html
    assert "__OKF_WORKSPACE__" not in html
    assert dest.resolve().as_posix() in html


def test_generated_viz_resolves_images_without_embedding_bytes(tmp_path: Path):
    dest = tmp_path / "ws"
    _workspace(dest)
    write_concept(
        dest / "ks" / "personal" / "nested" / "image.md",
        type_="Learning",
        title="Image",
        description="An image.",
        body="![Map](../assets/map.png)\n",
    )
    marker = b"NOT_EMBEDDED_IMAGE_BYTES"
    assets = dest / "ks" / "personal" / "assets"
    assets.mkdir()
    (assets / "map.png").write_bytes(marker)

    out = dest / ".okf" / "viz.html"
    generate_workspace_visualization(dest, out)
    html = out.read_text(encoding="utf-8")

    assert (dest / "ks" / "personal" / "nested").resolve().as_uri() in html
    assert "rewriteImages(bodyEl, conceptId)" in html
    assert marker.decode() not in html


def test_generated_viz_includes_view_mode_ui(tmp_path: Path):
    """View-mode dropdown + both renderers ship in the single file (ADR-0007)."""
    dest = tmp_path / "ws"
    _workspace(dest)
    out = dest / ".okf" / "viz.html"
    generate_workspace_visualization(dest, out)
    html = out.read_text(encoding="utf-8")

    assert 'id="view-mode"' in html
    assert 'id="graph-2d"' in html
    assert 'id="graph-3d"' in html
    assert "3d-force-graph" in html  # CDN script tag
    assert "function create2dRenderer" in html
    assert "function create3dRenderer" in html
    assert 'data-theme", "dark"' in html  # 3D forces the dark theme


def test_generated_viz_includes_chat_action_row(tmp_path: Path):
    dest = tmp_path / "ws"
    _workspace(dest)
    out = dest / ".okf" / "viz.html"
    generate_workspace_visualization(dest, out)
    html = out.read_text(encoding="utf-8")

    assert '<div class="actions-group">Serve (chat, live actions)</div>' in html
    assert 'id="actions-chat-cmd"' in html
    assert 'id="actions-chat-copy"' in html
    assert '--workspace "${workspace}" serve' in html


def test_generated_viz_includes_offboard_row_per_ks(tmp_path: Path):
    dest = tmp_path / "ws"
    _workspace_two_ks(dest)
    out = dest / ".okf" / "viz.html"
    generate_workspace_visualization(dest, out)
    html = out.read_text(encoding="utf-8")

    assert "offboard personal" in html
    assert "offboard work" in html
    assert html.count('class="offboard-cmd"') == 2
    assert html.count('class="offboard-copy"') == 2
    assert html.count('class="offboard-live"') == 2
    assert 'data-ks="work"' in html
    assert 'data-ks="personal"' in html
    assert '<div class="actions-group">Re-generate</div>' in html
    assert '<div class="actions-group">Off-board</div>' in html
    assert '<span class="offboard-ks">work</span>' in html
    assert '<span class="offboard-ks">personal</span>' in html


def test_offboard_command_uses_injected_cli_with_yes(tmp_path: Path):
    dest = tmp_path / "ws"
    _workspace(dest)
    out = dest / ".okf" / "viz.html"
    generate_workspace_visualization(dest, out)
    html = out.read_text(encoding="utf-8")

    m = re.search(
        r'<code class="offboard-cmd">&amp; "([^"]+)" offboard personal --yes</code>',
        html,
    )
    assert m, "offboard command not found in generated HTML"
    assert m.group(1).endswith(("okf", "okf.exe"))


def test_offboard_rows_absent_without_configured_ks(tmp_path: Path):
    dest = tmp_path / "ws"
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "okf.yaml").write_text("version: 1\nks: {}\n", encoding="utf-8")
    out = dest / ".okf" / "viz.html"
    generate_workspace_visualization(dest, out)
    html = out.read_text(encoding="utf-8")

    assert 'class="offboard-cmd"' not in html
    assert '" offboard ' not in html
    assert "__OKF_OFFBOARD_ROWS__" not in html
    assert '<div class="actions-group">Off-board</div>' not in html
