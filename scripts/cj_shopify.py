#!/usr/bin/env python3
"""
PawPath CJ Dropshipping ↔ Shopify integration CLI.

Version 1 (legacy): auth, research, import, fix, pipeline
Version 2 (autonomous): discover, run

Setup:
  1. cp .env.example .env
  2. Add CJ_API_KEY from CJ > My CJ > Authorization > API
  3. shopify store auth --store j53k50-mp.myshopify.com --scopes read_products,write_products,read_publications,write_publications,read_inventory,write_inventory,read_locations

Usage (V2 — recommended):
  python scripts/cj_shopify.py run --import-limit 5
  python scripts/cj_shopify.py discover --dry-run
  python scripts/cj_shopify.py run --dry-run --import-limit 10

Usage (V1 — legacy):
  python scripts/cj_shopify.py research --per-category 3
  python scripts/cj_shopify.py import --limit 5
  python scripts/cj_shopify.py fix
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env"
if ENV_FILE.exists():
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

sys.path.insert(0, str(ROOT))

from scripts.supplier.cj_client import CJClient, CJError  # noqa: E402
from scripts.supplier.importer import import_candidates  # noqa: E402
from scripts.supplier.research import research_candidates  # noqa: E402
from scripts.supplier import shopify_client  # noqa: E402
from scripts.supplier.shopify_client import ShopifyError  # noqa: E402
from scripts.supplier.v2.discovery import discover_products  # noqa: E402
from scripts.supplier.v2.pipeline import run_autonomous_pipeline  # noqa: E402
from scripts.supplier.v2.quality import filter_opportunities  # noqa: E402
from scripts.supplier.config import V2_OPPORTUNITIES_FILE  # noqa: E402
from scripts.supplier.progress import configure  # noqa: E402


def _init_progress(args: argparse.Namespace) -> None:
    quiet = getattr(args, "quiet", False)
    configure(verbose=not quiet)


def cmd_auth(_: argparse.Namespace) -> int:
    try:
        cj = CJClient()
        token = cj.authenticate()
        print("CJ authentication OK")
        print(f"  Token prefix: {token[:12]}...")
        return 0
    except CJError as exc:
        print(f"CJ auth failed: {exc}", file=sys.stderr)
        return 1


def cmd_research(args: argparse.Namespace) -> int:
    from scripts.supplier.progress import get_logger

    prog = get_logger()
    try:
        cj = CJClient()
        prog.phase(f"V1 research — top {args.per_category} per category")
        report = research_candidates(cj, per_category=args.per_category)
        prog.info(f"Found {report['total_candidates']} candidates")
        for cat, count in report["by_category"].items():
            prog.detail(f"{cat}: {count}")
        prog.info(f"Saved → data/cj_candidates.json")
        for item in report["candidates"]:
            prog.detail(
                f"[{item['category']}] {item['title']} "
                f"(score {item['score']:.0f}, ${item['cost_usd']:.2f})"
            )
        return 0
    except CJError as exc:
        prog.warn(f"Research failed: {exc}")
        return 1


def cmd_discover(args: argparse.Namespace) -> int:
    """V2: discovery + scoring + quality filter (no import)."""
    from scripts.supplier.progress import get_logger

    prog = get_logger()
    try:
        cj = CJClient()
        discovered = discover_products(cj, per_seed=args.per_seed, log=prog)
        accepted, rejected = filter_opportunities(discovered, log=prog)
        report = {
            "accepted": [o.to_dict() for o in accepted[:50]],
            "rejected_sample": [o.to_dict() for o in rejected[:20]],
            "totals": {"discovered": len(discovered), "accepted": len(accepted), "rejected": len(rejected)},
        }
        V2_OPPORTUNITIES_FILE.write_text(json.dumps(report, indent=2))
        prog.info(f"Saved → {V2_OPPORTUNITIES_FILE}")
        prog.phase(f"Top {args.show} accepted")
        for opp in accepted[: args.show]:
            prog.detail(
                f"[{opp.category_key}] score={opp.opportunity_score:.0f} "
                f"${opp.cost_usd:.2f}→${opp.pricing.retail_price:.2f} — {opp.title_raw[:60]}"
            )
        return 0
    except CJError as exc:
        prog.warn(f"Discovery failed: {exc}")
        return 1


def cmd_run(args: argparse.Namespace) -> int:
    """V2: full autonomous pipeline."""
    from scripts.supplier.progress import get_logger

    prog = get_logger()
    try:
        cj = CJClient()
        shop_id = args.shop_id or os.getenv("CJ_SHOP_ID")
        stats = run_autonomous_pipeline(
            cj,
            per_seed=args.per_seed,
            import_limit=args.import_limit,
            shop_id=shop_id,
            status=args.status,
            dry_run=args.dry_run,
            log=prog,
        )
        return 0 if stats.get("failed", 0) == 0 else 1
    except (CJError, ShopifyError) as exc:
        prog.warn(f"Pipeline failed: {exc}")
        return 1


def cmd_import(args: argparse.Namespace) -> int:
    from scripts.supplier.progress import get_logger

    prog = get_logger()
    try:
        cj = CJClient()
        shop_id = args.shop_id or os.getenv("CJ_SHOP_ID")
        prog.info(f"Importing up to {args.limit or 'all'} products as {args.status}...")
        log = import_candidates(
            cj,
            limit=args.limit,
            source_file=args.file,
            status=args.status,
            shop_id=shop_id,
        )
        prog.info(
            f"Done: {len(log['imported'])} imported, "
            f"{len(log['skipped'])} skipped, {len(log['failed'])} failed"
        )
        prog.info("Log → data/cj_import_log.json")
        return 0 if not log["failed"] else 1
    except (CJError, FileNotFoundError) as exc:
        prog.warn(f"Import failed: {exc}")
        return 1


def cmd_fix(args: argparse.Namespace) -> int:
    from scripts.supplier.progress import get_logger

    prog = get_logger()
    category_by_id: dict[str, str] = {}
    inventory_by_id: dict[str, int] = {}
    log_path = ROOT / "data" / "cj_import_log.json"
    if log_path.exists():
        log = json.loads(log_path.read_text())
        for row in log.get("imported") or []:
            pid = row.get("shopify_id")
            if pid:
                category_by_id[pid] = row.get("category") or "travel-gear"

    candidates_path = ROOT / "data" / "cj_candidates.json"
    if candidates_path.exists() and log_path.exists():
        data = json.loads(candidates_path.read_text())
        pid_to_inv = {c.get("cj_pid"): c.get("inventory") for c in data.get("candidates") or []}
        for row in json.loads(log_path.read_text()).get("imported") or []:
            shopify_id = row.get("shopify_id")
            cj_pid = row.get("cj_pid")
            if shopify_id and cj_pid and cj_pid in pid_to_inv:
                try:
                    inv = int(pid_to_inv[cj_pid] or 0)
                    if inv >= 10:
                        inventory_by_id[shopify_id] = inv
                except (TypeError, ValueError):
                    pass

    prog.info("Fixing CJ products (publish, category, inventory)...")
    try:
        result = shopify_client.fix_cj_products(
            category_by_id=category_by_id,
            inventory_by_id=inventory_by_id,
        )
        prog.info(f"Done: {len(result['fixed'])} fixed, {len(result['failed'])} failed")
        return 0 if not result["failed"] else 1
    except ShopifyError as exc:
        prog.warn(f"Fix failed: {exc}")
        return 1


def cmd_pipeline(args: argparse.Namespace) -> int:
    if cmd_research(args) != 0:
        return 1
    return cmd_import(args)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="PawPath CJ ↔ Shopify — V2 autonomous merchandising system"
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Minimal output (errors and final summary only)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_auth = sub.add_parser("auth", help="Test CJ API authentication")
    p_auth.set_defaults(func=cmd_auth)

    # --- V2 commands ---
    p_discover = sub.add_parser("discover", help="V2: discover & score products (no import)")
    p_discover.add_argument("--per-seed", type=int, default=8)
    p_discover.add_argument("--show", type=int, default=15, help="How many top results to print")
    p_discover.set_defaults(func=cmd_discover)

    p_run = sub.add_parser("run", help="V2: full autonomous discover → curate → import pipeline")
    p_run.add_argument("--per-seed", type=int, default=8)
    p_run.add_argument("--import-limit", type=int, default=5)
    p_run.add_argument("--status", type=str, default=os.getenv("V2_IMPORT_STATUS", os.getenv("IMPORT_STATUS", "DRAFT")))
    p_run.add_argument("--shop-id", type=str, default=None)
    p_run.add_argument("--dry-run", action="store_true", help="Discover & score only, no Shopify import")
    p_run.set_defaults(func=cmd_run)

    # --- V1 legacy commands ---
    p_research = sub.add_parser("research", help="[V1] Find CJ products per category")
    p_research.add_argument("--per-category", type=int, default=3)
    p_research.set_defaults(func=cmd_research)

    p_import = sub.add_parser("import", help="[V1] Import from data/cj_candidates.json")
    p_import.add_argument("--limit", type=int, default=None)
    p_import.add_argument("--file", type=str, default=None)
    p_import.add_argument("--status", type=str, default=os.getenv("IMPORT_STATUS", "DRAFT"))
    p_import.add_argument("--shop-id", type=str, default=None)
    p_import.set_defaults(func=cmd_import)

    p_fix = sub.add_parser("fix", help="Publish CJ products, set category & inventory")
    p_fix.set_defaults(func=cmd_fix)

    p_pipe = sub.add_parser("pipeline", help="[V1] Research then import")
    p_pipe.add_argument("--per-category", type=int, default=3)
    p_pipe.add_argument("--import-limit", type=int, default=None, dest="limit")
    p_pipe.add_argument("--file", type=str, default=None)
    p_pipe.add_argument("--status", type=str, default=os.getenv("IMPORT_STATUS", "DRAFT"))
    p_pipe.add_argument("--shop-id", type=str, default=None)
    p_pipe.set_defaults(func=cmd_pipeline)

    args = parser.parse_args()
    if args.command != "auth":
        _init_progress(args)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
