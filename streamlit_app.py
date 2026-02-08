import streamlit as st
import sys
import os
import re

# Add the ML directory to path so we can import the recommender
ML_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ML")
sys.path.insert(0, ML_DIR)

st.set_page_config(page_title="Cross-Media Recommender", layout="wide")


@st.cache_resource
def load_recommender():
    """Load the recommender model once and cache it."""
    from models.recommender import MediaRecommender
    import numpy as np

    recommender = MediaRecommender()
    recommender.load_data(os.path.join(ML_DIR, "data"))

    emb_path = os.path.join(ML_DIR, "data", "embeddings.npz")
    if os.path.exists(emb_path):
        data = np.load(emb_path)
        if data["embeddings"].shape[0] == len(recommender.items):
            recommender.load_index(emb_path)
        else:
            recommender.build_index()
            recommender.save_index(emb_path)
    else:
        recommender.build_index()
        recommender.save_index(emb_path)

    return recommender


@st.cache_data
def get_all_titles(_recommender):
    """Build a searchable list of all titles with their media type."""
    titles = []
    for item in _recommender.items:
        title = item.get("title", "Unknown")
        if isinstance(title, dict):
            title = title.get("english") or title.get("romaji") or "Unknown"
        media_type = item.get("media_type", "unknown")
        emoji = {"anime": "📺", "manga": "📖", "movie": "🎬"}.get(media_type, "❓")
        titles.append(f"{emoji} {title} ({media_type})")
    return sorted(set(titles))


def get_cover_image(item: dict):
    """Extract cover image URL from any media type."""
    poster = item.get("poster_path") or item.get("poster", "")
    if poster and isinstance(poster, str):
        if not poster.startswith("http"):
            return f"https://image.tmdb.org/t/p/w300{poster}"
        return poster

    cover = item.get("coverImage")
    if isinstance(cover, dict):
        return cover.get("large") or cover.get("medium")

    return None


def get_display_title(item: dict) -> str:
    title = item.get("title", "Unknown")
    if isinstance(title, dict):
        return title.get("english") or title.get("romaji") or "Unknown"
    return str(title)


def get_description(item: dict) -> str:
    desc = item.get("description") or item.get("overview") or ""
    clean = re.sub(r'<[^>]+>', '', str(desc))
    if len(clean) > 300:
        clean = clean[:300] + "..."
    return clean


def get_year(item: dict) -> str:
    year = item.get("year") or item.get("seasonYear") or item.get("release_date", "")
    if isinstance(year, str) and len(year) >= 4:
        return year[:4]
    return str(year) if year else ""


def get_genres(item: dict) -> list:
    return item.get("genres", [])[:5]


# ─── Load model ───
with st.spinner("Loading recommender model..."):
    recommender = load_recommender()
    all_titles = get_all_titles(recommender)

# ─── UI ───
st.title("🎯 Cross-Media Recommender")
st.caption(
    "Enter a movie, anime, or manga title — get the most similar movie, anime, and manga!"
)

search_input = st.selectbox(
    "🔍 Search for a title",
    options=[""] + all_titles,
    index=0,
    placeholder="Start typing a title...",
)

st.divider()

if search_input and search_input != "":
    # Extract title from "📺 Title (anime)" format
    match = re.match(r'^[^\s]+\s+(.+)\s+\(\w+\)$', search_input)
    if match:
        clean_title = match.group(1)
    else:
        clean_title = search_input

    with st.spinner("Finding recommendations..."):
        results = recommender.recommend(clean_title, n_per_type=1)

    if not results:
        st.error(f"Could not find '{clean_title}' in the database. Try another title.")
    else:
        source = results["source"]
        source_title = get_display_title(source)
        source_type = source.get("media_type", "unknown")
        source_emoji = {"anime": "📺", "manga": "📖", "movie": "🎬"}.get(source_type, "❓")

        # ─── Source card ───
        st.markdown(f"### {source_emoji} You searched: **{source_title}**")
        src_col1, src_col2 = st.columns([1, 3])
        with src_col1:
            img = get_cover_image(source)
            if img:
                st.image(img, width=200)
        with src_col2:
            genres = get_genres(source)
            year = get_year(source)
            if year:
                st.markdown(f"**Year:** {year}")
            if genres:
                st.markdown(f"**Genres:** {', '.join(genres)}")
            desc = get_description(source)
            if desc:
                st.markdown(f"{desc}")

        st.divider()
        st.markdown("### 🎯 Top Recommendations")

        # ─── Three columns: Movie, Anime, Manga ───
        sections = [
            ("🎬 Movie", results["movie"]),
            ("📺 Anime", results["anime"]),
            ("📖 Manga", results["manga"]),
        ]

        col1, col2, col3 = st.columns(3)

        for col, (header, items) in zip([col1, col2, col3], sections):
            with col:
                st.markdown(f"#### {header}")

                if not items:
                    st.info("No match found.")
                    continue

                item, score = items[0]
                title = get_display_title(item)
                year = get_year(item)
                genres = get_genres(item)
                desc = get_description(item)

                img = get_cover_image(item)
                if img:
                    st.image(img, width=200)

                st.markdown(f"**{title}**")
                if year:
                    st.caption(f"📅 {year}")

                st.metric("Match", f"{score:.0%}")

                if genres:
                    genre_tags = " · ".join(genres)
                    st.caption(f"🏷️ {genre_tags}")

                if desc:
                    with st.expander("Description"):
                        st.write(desc)

else:
    st.info("👆 Select a title above to get cross-media recommendations!")

    st.markdown("### 💡 Try these:")
    examples = ["Banana Fish", "Attack on Titan", "The Godfather", "Naruto", "Spirited Away"]
    ecols = st.columns(len(examples))
    for ecol, ex in zip(ecols, examples):
        with ecol:
            st.code(ex, language=None)
