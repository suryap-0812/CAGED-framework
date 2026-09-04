"""
Synthetic Content Item Catalog Generator for CAGED Recommender System.
"""

import random
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class ContentItem(BaseModel):
    """Synthetic social platform content item."""

    item_id: str = Field(..., description="Unique content item ID")
    category: str = Field(..., description="Content category (e.g. news, gaming, education)")
    quality_score: float = Field(..., ge=0.0, le=1.0, description="Inherent content quality score")
    originality_score: float = Field(..., ge=0.0, le=1.0, description="Originality score (1.0 = highly original creator)")
    freshness_decay_rate: float = Field(default=0.1, ge=0.0, description="Time decay rate factor")
    is_promotional: bool = Field(default=False, description="Flag for sponsored / promotional content")


class ContentCatalog:
    """Manages the synthetic content item repository."""

    def __init__(self, num_items: int = 500, categories: Optional[List[str]] = None, seed: int = 42):
        self.num_items = num_items
        self.categories = categories or [
            "education",
            "news",
            "gaming",
            "lifestyle",
            "technology",
            "entertainment",
        ]
        self.rng = random.Random(seed)
        self.items: List[ContentItem] = []
        self._generate_catalog()

    def _generate_catalog(self) -> None:
        """Generates synthetic content items with realistic score distributions."""
        for i in range(self.num_items):
            cat = self.rng.choice(self.categories)
            # Quality follows beta-like distribution
            quality = round(min(1.0, max(0.0, self.rng.gauss(0.65, 0.20))), 3)
            # Originality score: 70% original, 30% aggregator/clip content
            is_orig = self.rng.random() < 0.70
            orig_score = round(self.rng.uniform(0.7, 1.0) if is_orig else self.rng.uniform(0.1, 0.4), 3)
            is_promo = self.rng.random() < 0.08  # 8% promotional posts

            item = ContentItem(
                item_id=f"item_{i:06d}",
                category=cat,
                quality_score=quality,
                originality_score=orig_score,
                freshness_decay_rate=round(self.rng.uniform(0.05, 0.20), 3),
                is_promotional=is_promo,
            )
            self.items.append(item)

    def get_candidate_items(self, category: Optional[str] = None, count: int = 20) -> List[ContentItem]:
        """Returns a subset of candidate content items for recommendation scoring."""
        if category:
            matched = [item for item in self.items if item.category == category]
            if len(matched) >= count:
                return self.rng.sample(matched, k=count)
        return self.rng.sample(self.items, k=min(count, len(self.items)))
