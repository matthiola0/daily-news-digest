"""Shared data model for collected news items."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class NewsItem:
    title: str
    url: str
    source: str
    description: str = ""
    published: datetime | None = None
    extra: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "title": self.title,
            "url": self.url,
            "source": self.source,
            "description": self.description,
            "published": self.published.isoformat() if self.published else None,
            **self.extra,
        }
