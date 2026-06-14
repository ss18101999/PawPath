#!/usr/bin/env python3
"""CLI entry point for PawPath Meta Marketing API tools."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from meta_marketing.api.meta_client import MetaMarketingClient
from meta_marketing.reports.daily_report import DailyReportGenerator
from meta_marketing.services.account_audit_service import AccountAuditService
from meta_marketing.services.account_service import AccountService
from meta_marketing.services.ad_analysis_service import AdAnalysisService
from meta_marketing.services.autonomous_optimizer import optimize_ai_campaigns
from meta_marketing.services.campaign_launcher import launch_ai_test_campaigns
from meta_marketing.services.campaign_service import CampaignService
from meta_marketing.utils.config import ConfigError, load_config
from meta_marketing.utils.logging import configure, get_logger


def _print_json(data: object) -> None:
    print(json.dumps(data, indent=2, default=str))


def _parse_day(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


def _client() -> MetaMarketingClient:
    return MetaMarketingClient(load_config(), log=get_logger())


def cmd_account_overview(args: argparse.Namespace) -> int:
    log = get_logger()
    log.phase("Meta Marketing — account overview")
    service = AccountService(_client())
    overview = service.get_overview(
        date_preset=args.preset if not args.day else None,
        day=_parse_day(args.day),
    )
    log.info("Done")
    _print_json(overview)
    return 0


def cmd_campaigns_list(args: argparse.Namespace) -> int:
    log = get_logger()
    log.phase("Meta Marketing — list campaigns")
    service = CampaignService(_client())
    result = {"campaigns": service.list_campaigns(limit=args.limit)}
    log.info("Done")
    _print_json(result)
    return 0


def cmd_campaigns_pause(args: argparse.Namespace) -> int:
    service = CampaignService(_client())
    result = service.pause_campaign(args.campaign_id)
    get_logger().info("Done")
    _print_json(result)
    return 0


def cmd_campaigns_resume(args: argparse.Namespace) -> int:
    service = CampaignService(_client())
    result = service.resume_campaign(args.campaign_id)
    get_logger().info("Done")
    _print_json(result)
    return 0


def cmd_campaigns_performance(args: argparse.Namespace) -> int:
    log = get_logger()
    log.phase("Meta Marketing — campaign performance")
    service = CampaignService(_client())
    if args.campaign_id:
        result = service.get_campaign_performance(
            args.campaign_id,
            date_preset=args.preset if not args.day else None,
            day=_parse_day(args.day),
        )
    else:
        result = {
            "campaigns": service.get_all_campaign_performance(
                date_preset=args.preset if not args.day else None,
                day=_parse_day(args.day),
                limit=args.limit,
            )
        }
    log.info("Done")
    _print_json(result)
    return 0


def cmd_ads_analyze(args: argparse.Namespace) -> int:
    log = get_logger()
    log.phase("Meta Marketing — ad analysis")
    service = AdAnalysisService(_client())
    result = service.analyze_ads(
        date_preset=args.preset if not args.day else None,
        day=_parse_day(args.day),
        limit=args.limit,
    )
    log.info("Done")
    _print_json(result)
    return 0


def cmd_launch(args: argparse.Namespace) -> int:
    log = get_logger()
    log.phase("PawPath autonomous campaign launch")
    result = launch_ai_test_campaigns()
    log.info("Done")
    _print_json(result)
    return 0


def cmd_optimize_ai(args: argparse.Namespace) -> int:
    log = get_logger()
    log.phase("PawPath autonomous optimization")
    result = optimize_ai_campaigns(date_preset=args.preset)
    log.info("Done")
    _print_json(result)
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    log = get_logger()
    log.phase("Meta Marketing — full account audit")
    service = AccountAuditService(_client())
    output_dir = Path(args.output_dir)
    if args.save:
        paths = service.generate_files(
            output_dir=output_dir,
            date_preset=args.preset if not args.day else None,
            day=_parse_day(args.day),
        )
        result = {
            "status": "ok",
            "period": _parse_day(args.day).isoformat() if args.day else args.preset,
            "files": {key: str(path) for key, path in paths.items()},
        }
    else:
        result = service.run(
            date_preset=args.preset if not args.day else None,
            day=_parse_day(args.day),
        )
    log.info("Done")
    _print_json(result)
    return 0


def cmd_report_daily(args: argparse.Namespace) -> int:
    log = get_logger()
    log.phase("Meta Marketing — daily report")
    generator = DailyReportGenerator(_client())
    output_dir = Path(args.output_dir)
    paths = generator.generate_files(output_dir=output_dir, day=_parse_day(args.day))
    log.info("Done")
    _print_json(
        {
            "status": "ok",
            "report_date": _parse_day(args.day).isoformat() if args.day else "yesterday",
            "files": {key: str(path) for key, path in paths.items()},
        }
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="PawPath Meta Marketing API — account insights, campaigns, ads, reports"
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress progress logs (JSON output only)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    account = sub.add_parser("account", help="Account performance overview")
    account.add_argument("--preset", default="last_7d", help="Meta date_preset (default: last_7d)")
    account.add_argument("--day", help="Specific day YYYY-MM-DD (overrides preset)")
    account.set_defaults(func=cmd_account_overview)

    campaigns = sub.add_parser("campaigns", help="Campaign management")
    campaign_sub = campaigns.add_subparsers(dest="campaign_command", required=True)

    c_list = campaign_sub.add_parser("list", help="List campaigns")
    c_list.add_argument("--limit", type=int, default=100)
    c_list.set_defaults(func=cmd_campaigns_list)

    c_pause = campaign_sub.add_parser("pause", help="Pause a campaign")
    c_pause.add_argument("campaign_id")
    c_pause.set_defaults(func=cmd_campaigns_pause)

    c_resume = campaign_sub.add_parser("resume", help="Resume a campaign")
    c_resume.add_argument("campaign_id")
    c_resume.set_defaults(func=cmd_campaigns_resume)

    c_perf = campaign_sub.add_parser("performance", help="Campaign performance metrics")
    c_perf.add_argument("campaign_id", nargs="?", help="Optional campaign ID (all if omitted)")
    c_perf.add_argument("--preset", default="last_7d")
    c_perf.add_argument("--day", help="Specific day YYYY-MM-DD")
    c_perf.add_argument("--limit", type=int, default=100)
    c_perf.set_defaults(func=cmd_campaigns_performance)

    ads = sub.add_parser("ads", help="Ad-level analysis")
    ads_sub = ads.add_subparsers(dest="ads_command", required=True)
    ads_analyze = ads_sub.add_parser("analyze", help="Identify winning/losing ads")
    ads_analyze.add_argument("--preset", default="last_7d")
    ads_analyze.add_argument("--day", help="Specific day YYYY-MM-DD")
    ads_analyze.add_argument("--limit", type=int, default=250)
    ads_analyze.set_defaults(func=cmd_ads_analyze)

    audit = sub.add_parser("audit", help="Full audit: campaigns, ad sets, ads, ranked report")
    audit.add_argument("--preset", default="last_30d", help="Meta date_preset (default: last_30d)")
    audit.add_argument("--day", help="Specific day YYYY-MM-DD")
    audit.add_argument(
        "--output-dir",
        default="data/meta_reports",
        help="Output directory when using --save",
    )
    audit.add_argument(
        "--save",
        action="store_true",
        help="Write JSON + CSV report files",
    )
    audit.set_defaults(func=cmd_audit)

    launch = sub.add_parser("launch", help="Phase 1-3: Select products & create AI test campaigns")
    launch.set_defaults(func=cmd_launch)

    opt_ai = sub.add_parser("optimize-ai", help="Phase 4: Autonomous optimize AI test campaigns")
    opt_ai.add_argument("--preset", default="last_7d")
    opt_ai.set_defaults(func=cmd_optimize_ai)

    report = sub.add_parser("report", help="Generate reports")
    report_sub = report.add_subparsers(dest="report_command", required=True)
    report_daily = report_sub.add_parser("daily", help="Daily JSON + CSV performance report")
    report_daily.add_argument("--day", help="Report day YYYY-MM-DD (default: yesterday UTC)")
    report_daily.add_argument(
        "--output-dir",
        default="data/meta_reports",
        help="Output directory (default: data/meta_reports)",
    )
    report_daily.set_defaults(func=cmd_report_daily)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    configure(verbose=not args.quiet)
    try:
        return args.func(args)
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        get_logger().warn(str(exc))
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
