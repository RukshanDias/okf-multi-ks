from __future__ import annotations

from pathlib import Path

import yaml

from okf.models import BrainConfig, WorkspaceConfig


class WorkspaceConfigError(ValueError):
    pass


def load_workspace_config(workspace_root: Path) -> WorkspaceConfig:
    workspace_root = Path(workspace_root).resolve()
    config_path = workspace_root / "okf.yaml"
    if not config_path.is_file():
        raise WorkspaceConfigError(f"Workspace config not found: {config_path}")

    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise WorkspaceConfigError("okf.yaml must be a mapping")

    version = raw.get("version", 1)
    if version != 1:
        raise WorkspaceConfigError(f"Unsupported okf.yaml version: {version}")

    ks_raw = raw.get("ks")
    if ks_raw is None:
        ks_raw = raw.get("brains")
    if ks_raw is None:
        ks_raw = {}  # fresh notebook: no KS onboarded yet
    if not isinstance(ks_raw, dict):
        raise WorkspaceConfigError(
            "okf.yaml `ks` (or legacy `brains`) must be a mapping"
        )

    ks_library_raw = raw.get("ks_library")
    if ks_library_raw is not None and not isinstance(ks_library_raw, str):
        raise WorkspaceConfigError("ks_library must be a path string")
    # KS `path` entries resolve against the KS library when one is configured,
    # else against the workspace root (fixture/dev workspaces); absolute paths
    # win either way.
    ks_base = (
        (workspace_root / Path(ks_library_raw).expanduser()).resolve()
        if ks_library_raw
        else workspace_root
    )

    brains: dict[str, BrainConfig] = {}
    for label, spec in ks_raw.items():
        if not isinstance(spec, dict):
            raise WorkspaceConfigError(f"KS {label!r} must be a mapping")
        path_raw = spec.get("path")
        if not path_raw:
            raise WorkspaceConfigError(f"KS {label!r} requires a path")
        brain_path = (ks_base / path_raw).resolve()
        if_missing = spec.get("if_missing", "skip_with_warning")
        if if_missing not in ("error", "skip_with_warning"):
            raise WorkspaceConfigError(
                f"KS {label!r} has invalid if_missing: {if_missing!r}"
            )
        brains[label] = BrainConfig(
            label=label,
            path=brain_path,
            if_missing=if_missing,
            available=brain_path.is_dir(),
        )

    search_order = raw.get("link_search_order")
    if search_order is None:
        search_order = list(brains.keys())
    if not isinstance(search_order, list) or (brains and not search_order):
        raise WorkspaceConfigError("link_search_order must be a non-empty list")
    for label in search_order:
        if label not in brains:
            raise WorkspaceConfigError(
                f"link_search_order references unknown KS: {label!r}"
            )

    return WorkspaceConfig(
        root=workspace_root,
        brains=brains,
        link_search_order=[str(x) for x in search_order],
    )
