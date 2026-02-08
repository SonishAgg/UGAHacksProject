import streamlit as st
import requests
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Any, Optional
import html

# ============================================================
# CONFIG
# ============================================================
st.set_page_config(page_title="Media Tag Search", layout="wide")

# Put these in .streamlit/secrets.toml
# TMDB_API_KEY = "..."
# JIKAN_BASE_URL = "https://api.jikan.moe/v4"   # optional override
TMDB_API_KEY = st.secrets.get("24859a61465a5fcdca16003e3c27b9ef")
JIKAN_BASE_URL = st.secrets.get("JIKAN_BASE_URL", "https://api.jikan.moe/v4")

if not TMDB_API_KEY:
    st.error("Missing TMDB_API_KEY. Add it to Streamlit secrets.")
    st.stop()

# We’ll treat “tags” as a unified concept across sources:
# - TMDB: genres (mapped from genre_ids)
# - Jikan: genres/demographics/themes (strings)
API_ENDPOINTS = {
    "Movies (TMDB)": "https://api.themoviedb.org/3/trending/movie/week",
    # Jikan endpoints are paginated; we’ll fetch page(s) based on user sidebar controls
    # These placeholders will be built dynamically.
}

# ============================================================
# UI HELPERS
# ============================================================
def render_tag_badge(tag: str, is_selected: bool = False) -> str:
    tag = html.escape(str(tag))
    bg = "#2563eb" if is_selected else "#334155"
    return f"""
    <span style="
        display:inline-block;
        padding:2px 8px;
        margin:2px 6px 2px 0;
        border-radius:999px;
        background:{bg};
        color:white;
        font-size:12px;
        line-height:20px;
        ">
        {tag}
    </span>
    """


def normalize_tag(tag: str) -> str:
    """Unify tag casing/spacing."""
    return " ".join(str(tag).lower().strip().split())


# Optional: simple synonym map to “cross reference” tags across APIs.
# You can expand this over time.
TAG_SYNONYMS = {
    # common differences
    "sci fi": "science fiction",
    "sci-fi": "science fiction",
    "scifi": "science fiction",
    "romcom": "romance",
    "slice-of-life": "slice of life",
    "sol": "slice of life",
    "shounen": "shonen",
    "shoujo": "shojo",
}


def canon_tag(tag: str) -> str:
    t = normalize_tag(tag)
    return TAG_SYNONYMS.get(t, t)


# ============================================================
# DATA LOADING
# ============================================================
@st.cache_data(ttl=86400)
def load_tmdb_genres(api_key: str) -> Dict[int, str]:
    url = "https://api.themoviedb.org/3/genre/movie/list"
    r = requests.get(url, params={"api_key": api_key}, timeout=10)
    r.raise_for_status()
    data = r.json()
    # id -> canonical tag
    return {g["id"]: canon_tag(g["name"]) for g in data.get("genres", [])}


@st.cache_data(ttl=300)
def fetch_tmdb_trending_movies(api_key: str) -> List[Dict[str, Any]]:
    url = "https://api.themoviedb.org/3/trending/movie/week"
    r = requests.get(url, params={"api_key": api_key}, timeout=10)
    r.raise_for_status()
    data = r.json()
    return data.get("results", []) if isinstance(data, dict) else []


