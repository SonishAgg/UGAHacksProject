import streamlit as st
import requests
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Set
import html


API_ENDPOINTS = {"Movies": "https://api.themoviedb.org/3"
    
}

st.set_page_config(page_title="Media Tag Search", layout="wide")

# --- DATA LOADING ---
@st.cache_data(ttl=300)
def load_apis() -> Dict[str, List[Dict]]:
    """Load data from Sources"""
    results = {}
    
    def fetch(name: str, url: str):
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            return name, data if isinstance(data, list) else [data]
        except Exception as e:
            return name, {"error": str(e)}
    
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {executor.submit(fetch, name, url): name 
                  for name, url in API_ENDPOINTS.items()}
        for future in futures:
            name, data = future.result()
            results[name] = data
            
    return results

def normalize_content_data(raw_data: Dict) -> pd.DataFrame:
    """
    title, description, tags, source_api
    """
    records = []
    
    for api_name, items in raw_data.items():
        if isinstance(items, dict) and "error" in items:
            continue
            
        for item in items:
            # Flexible field mapping (adjust based on your actual API field names)
            title = item.get('title') or item.get('name') or item.get('heading') or 'Untitled'
            desc = item.get('description') or item.get('desc') or item.get('summary') or item.get('body') or ''
            
            # Normalize tags to a list
            tags = item.get('tags') or item.get('tag') or item.get('categories') or item.get('labels') or []
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(',') if t.strip()]
            elif not isinstance(tags, list):
                tags = [str(tags)] if tags else []
            
            # Clean tags: lowercase, strip whitespace
            tags = [str(t).lower().strip() for t in tags if t]
            
            records.append({
                'title': str(title),
                'description': str(desc),
                'tags': tags,  # List of strings
                'source_api': api_name,
                'raw_data': item  # Keep original for reference
            })
    
    return pd.DataFrame(records)

def extract_all_tags(df: pd.DataFrame) -> List[str]:
    """Extract unique tags across all items for the filter dropdown"""
    all_tags = set()
    for tag_list in df['tags']:
        if isinstance(tag_list, list):
            all_tags.update(tag_list)
    return sorted(list(all_tags))

# --- SEARCH LOGIC (Server-Side) ---
def search_content(
    df: pd.DataFrame, 
    text_query: str = None, 
    selected_tags: List[str] = None,
    match_all_tags: bool = True,  
    search_in_desc: bool = True
) -> pd.DataFrame:
    """
    Server-side filtering supporting:
    - Text search in title (and optionally description)
    - Tag filtering with AND/OR logic
    """
    results = df.copy()
    
    # 1. Text search (Title + optional Description)
    if text_query:
        text_query = text_query.lower()
        title_mask = results['title'].str.lower().str.contains(text_query, na=False)
        
        if search_in_desc:
            desc_mask = results['description'].str.lower().str.contains(text_query, na=False)
            text_mask = title_mask | desc_mask
        else:
            text_mask = title_mask
            
        results = results[text_mask]
    
    # 2. Tag filtering
    if selected_tags:
        def has_tags(item_tags):
            if not isinstance(item_tags, list):
                return False
            
            if match_all_tags:  # AND - must have ALL selected tags
                return all(tag in item_tags for tag in selected_tags)
            else:  # OR - must have AT LEAST ONE selected tag
                return any(tag in item_tags for tag in selected_tags)
        
        tag_mask = results['tags'].apply(has_tags)
        results = results[tag_mask]
    
    return results


def display_result_card(row: pd.Series, highlight_query: str = None):
    """Display a single search result as a card with prominent tags"""
    with st.container():
        col1, col2 = st.columns([4, 1])
        
        with col1:
            # Title with optional highlighting
            title = row['title']
            if highlight_query:
                title = title.replace(highlight_query, f"**{highlight_query}**")
            st.markdown(f"### {title}")
            
            # Description (truncated if long)
            desc = row['description']
            if len(desc) > 300:
                desc = desc[:300] + "..."
            if highlight_query:
                # Simple highlight (case sensitive in this basic version)
                desc = desc.replace(highlight_query, f"**{highlight_query}**")
            st.caption(desc)
            
            # Tags display
            st.markdown("**Tags:** " + " ".join([
                render_tag_badge(tag, is_selected=False) 
                for tag in row['tags']
            ]), unsafe_allow_html=True)
        
        with col2:
            st.caption(f"Source: *{row['source_api']}*")
            # Clickable tag filter - add buttons to refine search
            if st.button("🔍 View Details", key=f"btn_{row.name}"):
                with st.expander("Full Details", expanded=True):
                    st.json(row['raw_data'])

