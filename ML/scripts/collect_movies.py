"""
Main script to collect movie data from TMDb.

Usage:
    python scripts/collect_movies.py              # Default: ~200 movies
    python scripts/collect_movies.py --small      # Quick test: ~40 movies
    python scripts/collect_movies.py --large      # Full dataset: ~800+ movies
"""

import sys
import os

# Add project root to path so imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml.data_collection import MovieCollector


def collect_small():
    """Quick test — ~40 movies, takes ~2 minutes."""
    collector = MovieCollector()

    collector.collect_popular(pages=2)

    collector.save("movies_small.json")
    collector.stats()


def collect_default():
    """Default — ~200 movies, takes ~10 minutes."""
    collector = MovieCollector()

    collector.collect_popular(pages=5)
    collector.collect_top_rated(pages=5)

    collector.save("movies.json")
    collector.stats()


def collect_large():
    """
    Full dataset — ~800+ movies across genres and decades.
    Takes ~45 minutes.
    """
    collector = MovieCollector()

    # Popular and top rated
    collector.collect_popular(pages=5)
    collector.collect_top_rated(pages=5)

    # By genre (fills gaps in less popular genres)
    genres = {
        28: "Action",
        12: "Adventure",
        16: "Animation",
        35: "Comedy",
        80: "Crime",
        99: "Documentary",
        18: "Drama",
        14: "Fantasy",
        27: "Horror",
        10402: "Music",
        9648: "Mystery",
        10749: "Romance",
        878: "Sci-Fi",
        53: "Thriller",
        10752: "War",
        37: "Western",
    }
    for genre_id, genre_name in genres.items():
        collector.collect_by_genre(genre_id, genre_name, pages=2)

    # By decade (historical coverage)
    for decade in [1970, 1980, 1990, 2000, 2010, 2020]:
        collector.collect_by_decade(decade, pages=2)

    collector.save("movies_large.json")
    collector.stats()


if __name__ == "__main__":
    args = sys.argv[1:]

    if "--small" in args:
        collect_small()
    elif "--large" in args:
        collect_large()
    else:
        collect_default()