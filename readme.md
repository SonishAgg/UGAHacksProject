# Cross-Media Recommender

Cross-Media Recommender is a mixed media recommendation program that utilizes semantic similarity, K-Nearest Neighbors, and Hugging Face to take a user's input of a movie, anime, or manga and recommend the best movie, anime, or manga based on similarity. Rather than relying on brittle keyword matching, the system converts tags and genres into weighted text, encodes them into 384-dimensional vectors using Sentence-BERT (all-MiniLM-L6-v2), and performs cosine similarity searches to find the nearest neighbors across all three media types. This allows the engine to connect concepts like "wormhole" to "space opera" or "coming of age" to "teenage protagonist" without requiring exact term overlap.

## Features

The application offers cross-media recommendations where a single input returns the most similar movies, anime, and manga. It uses semantic embeddings to relate meaning across entirely different datasets and leverages AniList user description ratings to weight tag accuracy. The frontend is built with Streamlit for easy exploration and includes a re-roll system so users can refresh their picks if the initial results don't appeal to them.

## Tech Stack

The frontend is built with Streamlit and Python. The ML model uses Sentence-BERT (all-MiniLM-L6-v2) from Hugging Face along with scikit-learn. Similarity search is handled by K-Nearest Neighbors with cosine distance. Data is sourced from the TMDB API for movies and the AniList GraphQL API for anime and manga. All media items are represented as 384-dimensional semantic vectors.

## Project Structure

The repository is split into two main directories. The `ML/` directory contains the machine learning backend including data collection scripts (`tmdb_client.py`, `collector.py`), model logic (`tag_encoder.py`, `recommender.py`), runner scripts (`collect_movies.py`, `run_recommender.py`), and stored data (`movies.json`, `anime_list.json`, `manga_list.json`, `embeddings.npz`). The `media-recommender/` directory contains `app.py`, which is the Streamlit web interface. The root also includes a `.env` file for API credentials and a `requirements.txt` for dependencies.

## Getting Started

You will need Python 3.10 or higher and a free TMDB API account. Clone the repository, create a virtual environment, and install dependencies with `pip install -r requirements.txt`. Then create a `ML/.env` file containing your TMDB bearer token. Run `python3 scripts/collect_movies.py --large` and `python3 scripts/fetch_anilist.py` from the `ML/` directory to collect data. Finally, run `streamlit run media-recommender/app.py` from the project root and open `http://localhost:8501` in your browser.

## How It Works

Tags and genres from each media item are converted into weighted text where high-confidence AniList tags and genres receive greater emphasis. Sentence-BERT then encodes this text into a 384-dimensional vector. At query time, the input item's vector is compared against all stored vectors using cosine similarity via KNN. The top results are grouped by media type and returned to the user. The system also automatically deduplicates franchises and excludes the input item from results.

## Datasets and Performance

The system indexes approximately 4,500 items total: around 2,500 movies from TMDB, 1,000 anime from AniList, and 1,000 manga from AniList. Initial load takes roughly 15 seconds, the one-time embedding build takes around 30 seconds, and individual queries respond in under 100 milliseconds. A CLI mode is also available by running `python3 scripts/run_recommender.py` from the `ML/` directory.

## Future Work

Planned improvements include music recommendations, user personalization, additional data sources, model fine-tuning, and cloud deployment.

## Acknowledgments

This project was built at UGA Hacks 11. It is powered by TMDB, AniList, Sentence-Transformers, and Streamlit. 










