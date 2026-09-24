from __future__ import annotations

import argparse
import sys
from pathlib import Path

from okf.chat import resolve_agent, run_server
from okf.associations import (
    AssociationNeighbor,
    associations_for_concept_ref,
    upsert_association,
)
from okf.config import WorkspaceConfigError, load_workspace_config
from okf.identity import resolve_stable_id
from okf.index import check_workspace
from okf.offboard import execute_offboard, plan_offboard
from okf.seed import (
    DEFAULT_SEED_CAP,
    accept_seed_pack,
    load_seed_pack,
    propose_seed_pack,
    seed_pack_path,
    write_seed_pack,
)
from okf.store import index_dir
from okf.viewer import generate_workspace_visualization


def _find_workspace(start: Path | None) -> Path:
    if start is not None:
        return Path(start).resolve()
    return Path.home() / ".okf"


def _cmd_check(args: argparse.Namespace) -> int:
    root = _find_workspace(args.workspace)
    try:
        violations = check_workspace(root)
    except WorkspaceConfigError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    for w in violations:
        print(f"error: {w.message}")

    if violations:
        print(
            f"check failed: {len(violations)} issue(s) "
            "(Separation, required frontmatter, and/or image requirements)",
            file=sys.stderr,
        )
        return 1

    print(
        "check passed: Separation OK, required frontmatter present, "
        "and image requirements met"
    )
    return 0


def _format_neighbor_line(neighbor: AssociationNeighbor) -> str:
    def field(text: str) -> str:
        return text.replace("\t", " ").replace("\n", " ").strip()

    cols = [
        f"{neighbor.ks}:{neighbor.path}",
        field(neighbor.title),
        field(neighbor.description),
        neighbor.concept_id,
    ]
    if neighbor.note:
        cols.append(field(neighbor.note))
    return "\t".join(cols)


