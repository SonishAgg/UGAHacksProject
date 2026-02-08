import streamlit as st
import requests

# --------------------------------------------------
# CONFIG
# --------------------------------------------------
st.set_page_config(
    page_title="Media Search",
    layout="wide",
    initial_sidebar_state="collapsed"
)

TMDB_API_KEY = "24859a61465a5fcdca16003e3c27b9ef"
ANILIST_API_URL = "https://graphql.anilist.co"

# --------------------------------------------------
# HELPERS
# --------------------------------------------------
def normalize(tag: str) -> str:
    return tag.lower().strip()

def truncate(text: str, n: int = 300) -> str:
    if not text:
        return ""
    return text[:n] + "..." if len(text) > n else text

# --------------------------------------------------
# TMDB (MOVIES)
# --------------------------------------------------
@st.cache_data(ttl=3600)
def get_tmdb_genres():
    r = requests.get(
        "https://api.themoviedb.org/3/genre/movie/list",
        params={"api_key": TMDB_API_KEY},
        timeout=10,
    )
    r.raise_for_status()
    return {g["id"]: normalize(g["name"]) for g in r.json().get("genres", [])}

@st.cache_data(ttl=300)
def search_movies(query: str):
    r = requests.get(
        "https://api.themoviedb.org/3/search/movie",
        params={"api_key": TMDB_API_KEY, "query": query},
        timeout=10,
    )
    r.raise_for_status()
    return r.json().get("results", [])

# --------------------------------------------------
# ANILIST (ANIME / MANGA)
# --------------------------------------------------
ANILIST_QUERY = """
query ($search: String, $type: MediaType) {
  Page(perPage: 10) {
    media(search: $search, type: $type) {
      title {
        romaji
        english
      }
      description(asHtml: false)
      genres
    }
  }
}
"""

@st.cache_data(ttl=300)
def search_anilist(search: str, media_type: str):
    variables = {
        "search": search,
        "type": media_type
    }
    r = requests.post(
        ANILIST_API_URL,
        json={"query": ANILIST_QUERY, "variables": variables},
        timeout=10,
    )
    r.raise_for_status()
    data = r.json()
    return data["data"]["Page"]["media"]

# --------------------------------------------------
# UI
# --------------------------------------------------
st.title("🎥 Media Search")
st.caption("Search movies, anime, and manga using a single keyword.")

query = st.text_input(
    "Search",
    placeholder="Try: cyberpunk, romance, fantasy, action"
)

c1, c2, c3 = st.columns(3)
show_movies = c1.checkbox("Movies", value=True)
show_anime = c2.checkbox("Anime", value=True)
show_manga = c3.checkbox("Manga", value=True)

st.divider()

# --------------------------------------------------
# SEARCH
# --------------------------------------------------
if query:
    with st.spinner("Searching..."):
        genre_map = get_tmdb_genres()

        movies = search_movies(query) if show_movies else []
        anime = search_anilist(query, "ANIME") if show_anime else []
        manga = search_anilist(query, "MANGA") if show_manga else []

    if not movies and not anime and not manga:
        st.warning("No results found.")
        st.stop()

    # ------------------ Movies ------------------
    for m in movies:
        st.subheader(m.get("title") or "Untitled")
        st.caption("🎬 Movie")
        st.write(truncate(m.get("overview", "")))

        tags = [genre_map[g] for g in m.get("genre_ids", []) if g in genre_map]
        if tags:
            st.caption("Tags: " + ", ".join(tags))

        st.divider()

    # ------------------ Anime ------------------
    for a in anime:
        title = a["title"]["english"] or a["title"]["romaji"]
        st.subheader(title)
        st.caption("📺 Anime")

        description = a.get("description", "")
        st.write(truncate(description))

        tags = [normalize(t) for t in a.get("genres", [])]
        if tags:
            st.caption("Tags: " + ", ".join(tags))

        st.divider()

    # ------------------ Manga ------------------
    for m in manga:
        title = m["title"]["english"] or m["title"]["romaji"]
        st.subheader(title)
        st.caption("Manga")

        description = m.get("description", "")
        st.write(truncate(description))

        tags = [normalize(t) for t in m.get("genres", [])]
        if tags:
            st.caption("Tags: " + ", ".join(tags))

        st.divider()

else:
    st.info("Enter a keyword above to begin searching.")
