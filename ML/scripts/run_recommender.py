# ML/scripts/run_recommender.py

import sys
sys.path.insert(0, ".")

from models.recommender import MediaRecommender


def main():
    recommender = MediaRecommender()

    # Load all data
    recommender.load_data("data")

    # Build or load index
    try:
        recommender.load_index("data/embeddings.npz")
        print("Loaded cached embeddings")
    except FileNotFoundError:
        recommender.build_index()
        recommender.save_index("data/embeddings.npz")

    # Interactive loop
    print("\n" + "=" * 60)
    print("CROSS-MEDIA RECOMMENDER")
    print("Enter an anime, manga, or movie title to get recommendations.")
    print("Type 'quit' to exit.")
    print("=" * 60)

    while True:
        title = input("\n🎬 Enter title: ").strip()
        if title.lower() in ("quit", "exit", "q"):
            break

        results = recommender.recommend(title, n=10, cross_media=True)

        if not results:
            print("No results found. Try a different title.")
            continue

        print(f"\n{'Rank':<5} {'Type':<8} {'Score':<8} {'Title'}")
        print("-" * 60)

        for rank, (item, score) in enumerate(results, 1):
            media_type = item.get("media_type", "?")
            if isinstance(item.get("title"), dict):
                name = item["title"].get("english") or item["title"].get("romaji")
            else:
                name = item.get("title", "Unknown")

            emoji = {"anime": "📺", "manga": "📖", "movie": "🎬"}.get(media_type, "❓")
            print(f"{rank:<5} {emoji} {media_type:<6} {score:<8.3f} {name}")


if __name__ == "__main__":
    main()