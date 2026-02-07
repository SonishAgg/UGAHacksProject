import streamlit as st
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import pandas as pd

# ============================================
# 1. LOAD THE AI MODEL (runs once, then cached)
# ============================================
@st.cache_resource
def load_model():
    return SentenceTransformer('all-MiniLM-L6-v2')

model = load_model()

# ============================================
# 2. FAKE DATA (we'll use real APIs later)
# ============================================
media_items = [
    {"title": "Blade Runner 2049",   "type": "movie", "description": "melancholy atmospheric sci-fi neon dystopia lonely"},
    {"title": "Interstellar",        "type": "movie", "description": "epic emotional space exploration hope father daughter"},
    {"title": "Midsommar",           "type": "movie", "description": "bright unsettling folk horror daylight cult creepy"},
    {"title": "La La Land",          "type": "movie", "description": "romantic jazz dreamy bittersweet los angeles musical"},
    {"title": "The Social Network",  "type": "movie", "description": "tense ambitious tech betrayal fast-paced dark"},
    {"title": "Runaway - Kanye West","type": "music", "description": "melancholy piano epic emotional cinematic grandiose"},
    {"title": "Breathe - Pink Floyd","type": "music", "description": "atmospheric slow ambient existential spacey psychedelic"},
    {"title": "Redbone - Childish Gambino", "type": "music", "description": "groovy retro funky dreamy smooth psychedelic"},
    {"title": "Exit Music - Radiohead",     "type": "music", "description": "sad dramatic building emotional orchestral dark"},
    {"title": "Midnight City - M83",        "type": "music", "description": "neon synth nostalgic euphoric driving nighttime city"},
]

# ============================================
# 3. GENERATE EMBEDDINGS (turn words → numbers)
# ============================================
@st.cache_data
def get_embeddings():
    descriptions = [item["description"] for item in media_items]
    embeddings = model.encode(descriptions)
    return embeddings

embeddings = get_embeddings()

# ============================================
# 4. BUILD THE STREAMLIT UI
# ============================================
st.title("🎬🎵 Cross-Media Recommender")
st.write("Pick a movie, anime, manga, or song — get recommendations across ALL media types!")

# Dropdown to pick a media item
titles = [item["title"] for item in media_items]
selected = st.selectbox("Choose one:", titles)

# Find which item they picked
selected_index = titles.index(selected)
selected_item = media_items[selected_index]

st.markdown(f"**You picked:** {selected_item['title']}  (`{selected_item['type']}`)")
st.markdown(f"**Vibes:** _{selected_item['description']}_")

st.divider()

# ============================================
# 5. FIND SIMILAR ITEMS (the magic part!)
# ============================================
if st.button("🔍 Get Recommendations"):

    # Calculate how similar EVERY item is to the one you picked
    selected_embedding = embeddings[selected_index].reshape(1, -1)
    similarities = cosine_similarity(selected_embedding, embeddings)[0]

    # Build a results table
    results = []
    for i, item in enumerate(media_items):
        if i == selected_index:
            continue  # skip the one you picked 
        results.append({
            "Title": item["title"],
            "Type": "🎬 Movie" if item["type"] == "movie" else "🎵 Music",
            "Match Score": f"{similarities[i]:.0%}",
            "score_raw": similarities[i],
        })

    # Sort by highest match
    results = sorted(results, key=lambda x: x["score_raw"], reverse=True)

    # Display results
    st.subheader("Your Recommendations:")
    for rank, r in enumerate(results, 1):
        st.write(f"**{rank}. {r['Type']} {r['Title']}** — {r['Match Score']} match")

    st.snow()
    