def _cmd_associations(args: argparse.Namespace) -> int:
    root = _find_workspace(args.workspace)
    try:
        neighbors = associations_for_concept_ref(root, args.concept_ref)
    except (WorkspaceConfigError, LookupError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    if not neighbors:
        print("no associations")
        return 0
    for n in neighbors:
        print(_format_neighbor_line(n))
    return 0


def _cmd_associate(args: argparse.Namespace) -> int:
    root = _find_workspace(args.workspace)
    try:
        config = load_workspace_config(root)
        a_id = resolve_stable_id(root, config, args.a_ks, args.a_path)
        b_id = resolve_stable_id(root, config, args.b_ks, args.b_path)
    except (WorkspaceConfigError, LookupError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    assoc = upsert_association(
        root,
        a_ks=args.a_ks,
        a_concept_id=a_id,
        b_ks=args.b_ks,
        b_concept_id=b_id,
        source=args.source,
        note=args.note,
    )
    print(f"association {assoc.id}: {args.a_ks}:{args.a_path} <-> {args.b_ks}:{args.b_path}")
    return 0


def _cmd_seed_propose(args: argparse.Namespace) -> int:
    root = _find_workspace(args.workspace)
    try:
        candidates = propose_seed_pack(root, new_ks=args.ks, cap=args.cap)
    except (WorkspaceConfigError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    out = write_seed_pack(
        root, candidates, new_ks=args.ks, path=Path(args.out) if args.out else None
    )

    for i, c in enumerate(candidates, start=1):
        print(
            f"{i}. [{c.similarity_score}] {c.a_ks}:{c.a_path} <-> "
            f"{c.b_ks}:{c.b_path}  ({c.reason})"
        )
    print(f"wrote {len(candidates)} candidate(s) to {out}")
    return 0


def _cmd_seed_accept(args: argparse.Namespace) -> int:
    root = _find_workspace(args.workspace)
    path = Path(args.file) if args.file else seed_pack_path(root)
    if not path.is_file():
        print(f"error: seed pack not found: {path}", file=sys.stderr)
        return 1
    candidates = load_seed_pack(path)
    indexes = None
    if args.all:
        indexes = None
    elif args.index:
        indexes = set(args.index)
    else:
        print("error: pass --all or --index N (repeatable)", file=sys.stderr)
        return 1
    try:
        n = accept_seed_pack(root, candidates, indexes=indexes)
    except (WorkspaceConfigError, LookupError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(f"accepted {n} association(s) into Association store")
    return 0


def _cmd_viz(args: argparse.Namespace) -> int:
    root = _find_workspace(args.workspace)
    out = Path(args.out) if args.out else index_dir(root) / "viz.html"
    try:
        stats = generate_workspace_visualization(root, out)
    except (WorkspaceConfigError, FileNotFoundError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(
        f"wrote {out} ({stats['concepts']} concepts, {stats['edges']} edges)"
    )
    return 0


def _cmd_serve(args: argparse.Namespace) -> int:
    root = _find_workspace(args.workspace)
    try:
        agent_argv = resolve_agent(args.agent, root)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    out = index_dir(root) / "viz.html"
    try:
        stats = generate_workspace_visualization(root, out)
    except (WorkspaceConfigError, FileNotFoundError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(f"wrote {out} ({stats['concepts']} concepts, {stats['edges']} edges)")
    return run_server(agent_argv, workspace_root=root, viz_path=out)


def _cmd_offboard(args: argparse.Namespace) -> int:
    root = _find_workspace(args.workspace)
    try:
        plan = plan_offboard(root, args.label)
    except (WorkspaceConfigError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    if not args.yes:
        if plan.seed_pack_referenced:
            seed_fate = f"delete (references {plan.label!r})"
        elif plan.seed_pack_present:
            seed_fate = f"keep (does not reference {plan.label!r})"
        else:
            seed_fate = "none"
        print(f"offboard {plan.label} would remove:")
        print(f"  okf.yaml: ks entry {plan.label!r} ({plan.ks_path})")
        print(f"  associations: {plan.association_count} association(s)")
        print(f"  id-overlay: {plan.overlay_count} overlay entry(ies)")
        print(f"  seed-pack.json: {seed_fate}")
        print("nothing modified; re-run with --yes to execute")
        return 1

    execute_offboard(root, plan)
    print(f"offboarded {plan.label}; KS folder remains on disk: {plan.ks_path}")
    out = index_dir(root) / "viz.html"
    try:
        stats = generate_workspace_visualization(root, out)
    except (WorkspaceConfigError, OSError) as e:
        print(f"error: viz regeneration failed: {e}", file=sys.stderr)
        return 1
    print(
        f"wrote {out} ({stats['concepts']} concepts, {stats['edges']} edges)"
    )
    return 0


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="okf", description="OKF Multi-KS workspace CLI")
    p.add_argument(
        "--workspace",
        type=Path,
        default=None,
        help="Workspace root containing okf.yaml (default: ~/.okf).",
    )
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser(
        "check",
        help="Fail on Separation violations or missing required frontmatter",
    )

    associations = sub.add_parser(
        "associations",
        help="List Cross-KS association neighbors for a concept UUID or ks:path",
    )
    associations.add_argument(
        "concept_ref",
        help="Stable concept id (UUID) or ks:path (e.g. personal:tracing.md)",
    )

    associate = sub.add_parser(
        "associate",
        help="Upsert a Cross-KS association (agent/manual; C1)",
    )
    associate.add_argument("a_ks")
    associate.add_argument("a_path")
    associate.add_argument("b_ks")
    associate.add_argument("b_path")
    associate.add_argument(
        "--source",
        default="manual",
        choices=["seed", "ingest", "ask", "manual"],
    )
    associate.add_argument("--note", default=None)

    seed = sub.add_parser("seed", help="Seed pack propose / accept")
    seed_sub = seed.add_subparsers(dest="seed_command", required=True)
    propose = seed_sub.add_parser("propose", help="Catalog-first Seed pack")
    propose.add_argument("--ks", required=True, help="Newly added KS label")
    propose.add_argument("--cap", type=int, default=DEFAULT_SEED_CAP)
    propose.add_argument("--out", type=Path, default=None)
    accept = seed_sub.add_parser("accept", help="Write Seed pack into Association store")
    accept.add_argument("--file", type=Path, default=None)
    accept.add_argument("--all", action="store_true")
    accept.add_argument("--index", type=int, action="append", default=None)

    viz = sub.add_parser("viz", help="Generate Multi-KS HTML graph visualization")
    viz.add_argument("--out", type=Path, default=None)

    serve = sub.add_parser(
        "serve",
        help="Start OKF Server: regenerate viz, serve the viewer, open it",
    )
    serve.add_argument(
        "--agent",
        default=None,
        help="Agent name (built-in: claude, opencode; more via config.json).",
    )

    offboard = sub.add_parser(
        "offboard",
        help="Deregister a KS from the notebook (KS folder stays on disk)",
    )
    offboard.add_argument("label", help="Configured KS label to offboard")
    offboard.add_argument(
        "--yes",
        action="store_true",
        help="Execute; without it, print the removal summary and exit 1",
    )

    return p


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "check":
        return _cmd_check(args)
    if args.command == "associations":
        return _cmd_associations(args)
    if args.command == "associate":
        return _cmd_associate(args)
    if args.command == "seed":
        if args.seed_command == "propose":
            return _cmd_seed_propose(args)
        if args.seed_command == "accept":
            return _cmd_seed_accept(args)
    if args.command == "viz":
        return _cmd_viz(args)
    if args.command == "serve":
        return _cmd_serve(args)
    if args.command == "offboard":
        return _cmd_offboard(args)
    raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
