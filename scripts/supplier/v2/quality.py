"""V2 product quality gate — curate for premium brand standards."""

from __future__ import annotations

from typing import Optional

from ..config import MIN_IMAGE_SCORE, MIN_OPPORTUNITY_SCORE, TARGET_GROSS_MARGIN_PCT
from ..progress import ProgressLogger, get_logger
from .models import ProductOpportunity


def apply_quality_gate(opp: ProductOpportunity) -> ProductOpportunity:
    """Mark opportunity rejected if it fails brand quality thresholds."""
    reasons = list(opp.rejection_reasons)

    if opp.opportunity_score < MIN_OPPORTUNITY_SCORE:
        reasons.append(f"score_below_{MIN_OPPORTUNITY_SCORE}")

    if opp.image_score < MIN_IMAGE_SCORE:
        reasons.append(f"image_score_below_{MIN_IMAGE_SCORE}")

    if opp.pricing.margin_pct < TARGET_GROSS_MARGIN_PCT - 10:
        reasons.append("insufficient_margin")

    hard_rejects = {
        "blocked_niche_keyword",
        "off_category",
        "not_pet_relevant",
        "cost_too_low",
        "cost_too_high",
        "weak_images",
        "low_brandability",
    }
    if any(r in hard_rejects for r in reasons):
        opp.rejected = True
    elif len([r for r in reasons if r.startswith("score_below")]) > 0:
        opp.rejected = True
    elif opp.image_score < MIN_IMAGE_SCORE:
        opp.rejected = True

    opp.rejection_reasons = list(dict.fromkeys(reasons))
    return opp


def filter_opportunities(
    opportunities: list[ProductOpportunity],
    *,
    log: Optional[ProgressLogger] = None,
) -> tuple[list[ProductOpportunity], list[ProductOpportunity]]:
    log = log or get_logger()
    accepted: list[ProductOpportunity] = []
    rejected: list[ProductOpportunity] = []
    total = len(opportunities)

    log.phase(f"Quality gate — {total} products (min score {MIN_OPPORTUNITY_SCORE})")

    for idx, opp in enumerate(opportunities, start=1):
        opp = apply_quality_gate(opp)
        if opp.rejected:
            rejected.append(opp)
        else:
            accepted.append(opp)
        log.counter(
            idx,
            total,
            f"{'reject' if opp.rejected else 'accept'} score={opp.opportunity_score:.0f} {(opp.title_raw or '')[:40]}",
            every=max(1, total // 15),
        )

    accepted.sort(key=lambda o: o.opportunity_score, reverse=True)
    log.info(f"Curation — {len(accepted)} accepted, {len(rejected)} rejected")
    if accepted:
        log.detail(f"top pick: score {accepted[0].opportunity_score:.0f} — {accepted[0].title_raw[:50]}")
    return accepted, rejected
