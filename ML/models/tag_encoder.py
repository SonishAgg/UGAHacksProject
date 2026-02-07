# ML/models/tag_encoder.py

class TagEncoder:
    """
    Converts heterogeneous tags/keywords/genres into a single
    text string suitable for sentence embedding.
    """

    @staticmethod
    def encode(item: dict) -> str:
        """
        Build a weighted text representation.
        
        Anime/manga tags have ranks (0-100), so higher-ranked tags
        get repeated to increase their embedding weight.
        Movie keywords are treated as rank 50 (neutral).
        """
        parts = []

        # Genres (high importance)
        for genre in item.get("genres", []):
            parts.append(genre)
            parts.append(genre)  # double-weight genres

        # Ranked tags (anime/manga from AniList)
        for tag in item.get("tags", []):
            name = tag["name"]
            rank = tag.get("rank", 50)
            desc = tag.get("description", "")

            if rank >= 80:
                parts.extend([name] * 3)       # high confidence: 3x
                parts.append(desc)
            elif rank >= 60:
                parts.extend([name] * 2)       # medium confidence: 2x
            else:
                parts.append(name)             # low confidence: 1x

        # Flat keywords (movies from TMDB)
        for kw in item.get("keywords", []):
            parts.extend([kw] * 2)  # 2x weight, same as mid-rank tags

        # Description snippet (first 200 chars for context)
        desc = item.get("description", "")
        if desc:
            import re
            clean = re.sub(r'<[^>]+>', '', desc)  # strip HTML
            parts.append(clean[:200])

        return " . ".join(parts)