# --- MAIN APP ---
st.title("Tag-Based Media Search")
st.markdown("Search by Description")

# Load data
with st.spinner("Loading..."):
    raw_data = load_apis()
    df = normalize_content_data(raw_data)

if df.empty:
    st.error("No data loaded")
    st.stop()

# Get all available tags for the filter
all_tags = extract_all_tags(df)

# --- SEARCH INTERFACE ---
st.sidebar.header("Search Filters")

# Text search
search_text = st.sidebar.text_input(
    "Search titles & descriptions",
    placeholder="Enter keywords..."
)

# Tag filtering
st.sidebar.markdown("---")
st.sidebar.subheader("Filter by Tags")

# Show tag statistics
tag_counts = {}
for tags in df['tags']:
    for tag in tags:
        tag_counts[tag] = tag_counts.get(tag, 0) + 1

# Tag selection mode
tag_mode = st.sidebar.radio(
    "Tag match mode",
    ["Match ANY (OR)", "Match ALL (AND)"],
    help="OR: Item has at least one selected tag. AND: Item has all selected tags."
)

selected_tags = st.sidebar.multiselect(
    "Filter",
    options=all_tags,
    format_func=lambda x: f"{x} ({tag_counts.get(x, 0)})",  # Show count
    help="Start typing to tag search"
)

# Additional options
st.sidebar.markdown("---")
search_in_desc = st.sidebar.checkbox("Search in descriptions", value=True)
st.sidebar.caption(f"Total items loaded: **{len(df)}**")
st.sidebar.caption(f"Unique tags: **{len(all_tags)}**")

# --- EXECUTE SEARCH ---
match_all = tag_mode == "Match ALL (AND)"
results = search_content(
    df, 
    text_query=search_text if search_text else None,
    selected_tags=selected_tags if selected_tags else None,
    match_all_tags=match_all,
    search_in_desc=search_in_desc
)

# --- RESULTS DISPLAY ---
st.divider()

# Summary stats
col1, col2, col3 = st.columns(3)
col1.metric("Results Found", len(results))
col2.metric("APIs Searched", len(API_ENDPOINTS))
if selected_tags:
    col3.metric("Active Tag Filters", len(selected_tags))

# Active filters display
if search_text or selected_tags:
    filter_desc = []
    if search_text:
        filter_desc.append(f"text: '{search_text}'")
    if selected_tags:
        filter_desc.append(f"tags: {', '.join(selected_tags)}")
    st.info(f"Active filters: **{' + '.join(filter_desc)}**")

# Display results
if len(results) == 0:
    st.warning("No results")
    
    # Suggestions: Show related tags or similar items
    if selected_tags:
        st.caption("Try removing some tag filters or switching to 'Match ANY' mode")
else:
    # Results found
    st.success(f"Found {len(results)} items")
    
    # View mode toggle
    view_mode = st.radio("Display mode", ["Cards", "Compact List"], horizontal=True)
    
    if view_mode == "Cards":
        for _, row in results.iterrows():
            display_result_card(row, highlight_query=search_text if search_text else None)
            st.divider()
    else:
        # Compact table view
        display_df = results[['title', 'description', 'tags', 'source_api']].copy()
        display_df['tags'] = display_df['tags'].apply(lambda x: ', '.join(x))
        st.dataframe(display_df, use_container_width=True, height=600)
        
        # Quick tag cloud of results
        if len(results) < 50:  # Only for manageable result sets
            st.caption("Tags in current results:")
            result_tags = set()
            for tags in results['tags']:
                result_tags.update(tags)
            st.markdown(" ".join([render_tag_badge(t) for t in result_tags]), unsafe_allow_html=True)
