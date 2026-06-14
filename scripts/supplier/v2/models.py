"""V2 data models for product discovery and merchandising."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional


@dataclass
class ScoreBreakdown:
    popularity: float = 0.0
    demand: float = 0.0
    ratings: float = 0.0
    growth: float = 0.0
    quality: float = 0.0
    us_market: float = 0.0
    shipping: float = 0.0
    uniqueness: float = 0.0
    brandability: float = 0.0
    margin: float = 0.0

    @property
    def total(self) -> float:
        return (
            self.popularity
            + self.demand
            + self.ratings
            + self.growth
            + self.quality
            + self.us_market
            + self.shipping
            + self.uniqueness
            + self.brandability
            + self.margin
        )

    def to_dict(self) -> dict[str, float]:
        return asdict(self)


@dataclass
class ImageAssessment:
    url: str
    score: float
    width: int = 0
    height: int = 0
    bytes_size: int = 0
    rejected: bool = False
    reasons: list[str] = field(default_factory=list)


@dataclass
class PricingRecommendation:
    cost: float
    shipping_estimate: float
    landed_cost: float
    retail_price: float
    compare_at_price: float
    gross_margin: float
    margin_pct: float


@dataclass
class MerchandisedContent:
    title: str
    seo_title: str
    seo_description: str
    description_html: str
    benefits: list[str]
    features: list[str]
    faqs: list[dict[str, str]]
    tags: list[str]


@dataclass
class CollectionAssignment:
    collection_id: str
    collection_title: str
    collection_handle: str
    collection_tag: str
    created: bool = False
    category_key: str = ""


@dataclass
class ProductOpportunity:
    cj_pid: str
    cj_sku: str
    title_raw: str
    cost_usd: float
    listed_num: int
    inventory: int
    category_key: str
    search_query: str
    opportunity_score: float
    score_breakdown: ScoreBreakdown
    image_urls: list[str]
    image_score: float
    images: list[ImageAssessment]
    pricing: PricingRecommendation
    content: Optional[MerchandisedContent] = None
    collection: Optional[CollectionAssignment] = None
    cj_product: Optional[dict[str, Any]] = None
    rejected: bool = False
    rejection_reasons: list[str] = field(default_factory=list)
    shopify_id: Optional[str] = None
    shopify_handle: Optional[str] = None
    shopify_status: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "cj_pid": self.cj_pid,
            "cj_sku": self.cj_sku,
            "title_raw": self.title_raw,
            "cost_usd": self.cost_usd,
            "listed_num": self.listed_num,
            "inventory": self.inventory,
            "category_key": self.category_key,
            "search_query": self.search_query,
            "opportunity_score": round(self.opportunity_score, 1),
            "score_breakdown": self.score_breakdown.to_dict(),
            "image_score": round(self.image_score, 1),
            "pricing": asdict(self.pricing),
            "rejected": self.rejected,
            "rejection_reasons": self.rejection_reasons,
            "shopify_id": self.shopify_id,
            "shopify_status": self.shopify_status,
            "title": self.content.title if self.content else None,
            "collection": asdict(self.collection) if self.collection else None,
        }
