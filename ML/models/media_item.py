# ML/models/media_item.py

from dataclasses import dataclass, field

@dataclass
class MediaItem:
    id: str
    title: str
    media_type: str  # "anime", "manga", "movie"
    description: str
    genres: list[str] = field(default_factory=list)
    tags: list[dict] = field(default_factory=list)  # [{"name": ..., "rank": ...}]
    keywords: list[str] = field(default_factory=list)