from __future__ import annotations

from pathlib import Path

import pytest

from okf.cli import main
from tests.conftest import write_concept


@pytest.mark.parametrize("workspace_root", ["personal_only"], indirect=True)
def test_personal_only_check_passes(workspace_root):
    assert main(["--workspace", str(workspace_root), "check"]) == 0
    assert not (workspace_root / ".okf" / "index.json").is_file()


@pytest.mark.parametrize("workspace_root", ["policy_violation"], indirect=True)
def test_cross_ks_markdown_fails_check(workspace_root):
    assert main(["--workspace", str(workspace_root), "check"]) != 0
    assert not (workspace_root / ".okf" / "index.json").is_file()


@pytest.mark.parametrize("workspace_root", ["dangling_link"], indirect=True)
def test_dangling_check_passes(workspace_root):
    assert main(["--workspace", str(workspace_root), "check"]) == 0


@pytest.mark.parametrize("workspace_root", ["ambiguous_link"], indirect=True)
def test_ambiguous_link_check_passes(workspace_root):
    assert main(["--workspace", str(workspace_root), "check"]) == 0


@pytest.mark.parametrize("workspace_root", ["personal_only"], indirect=True)
def test_missing_id_fails_check(workspace_root: Path):
    write_concept(
        workspace_root / "brains" / "personal" / "no-id.md",
        type_="Learning",
        title="No Id",
        description="Missing frontmatter id.",
        body="x\n",
        id_=False,
    )
    assert main(["--workspace", str(workspace_root), "check"]) != 0


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ("![](../assets/map.png)\n", 1),
        ("![Map](map.png)\n", 1),
        ("![Map](../assets/map.png)\n", 0),
    ],
)
@pytest.mark.parametrize("workspace_root", ["personal_only"], indirect=True)
def test_image_requirements(workspace_root: Path, body: str, expected: int):
    write_concept(
        workspace_root / "brains" / "personal" / "nested" / "image.md",
        type_="Learning",
        title="Image",
        description="Image validation.",
        body=body,
    )
    assert main(["--workspace", str(workspace_root), "check"]) == expected
