from __future__ import annotations

from pathlib import Path


def index_dir(workspace_root: Path) -> Path:
    """Workspace overlay directory (Association store, Id overlay, viz).

    The Notebook home is itself named `.okf` (ADR-0004); nesting another
    `.okf/` inside it would be redundant, so overlay files sit flat there.
    """
    workspace_root = Path(workspace_root)
    if workspace_root.name == ".okf":
        return workspace_root
    return workspace_root / ".okf"
