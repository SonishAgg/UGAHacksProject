import streamlit as st
import requests

st.set_page_config(page_title="Descriptor Media Search", layout="wide")

TMDB_API_KEY = st.secrets["TMDB_API_KEY"]
ANILIST_API_URL = "https://graphql.anilist.co"

def truncate(text: str, n: int = 260) -> str:
    if not text:
        return ""
    return text[:n] + "..." if len(text) > n else text

def clean(s: str) -> str:
    return (s or "").strip()

# -----------------------------
# TMDB (Movies) - descriptor via "keyword" -> discover
# -----------------------------
@st.cache_data(ttl=3600)
def tmdb_genres():
    r = requests.get(
        "https://api.themoviedb.org/3/genre/movie/list",
        params={"api_key": TMDB_API_KEY},
        timeout=10,
    )
    r.raise_for_status()
    genres = r.json().get("genres", [])
    # name->id and id->name
    name_to_id = {g["name"].lower(): g["id"] for g in genres}
    id_to_name = {g["id"]: g["name"].lower() for g in genres}
    return name_to_id, id_to_name

@st.cache_data(ttl=300)
def tmdb_keyword_ids(descriptor: str, max_ids: int = 3):
    r = requests.get(
        "https://api.themoviedb.org/3/search/keyword",
        params={"api_key": TMDB_API_KEY, "query": descriptor},
        timeout=10,
    )
    r.raise_for_status()
    results = r.json().get("results", [])
    # take a few best matching keyword IDs
    return [k["id"] for k in results[:max_ids] if "id" in k]

@st.cache_data(ttl=300)
def tmdb_discover_movies(descriptor: str, limit: int = 12):
    name_to_id, id_to_name = tmdb_genres()

    # If descriptor matches an actual TMDB genre name, use with_genres too
    genre_id = name_to_id.get(descriptor.lower())

    # Also try keyword-based discovery for broader descriptors
    kw_ids = tmdb_keyword_ids(descriptor, max_ids=3)

    params = {
        "api_key": TMDB_API_KEY,
        "sort_by": "popularity.desc",
        "include_adult": "false",
        "page": 1,
    }
    if genre_id:
        params["with_genres"] = str(genre_id)
    if kw_ids:
        params["with_keywords"] = ",".join(str(x) for x in kw_ids)

    # If neither matched, discovery will be too broad; return empty
    if not genre_id and not kw_ids:
        return []

    r = requests.get("https://api.themoviedb.org/3/discover/movie", params=params, timeout=10)
    r.raise_for_status()
    items = r.json().get("results", [])[:limit]

    # Normalize tags (genres) from genre_ids
    out = []
    for m in items:
        tags = [id_to_name.get(gid) for gid in m.get("genre_ids", []) if gid in id_to_name]
        out.append({
            "title": m.get("title") or "Untitled",
            "description": m.get("overview") or "",
            "tags": [t for t in tags if t],
            "type": "Movie",
        })
    return out

# -----------------------------
# AniList (Anime/Manga) - descriptor via genre_in / tag_in
# -----------------------------
ANILIST_DESCRIPTOR_QUERY = """
query ($type: MediaType, $genre_in: [String], $tag_in: [String]) {
  Page(perPage: 12) {
    media(type: $type, genre_in: $genre_in, tag_in: $tag_in, sort: POPULARITY_DESC) {
      title { romaji english }
      description(asHtml: false)
      genres
      tags { name }
    }
  }
}
"""

@st.cache_data(ttl=300)
def anilist_by_descriptor(descriptor: str, media_type: str):
    # AniList expects exact-ish strings for genre/tag.
    # We'll try both: genre_in and tag_in with the same descriptor.
    variables = {
        "type": media_type,
        "genre_in": [descriptor],
        "tag_in": [descriptor],
    }
    r = requests.post(
        ANILIST_API_URL,
        json={"query": ANILIST_DESCRIPTOR_QUERY, "variables": variables},
        timeout=10,
    )
    r.raise_for_status()
    data = r.json()
    items = data.get("data", {}).get("Page", {}).get("media", []) or []

    out = []
    for it in items:
        title = it["title"].get("english") or it["title"].get("romaji") or "Untitled"
        genres = [g.lower() for g in (it.get("genres") or [])]
        tag_names = [t["name"].lower() for t in (it.get("tags") or []) if "name" in t]
        # Keep it simple: show genres + a few tags
        tags = list(dict.fromkeys(genres + tag_names[:6]))

        out.append({
            "title": title,
            "description": it.get("description") or "",
            "tags": tags,
            "type": "Anime" if media_type == "ANIME" else "Manga",
        })
    return out

# -----------------------------
# UI
# -----------------------------
st.title("🔎 Descriptor Media Search")
st.caption("Search by a descriptor (genre/tag/keyword), not by title. Examples: romance, cyberpunk, time travel, sports.")

descriptor = st.text_input("Descriptor", placeholder="e.g., romance, cyberpunk, time travel")

c1, c2, c3 = st.columns(3)
show_movies = c1.checkbox("Movies", value=True)
show_anime = c2.checkbox("Anime", value=True)
show_manga = c3.checkbox("Manga", value=True)

st.divider()

if descriptor:
    with st.spinner("Finding matches..."):
        results = []

        if show_movies:
            results += tmdb_discover_movies(descriptor)

        if show_anime:
            results += anilist_by_descriptor(descriptor, "ANIME")

        if show_manga:
            results += anilist_by_descriptor(descriptor, "MANGA")

    if not results:
        st.warning("No matches found for that descriptor. Try a simpler genre (e.g., action, romance, fantasy).")
    else:
        # Group by type so it's easy to read
        for section in ["Movie", "Anime", "Manga"]:
            section_items = [r for r in results if r["type"] == section]
            if not section_items:
                continue

            st.subheader(f"{section}s" if section != "Manga" else "Manga")
            for item in section_items:
                st.markdown(f"**{item['title']}**")
                st.write(truncate(item["description"]))
                if item["tags"]:
                    st.caption("Tags: " + ", ".join(item["tags"][:10]))
                st.divider()
else:
    st.info("Type a descriptor above to search.")
