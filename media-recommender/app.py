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

TMDB_API_KEY = st.secrets["24859a61465a5fcdca16003e3c27b9ef"]
JIKAN_API = "https://api.jikan.moe/v4"

# --------------------------------------------------
# HELPERS
# --------------------------------------------------
def normalize(tag):
    return tag.lower().strip()

def truncate(text, n=300):
    return text[:n] + "..." if len(text) > n else text

# --------------------------------------------------
# TMDB (Movies)
# --------------------------------------------------
@st.cache_data(ttl=3600)
def get_tmdb_genres():
    r = requests.get(
        "https://api.themoviedb.org/3/genre/movie/list",
        params={"api_key": TMDB_API_KEY},
        timeout=10,
    )
    return {g["id"]: normalize(g["name"]) for g in r.json()["genres"]}

@st.cache_data(ttl=300)
def search_movies(query):
    r = requests.get(
        "https://api.themoviedb.org/3/search/movie",
        params={"api_key": TMDB_API_KEY, "query": query},
        timeout=10,
    )
    return r.json().get("results", [])

# --------------------------------------------------
# JIKAN (Anime / Manga)
# --------------------------------------------------
@st.cache_data(ttl=300)
def search_jikan(kind, query):
    r = requests.get(
        f"{JIKAN_API}/{kind}",
        params={"q": query, "limit": 10},
        timeout=10,
    )
    return r.json().get("data", [])

def extract_jikan_tags(item):
    tags = []
    for key in ("genres", "themes", "demographics"):
        for t in item.get(key, []):
            tags.append(normalize(t["name"]))
    return list(set(tags))

# --------------------------------------------------
# UI
# --------------------------------------------------
st.title("Media Search")
st.caption("Search movies, anime, and manga using a single keyword.")

query = st.text_input(
    "Search",
    placeholder="Try: cyberpunk, romance, action, fantasy"
)

col1, col2, col3 = st.columns(3)
with col1:
    show_movies = st.checkbox("Movies", value=True)
with col2:
    show_anime = st.checkbox("Anime", value=True)
with col3:
    show_manga = st.checkbox("Manga", value=True)

st.divider()

# --------------------------------------------------
# SEARCH
# --------------------------------------------------
if query:
    with st.spinner("Searching..."):
        genre_map = get_tmdb_genres()

        movies = search_movies(query) if show_movies else []
        anime = search_jikan("anime", query) if show_anime else []
        manga = search_jikan("manga", query) if show_manga else []

    # ------------------ Movies ------------------
    for m in movies:
        with st.container():
            st.subheader(m.get("title"))
            st.caption("🎬 Movie")

            overview = m.get("overview", "")
            if overview:
                st.write(truncate(overview))

            tags = [genre_map[g] for g in m.get("genre_ids", []) if g in genre_map]
            if tags:
                st.caption("Tags: " + ", ".join(tags))

            st.divider()

    # ------------------ Anime ------------------
    for a in anime:
        with st.container():
            st.subheader(a.get("title"))
            st.caption("Anime")

            synopsis = a.get("synopsis", "")
            if synopsis:
                st.write(truncate(synopsis))

            tags = extract_jikan_tags(a)
            if tags:
                st.caption("Tags: " + ", ".join(tags))

            st.divider()

    # ------------------ Manga ------------------
    for m in manga:
        with st.container():
            st.subheader(m.get("title"))
            st.caption("Manga")

            synopsis = m.get("synopsis", "")
            if synopsis:
                st.write(truncate(synopsis))

            tags = extract_jikan_tags(m)
            if tags:
                st.caption("Tags: " + ", ".join(tags))

            st.divider()

elif query == "":
    st.info("Enter a keyword above to begin searching.")
