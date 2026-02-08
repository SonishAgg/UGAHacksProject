# ML/models/recommender.py

import json
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer
from sklearn.neighbors import NearestNeighbors
from models.tag_encoder import TagEncoder


class MediaRecommender:
    def __init__(self, model_name="all-MiniLM-L6-v2"):
        """
        all-MiniLM-L6-v2: fast, 384-dim, great for semantic similarity
        """
        self.encoder = SentenceTransformer(model_name)
        self.tag_encoder = TagEncoder()
        self.items = []         # list of raw item dicts
        self.embeddings = None  # numpy array (N, 384)
        self.knn = None

    def load_data(self, data_dir: str = "data"):
        """Load all media from JSON files."""
        data_path = Path(data_dir)

        # Load anime
        anime_file = data_path / "anime_list.json"
        if anime_file.exists():
            with open(anime_file) as f:
                for item in json.load(f):
                    item["media_type"] = "anime"
                    self.items.append(item)

        # Load manga
        manga_file = data_path / "manga_list.json"
        if manga_file.exists():
            with open(manga_file) as f:
                for item in json.load(f):
                    item["media_type"] = "manga"
                    self.items.append(item)

        # Load movies
        movies_file = data_path / "movies.json"
        if movies_file.exists():
            with open(movies_file) as f:
                raw = json.load(f)
                movie_list = raw.get("movies", raw) if isinstance(raw, dict) else raw
                for item in movie_list:
                    item["media_type"] = "movie"
                    self.items.append(item)

        print(f"Loaded {len(self.items)} total items")

    def build_index(self):
        """Encode all items and build KNN index."""
        print("Encoding items with Sentence-BERT...")

        # Convert each item to text via TagEncoder
        texts = [self.tag_encoder.encode(item) for item in self.items]

        # Batch encode (GPU if available)
        self.embeddings = self.encoder.encode(
            texts,
            show_progress_bar=True,
            batch_size=64,
            normalize_embeddings=True  # so dot product = cosine similarity
        )

        # Build KNN with cosine similarity
        self.knn = NearestNeighbors(
            n_neighbors=20,
            metric="cosine",
            algorithm="brute"  # fine for < 100k items
        )
        self.knn.fit(self.embeddings)
        print(f"Index built with {len(self.items)} items")

    def find_item(self, title: str) -> int | None:
        """Find item index by title (fuzzy match)."""
        title_lower = title.lower().strip()

        for i, item in enumerate(self.items):
            # Check various title fields
            titles_to_check = []
            if isinstance(item.get("title"), dict):
                titles_to_check.extend([
                    item["title"].get("romaji", ""),
                    item["title"].get("english", ""),
                ])
            elif isinstance(item.get("title"), str):
                titles_to_check.append(item["title"])

            for t in titles_to_check:
                if t and title_lower in t.lower():
                    return i
        return None

    def recommend(self, title: str, n: int = 10, cross_media: bool = True):
        """
        Get recommendations for a given title.
        
        Args:
            title: Name of anime, manga, or movie
            n: Number of recommendations
            cross_media: If True, recommend across all media types
        
        Returns:
            List of (item, distance) tuples
        """
        idx = self.find_item(title)
        if idx is None:
            print(f"'{title}' not found in database.")
            return []

        source = self.items[idx]
        source_type = source.get("media_type", "unknown")
        source_title = (
            source["title"].get("english") or source["title"].get("romaji")
            if isinstance(source["title"], dict) 
            else source["title"]
        )
        print(f"\nFound: {source_title} ({source_type})")

        # Query KNN
        distances, indices = self.knn.kneighbors(
            self.embeddings[idx].reshape(1, -1),
            n_neighbors=n + 1  # +1 because the item itself is included
        )

        results = []
        for dist, i in zip(distances[0], indices[0]):
            if i == idx:
                continue  # skip self

            item = self.items[i]

            # Filter by cross-media preference
            if not cross_media and item.get("media_type") != source_type:
                continue

            results.append((item, 1 - dist))  # convert distance to similarity

        return results[:n]

    def save_index(self, path: str = "data/embeddings.npz"):
        """Save embeddings to disk so we don't re-encode every time."""
        np.savez_compressed(path, embeddings=self.embeddings)
        print(f"Saved embeddings to {path}")

    def load_index(self, path: str = "data/embeddings.npz"):
        """Load pre-computed embeddings."""
        data = np.load(path)
        self.embeddings = data["embeddings"]
        self.knn = NearestNeighbors(
            n_neighbors=20, metric="cosine", algorithm="brute"
        )
        self.knn.fit(self.embeddings)
        print(f"Loaded embeddings from {path}")