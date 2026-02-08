# ML/scripts/run_recommender.py

import sys
sys.path.insert(0, ".")

from models.recommender import MediaRecommender


def display_results(results: dict):
    """Pretty-print grouped recommendations."""
    source = results["source"]

    title = source.get("title", "Unknown")
    if isinstance(title, dict):
        title = title.get("english") or title.get("romaji") or "Unknown"

    media_sections = [
        ("🎬 Similar Movies", results["movie"]),
        ("📺 Similar Anime", results["anime"]),
        ("📖 Similar Manga", results["manga"]),
    ]

    for header, items in media_sections:
        print(f"\n  {header}")
        print(f"  {'─' * 50}")

        if not items:
            print(f"  (no data available)")
            continue

        for rank, (item, score) in enumerate(items, 1):
            name = item.get("title", "Unknown")
            if isinstance(name, dict):
                name = name.get("english") or name.get("romaji") or "Unknown"

            genres = ", ".join(item.get("genres", [])[:3])
            year = item.get("year") or item.get("seasonYear") or ""

            print(f"  {rank}. {name} ({year})  [{score:.1%} match]")
            if genres:
                print(f"     Genres: {genres}")


def main():
    recommender = MediaRecommender()
    recommender.load_data("data")

    import os, numpy as np
    emb_path = "data/embeddings.npz"

    if os.path.exists(emb_path):
        old = np.load(emb_path)
        if old["embeddings"].shape[0] != len(recommender.items):
            print(f"Data changed ({old['embeddings'].shape[0]} -> {len(recommender.items)} items). Rebuilding...")
            recommender.build_index()
            recommender.save_index(emb_path)
        else:
            recommender.load_index(emb_path)
    else:
        recommender.build_index()
        recommender.save_index(emb_path)

    print("\n" + "=" * 60)
    print("  🎯 CROSS-MEDIA RECOMMENDER")
    print("  Enter an anime, manga, or movie title.")
    print("  Get the most similar movie, anime, and manga!")
    print("  Type 'quit' to exit.")
    print("=" * 60)

    while True:
        title = input("\n🔍 Enter title: ").strip()
        if title.lower() in ("quit", "exit", "q"):
            break

        results = recommender.recommend(title, n_per_type=3)

        if not results:
            print("No results found. Try a different title.")
            continue

        display_results(results)


if __name__ == "__main__":
    main()
