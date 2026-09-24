from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml

from okf.associations import load_associations, remove_associations_for_ks
from okf.config import load_workspace_config
from okf.id_overlay import load_id_overlay, save_id_overlay
from okf.seed import load_seed_pack, seed_pack_path


@dataclass(frozen=True)
class OffboardPlan:
    label: str
    ks_path: Path
    association_count: int
    overlay_count: int
    seed_pack_present: bool
    seed_pack_referenced: bool


def plan_offboard(workspace_root: Path, label: str) -> OffboardPlan:
    config = load_workspace_config(workspace_root)
    if label not in config.brains:
        configured = ", ".join(config.brains) or "(none)"
        raise ValueError(f"unknown KS {label!r}; configured: {configured}")
    association_count = sum(
        1
        for a in load_associations(workspace_root)
        if a.a.ks == label or a.b.ks == label
    )
    prefix = f"{label}:"
    overlay_count = sum(
        1 for key in load_id_overlay(workspace_root) if key.startswith(prefix)
    )
    pack = seed_pack_path(workspace_root)
    seed_pack_present = pack.is_file()
    seed_pack_referenced = seed_pack_present and any(
        c.a_ks == label or c.b_ks == label for c in load_seed_pack(pack)
    )
    return OffboardPlan(
        label=label,
        ks_path=config.brains[label].path,
        association_count=association_count,
        overlay_count=overlay_count,
        seed_pack_present=seed_pack_present,
        seed_pack_referenced=seed_pack_referenced,
    )


def _drop_ks_from_okf_yaml(workspace_root: Path, label: str) -> None:
    """Atomic rewrite: temp file in the same dir, then os.replace."""
    config_path = Path(workspace_root) / "okf.yaml"
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    ks_key = "ks" if "ks" in raw else "brains"
    (raw.get(ks_key) or {}).pop(label, None)
    search_order = raw.get("link_search_order")
    if isinstance(search_order, list) and label in search_order:
        search_order.remove(label)
    tmp_path = config_path.with_name("okf.yaml.tmp")
    tmp_path.write_text(
        yaml.safe_dump(raw, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    os.replace(tmp_path, config_path)


def execute_offboard(workspace_root: Path, plan: OffboardPlan) -> None:
    _drop_ks_from_okf_yaml(workspace_root, plan.label)
    remove_associations_for_ks(workspace_root, plan.label)
    entries = load_id_overlay(workspace_root)
    prefix = f"{plan.label}:"
    kept = {k: v for k, v in entries.items() if not k.startswith(prefix)}
    if len(kept) != len(entries):
        save_id_overlay(workspace_root, kept)
    if plan.seed_pack_referenced:
        seed_pack_path(workspace_root).unlink()