@st.cache_data(ttl=300)
def fetch_jikan(
    base_url: str,
    media_type: str,
    query: Optional[str],
    pages: int = 1,
    sfw: bool = True,
) -> List[Dict[str, Any]]:
    """
    Jikan endpoints:
      - Anime search: /anime?q=...&page=...
      - Manga search: /manga?q=...&page=...
    If query is empty, Jikan still returns popular-ish results for page=1.
    """
    items: List[Dict[str, Any]] = []
    endpoint = f"{base_url}/{media_type}"

    params_base = {"page": 1}
    if query:
        params_base["q"] = query
    if sfw:
        params_base["sfw"] = "true"

    for p in range(1, max(1, pages) + 1):
        params = dict(params_base)
        params["page"] = p
        r = requests.get(endpoint, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        page_items = data.get("data", []) if isinstance(data, dict) else []
        items.extend(page_items)

    return items


def extract_jikan_tags(item: Dict[str, Any]) -> List[str]:
    """
    Jikan has multiple tag-like fields:
      - genres: [{name: ...}]
      - themes: [{name: ...}]
      - demographics: [{name: ...}]  (e.g., Shonen, Seinen)
    We'll merge them all into tags.
    """
    tags: List[str] = []
    for key in ("genres", "themes", "demographics"):
        vals = item.get(key) or []
        if isinstance(vals, list):
            for v in vals:
                name = v.get("name") if isinstance(v, dict) else None
                if name:
                    tags.append(canon_tag(name))
    # also some anime have "explicit_genres" in newer schemas; include if present
    vals = item.get("explicit_genres") or []
    if isinstance(vals, list):
        for v in vals:
            name = v.get("name") if isinstance(v, dict) else None
            if name:
                tags.append(canon_tag(name))
    # de-dupe
    return sorted(set([t for t in tags if t]))


def normalize_to_df(
    tmdb_items: List[Dict[str, Any]],
    tmdb_genre_map: Dict[int, str],
    jikan_anime: List[Dict[str, Any]],
    jikan_manga: List[Dict[str, Any]],
) -> pd.DataFrame:
    records: List[Dict[str, Any]] = []

    # TMDB movies -> tags from genre_ids
    for item in tmdb_items:
        title = item.get("title") or item.get("name") or "Untitled"
        desc = item.get("overview") or ""
        genre_ids = item.get("genre_ids") or []
        tags = []
        if isinstance(genre_ids, list):
            tags = [tmdb_genre_map.get(gid) for gid in genre_ids if gid in tmdb_genre_map]
        tags = sorted(set([t for t in tags if t]))

        records.append(
            {
                "title": str(title),
                "description": str(desc),
                "tags": tags,
                "source_api": "Movies (TMDB)",
                "media_type": "movie",
                "raw_data": item,
            }
        )

    # Jikan anime
    for item in jikan_anime:
        title = item.get("title") or item.get("title_english") or item.get("title_japanese") or "Untitled"
        desc = item.get("synopsis") or ""
        tags = extract_jikan_tags(item)
        records.append(
            {
                "title": str(title),
                "description": str(desc),
                "tags": tags,
                "source_api": "Anime (Jikan)",
                "media_type": "anime",
                "raw_data": item,
            }
        )

    # Jikan manga
    for item in jikan_manga:
        title = item.get("title") or item.get("title_english") or item.get("title_japanese") or "Untitled"
        desc = item.get("synopsis") or ""
        tags = extract_jikan_tags(item)
        records.append(
            {
                "title": str(title),
                "description": str(desc),
                "tags": tags,
                "source_api": "Manga (Jikan)",
                "media_type": "manga",
                "raw_data": item,
            }
        )

    return pd.DataFrame(records)


def extract_all_tags(df: pd.DataFrame) -> List[str]:
    all_tags = set()
    for tag_list in df["tags"]:
        if isinstance(tag_list, list):
            all_tags.update(tag_list)
    return sorted(all_tags)


# ============================================================
# SEARCH LOGIC
# ============================================================
def search_content(
    df: pd.DataFrame,
    text_query: Optional[str] = None,
    selected_tags: Optional[List[str]] = None,
    match_all_tags: bool = True,
    search_in_desc: bool = True,
    source_filter: Optional[List[str]] = None,
) -> pd.DataFrame:
    results = df.copy()

    # Filter by source (optional)
    if source_filter:
        results = results[results["source_api"].isin(source_filter)]

    # Text search
    if text_query:
        q = text_query.lower()
        title_mask = results["title"].str.lower().str.contains(q, na=False)
        if search_in_desc:
            desc_mask = results["description"].str.lower().str.contains(q, na=False)
            results = results[title_mask | desc_mask]
        else:
            results = results[title_mask]

    # Tag filtering
    if selected_tags:
        selected = [canon_tag(t) for t in selected_tags]

        def has_tags(item_tags):
            if not isinstance(item_tags, list):
                return False
            if match_all_tags:
                return all(t in item_tags for t in selected)
            return any(t in item_tags for t in selected)

        results = results[results["tags"].apply(has_tags)]

    return results


def display_result_card(row: pd.Series):
    with st.container():
        col1, col2 = st.columns([4, 1])

        with col1:
            st.markdown(f"### {row['title']}")
            desc = row["description"] or ""
            if len(desc) > 300:
                desc = desc[:300] + "..."
            st.caption(desc)

            tags = row["tags"] if isinstance(row["tags"], list) else []
            if tags:
                st.markdown(
                    "**Tags:** " + " ".join([render_tag_badge(t) for t in tags]),
                    unsafe_allow_html=True,
                )
            else:
                st.markdown("**Tags:** _None_")

        with col2:
            st.caption(f"Source: *{row['source_api']}*")
            if st.button("🔍 View Details", key=f"btn_{row.name}"):
                with st.expander("Full Details", expanded=True):
                    st.json(row["raw_data"])


# ============================================================
# CROSS-REFERENCE (TAG OVERLAP)
# ============================================================
def compute_tag_overlap(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build a small table that shows how many items in each source contain each tag.
    Helps “cross reference” genres/tags across APIs.
    """
    sources = sorted(df["source_api"].unique().tolist())
    rows = []
    all_tags = extract_all_tags(df)

    for tag in all_tags:
        row = {"tag": tag}
        for src in sources:
            subset = df[df["source_api"] == src]
            row[src] = int(subset["tags"].apply(lambda t: isinstance(t, list) and tag in t).sum())
        row["total"] = int(df["tags"].apply(lambda t: isinstance(t, list) and tag in t).sum())
        rows.append(row)

    out = pd.DataFrame(rows)
    # put most “cross-source” tags on top (appear in 2+ sources)
    src_cols = [c for c in out.columns if c not in ("tag", "total")]
    out["sources_with_tag"] = (out[src_cols] > 0).sum(axis=1)
    out = out.sort_values(by=["sources_with_tag", "total", "tag"], ascending=[False, False, True]).drop(
        columns=["sources_with_tag"]
    )
    return out


# ============================================================
# MAIN APP
# ============================================================
st.title("Tag-Based Media Search")
st.markdown("Search movies + anime/manga and filter by **shared tags** across sources.")

# Sidebar: data controls
st.sidebar.header("Data Sources")

include_sources = st.sidebar.multiselect(
    "Include sources",
    options=["Movies (TMDB)", "Anime (Jikan)", "Manga (Jikan)"],
    default=["Movies (TMDB)", "Anime (Jikan)", "Manga (Jikan)"],
)

st.sidebar.markdown("---")
st.sidebar.subheader("Anime/Manga (Jikan) options")

jikan_query = st.sidebar.text_input(
    "Anime/Manga keyword (optional)",
    placeholder="e.g., Naruto, cyberpunk, romance..."
)
jikan_pages = st.sidebar.slider("Pages to fetch (Jikan)", min_value=1, max_value=3, value=1)
jikan_sfw = st.sidebar.checkbox("SFW only (Jikan)", value=True)

# Load data
with st.spinner("Loading..."):
    tmdb_genre_map = load_tmdb_genres(TMDB_API_KEY)

    # Fetch concurrently
    with ThreadPoolExecutor(max_workers=3) as executor:
        fut_tmdb = executor.submit(fetch_tmdb_trending_movies, TMDB_API_KEY)

        # Only fetch Jikan if included; else keep empty lists
        fut_anime = None
        fut_manga = None
        if "Anime (Jikan)" in include_sources:
            fut_anime = executor.submit(fetch_jikan, JIKAN_BASE_URL, "anime", jikan_query or None, jikan_pages, jikan_sfw)
        if "Manga (Jikan)" in include_sources:
            fut_manga = executor.submit(fetch_jikan, JIKAN_BASE_URL, "manga", jikan_query or None, jikan_pages, jikan_sfw)

        tmdb_items = fut_tmdb.result() if "Movies (TMDB)" in include_sources else []
        jikan_anime = fut_anime.result() if fut_anime else []
        jikan_manga = fut_manga.result() if fut_manga else []

    df = normalize_to_df(tmdb_items, tmdb_genre_map, jikan_anime, jikan_manga)

# Apply source filter to df (so stats/tags match what user included)
df = df[df["source_api"].isin(include_sources)]

if df.empty:
    st.error("No data loaded (check API keys, rate limits, or filters).")
    st.stop()

all_tags = extract_all_tags(df)

# Sidebar: search filters
st.sidebar.markdown("---")
st.sidebar.header("Search Filters")

search_text = st.sidebar.text_input("Search titles & descriptions", placeholder="Enter keywords...")
tag_mode = st.sidebar.radio(
    "Tag match mode",
    ["Match ANY (OR)", "Match ALL (AND)"],
    help="OR: at least one tag. AND: must include all selected tags.",
)

selected_tags = st.sidebar.multiselect("Filter by tags", options=all_tags)
search_in_desc = st.sidebar.checkbox("Search in descriptions", value=True)

# Execute search
match_all = tag_mode == "Match ALL (AND)"
results = search_content(
    df,
    text_query=search_text if search_text else None,
    selected_tags=selected_tags if selected_tags else None,
    match_all_tags=match_all,
    search_in_desc=search_in_desc,
    source_filter=include_sources,
)

# Results summary
st.divider()
c1, c2, c3 = st.columns(3)
c1.metric("Results Found", len(results))
c2.metric("Items Loaded", len(df))
c3.metric("Unique Tags", len(all_tags))

# Active filters display
if search_text or selected_tags:
    parts = []
    if search_text:
        parts.append(f"text: '{search_text}'")
    if selected_tags:
        parts.append("tags: " + ", ".join(selected_tags))
    st.info(f"Active filters: **{' + '.join(parts)}**")

# Cross-reference panel
with st.expander("🔗 Cross-reference tags across sources (what overlaps?)", expanded=False):
    overlap_df = compute_tag_overlap(df)
    st.caption("Counts show how many items in each source contain a given tag.")
    st.dataframe(overlap_df, use_container_width=True, height=420)

# Display results
if results.empty:
    st.warning("No results.")
    st.caption("Try fewer tags, switch to 'Match ANY', or broaden your text query.")
else:
    st.success(f"Found {len(results)} items")

    view_mode = st.radio("Display mode", ["Cards", "Compact List"], horizontal=True)

    if view_mode == "Cards":
        for _, row in results.iterrows():
            display_result_card(row)
            st.divider()
    else:
        display_df = results[["title", "description", "tags", "source_api", "media_type"]].copy()
        display_df["tags"] = display_df["tags"].apply(lambda x: ", ".join(x) if isinstance(x, list) else "")
        st.dataframe(display_df, use_container_width=True, height=600)

        if len(results) < 50 and all_tags:
            st.caption("Tags in current results:")
            result_tags = set()
            for tags in results["tags"]:
                result_tags.update(tags)
            st.markdown(" ".join([render_tag_badge(t) for t in sorted(result_tags)]), unsafe_allow_html=True)
