from __future__ import annotations

from pathlib import Path

from okf.association_graph import associations_to_edges
from okf.associations import prune_associations_to_configured_ks
from okf.config import WorkspaceConfigError, load_workspace_config
from okf.graph import compute_backlinks, merge_edges
from okf.loader import frontmatter_warnings, image_warnings, load_brain
from okf.models import IndexResult, IndexWarning
from okf.resolver import resolve_links

_CHECK_FAIL_CODES = frozenset(
    {
        "cross_ks_markdown_link",
        "image_outside_assets",
        "missing_image_alt",
        "missing_required_frontmatter",
    }
)


def scan_workspace(workspace_root: Path) -> IndexResult:
    """Live-scan KS markdown + Association store. Does not write index.json."""
    config = load_workspace_config(workspace_root)
    concepts = []
    warnings: list[IndexWarning] = []

    configured = set(config.brains.keys())
    pruned = prune_associations_to_configured_ks(workspace_root, configured)
    if pruned:
        warnings.append(
            IndexWarning(
                code="associations_pruned",
                source=("", ""),
                message=(
                    f"Removed {pruned} association(s) touching KS labels "
                    "not in okf.yaml"
                ),
            )
        )

    for brain in config.brains.values():
        if not brain.available:
            if brain.if_missing == "error":
                raise WorkspaceConfigError(
                    f"KS {brain.label!r} path not found: {brain.path}"
                )
            warnings.append(
                IndexWarning(
                    code="missing_brain",
                    source=(brain.label, ""),
                    message=f"KS {brain.label!r} path not found; skipped: {brain.path}",
                )
            )
            continue
        concepts.extend(load_brain(brain))

    warnings.extend(frontmatter_warnings(concepts))
    warnings.extend(image_warnings(concepts))

    forward, link_warnings, errors = resolve_links(config, concepts)
    warnings.extend(link_warnings)

    assoc_forward, assoc_warnings = associations_to_edges(workspace_root, concepts)
    warnings.extend(assoc_warnings)
    forward = merge_edges(forward, assoc_forward)

    backlinks = compute_backlinks(forward)

    return IndexResult(
        success=len(errors) == 0,
        warnings=warnings,
        errors=errors,
        forward=forward,
        backlinks=backlinks,
        concepts=concepts,
    )


def check_workspace(workspace_root: Path) -> list[IndexWarning]:
    """Separation + required frontmatter violations (live scan, no index.json)."""
    result = scan_workspace(workspace_root)
    return [w for w in result.warnings if w.code in _CHECK_FAIL_CODES]
