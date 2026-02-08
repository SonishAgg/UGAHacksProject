# ML/models/recommender.py

import json
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer
from sklearn.neighbors import NearestNeighbors
from models.tag_encoder import TagEncoder


class MediaRecommender:
    def __init__(self, model_name="all-MiniLM-L6-v2"):
        self.encoder = SentenceTransformer(model_name)
        self.tag_encoder = TagEncoder()
        self.items = []
        self.embeddings = None
        self.knn = None

    def load_data(self, data_dir: str = "data"):
        """Load all media from JSON files."""
        data_path = Path(data_dir)
        processed = data_path / "processed"

        # Load anime (check both data/ and data/processed/)
        for search_dir in [data_path, processed]:
            anime_file = search_dir / "anime_list.json"
            if anime_file.exists():
                with open(anime_file) as f:
                    for item in json.load(f):
                        item["media_type"] = "anime"
                        self.items.append(item)
                print(f"  Loaded anime from {anime_file}")
                break

        # Load manga
        for search_dir in [data_path, processed]:
            manga_file = search_dir / "manga_list.json"
            if manga_file.exists():
                with open(manga_file) as f:
                    for item in json.load(f):
                        item["media_type"] = "manga"
                        self.items.append(item)
                print(f"  Loaded manga from {manga_file}")
                break

        # Load movies
        for search_dir in [data_path, processed]:
            movies_file = search_dir / "movies.json"
            if movies_file.exists():
                with open(movies_file) as f:
                    raw = json.load(f)
                    movie_list = raw.get("movies", raw) if isinstance(raw, dict) else raw
                    for item in movie_list:
                        item["media_type"] = "movie"
                        self.items.append(item)
                print(f"  Loaded movies from {movies_file}")
                break

        # Count by type
        counts = {}
        for item in self.items:
            t = item.get("media_type", "unknown")
            counts[t] = counts.get(t, 0) + 1
        
        print(f"\nLoaded {len(self.items)} total items:")
        for t, c in sorted(counts.items()):
            print(f"  {t}: {c}")

    def build_index(self):
        """Encode all items and build KNN index."""
        print("\nEncoding items with Sentence-BERT...")

        texts = [self.tag_encoder.encode(item) for item in self.items]

        self.embeddings = self.encoder.encode(
            texts,
            show_progress_bar=True,
            batch_size=64,
            normalize_embeddings=True
        )

        self.knn = NearestNeighbors(
            n_neighbors=min(50, len(self.items)),
            metric="cosine",
            algorithm="brute"
        )
        self.knn.fit(self.embeddings)
        print(f"Index built with {len(self.items)} items")

    def _get_title(self, item: dict) -> str:
        """Extract display title from any media type."""
        title = item.get("title", "Unknown")
        if isinstance(title, dict):
            return title.get("english") or title.get("romaji") or "Unknown"
        return str(title)

    def find_item(self, title: str) -> int | None:
        """Find item index by title (fuzzy match)."""
        title_lower = title.lower().strip()

        # Exact match first
        for i, item in enumerate(self.items):
            if self._get_title(item).lower() == title_lower:
                return i

        # Substring match
        for i, item in enumerate(self.items):
            if title_lower in self._get_title(item).lower():
                return i

        return None

    def recommend(self, title: str, n_per_type: int = 3):
        """
        Get recommendations grouped by media type.

        Returns:
            dict with keys 'source', 'anime', 'manga', 'movie'
        """
        idx = self.find_item(title)
        if idx is None:
            print(f"'{title}' not found in database.")
            return None

        source = self.items[idx]
        source_title = self._get_title(source)
        source_type = source.get("media_type", "unknown")
        print(f"\nFound: {source_title} ({source_type})")

        # Query KNN — get plenty of neighbors so we have enough per type
        n_query = min(len(self.items), 200)
        distances, indices = self.knn.kneighbors(
            self.embeddings[idx].reshape(1, -1),
            n_neighbors=n_query
        )

        # Group by media type
        results = {"anime": [], "manga": [], "movie": []}

        for dist, i in zip(distances[0], indices[0]):
            if i == idx:
                continue

            item = self.items[i]
            mtype = item.get("media_type", "unknown")
            similarity = 1 - dist

            if mtype in results and len(results[mtype]) < n_per_type:
                results[mtype].append((item, similarity))

            # Stop early if we have enough of everything
            if all(len(v) >= n_per_type for v in results.values()):
                break

        return {
            "source": source,
            "anime": results["anime"],
            "manga": results["manga"],
            "movie": results["movie"],
        }

    def save_index(self, path: str = "data/embeddings.npz"):
        np.savez_compressed(path, embeddings=self.embeddings)
        print(f"Saved embeddings to {path}")

    def load_index(self, path: str = "data/embeddings.npz"):
        data = np.load(path)
        self.embeddings = data["embeddings"]
        self.knn = NearestNeighbors(
            n_neighbors=min(50, len(self.embeddings)),
            metric="cosine",
            algorithm="brute"
        )
        self.knn.fit(self.embeddings)
        print(f"Loaded embeddings from {path}")
