from __future__ import annotations

import json
import uuid
from pathlib import Path

from okf.store import index_dir


def id_overlay_path(workspace_root: Path) -> Path:
    return index_dir(workspace_root) / "id-overlay.json"


def load_id_overlay(workspace_root: Path) -> dict[str, str]:
    path = id_overlay_path(workspace_root)
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("version") != 1:
        raise ValueError(f"Unsupported id-overlay schema at {path}")
    entries = data.get("entries") or {}
    if not isinstance(entries, dict):
        raise ValueError(f"id-overlay entries must be a mapping at {path}")
    return {str(k): str(v) for k, v in entries.items()}


def save_id_overlay(workspace_root: Path, entries: dict[str, str]) -> Path:
    out_dir = index_dir(workspace_root)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = id_overlay_path(workspace_root)
    path.write_text(
        json.dumps({"version": 1, "entries": entries}, indent=2),
        encoding="utf-8",
    )
    return path


def overlay_key(ks: str, rel_path: str) -> str:
    return f"{ks}:{rel_path.replace(chr(92), '/')}"


def ensure_overlay_id(
    workspace_root: Path, ks: str, rel_path: str
) -> tuple[str, bool]:
    """Return (uuid, created). Does not rewrite concept markdown."""
    entries = load_id_overlay(workspace_root)
    key = overlay_key(ks, rel_path)
    if key in entries:
        return entries[key], False
    new_id = str(uuid.uuid4())
    entries[key] = new_id
    save_id_overlay(workspace_root, entries)
    return new_id, True
