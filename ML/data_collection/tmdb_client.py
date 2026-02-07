"""
TMDb API client.
Handles authentication, rate limiting, and all movie endpoints.
"""

import os
import time
from pathlib import Path
import requests
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path)


class TMDbClient:
    """
    The Movie Database API client.
    Rate limit: 40 requests per 10 seconds.
    """

    BASE_URL = "https://api.themoviedb.org/3"

    def __init__(self):
        self.access_token = os.getenv("TMDB_ACCESS_TOKEN")
        if not self.access_token:
            raise ValueError(
                "TMDB_ACCESS_TOKEN not found in .env file.\n"
                "Get one at https://www.themoviedb.org/settings/api"
            )
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
        }
        self.request_count = 0
        self.window_start = time.time()

    def _rate_limit(self):
        """Stay under 40 requests per 10 seconds."""
        self.request_count += 1
        if self.request_count >= 35:
            elapsed = time.time() - self.window_start
            if elapsed < 10:
                sleep_time = 10 - elapsed + 0.5
                time.sleep(sleep_time)
            self.request_count = 0
            self.window_start = time.time()

    def get(self, endpoint, params=None):
        """Make a GET request with rate limiting and retry."""
        self._rate_limit()

        response = requests.get(
            f"{self.BASE_URL}{endpoint}",
            params=params or {},
            headers=self.headers,
            timeout=10,
        )

        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 10))
            print(f"  Rate limited. Waiting {retry_after}s...")
            time.sleep(retry_after)
            return self.get(endpoint, params)

        response.raise_for_status()
        return response.json()

    def get_movie(self, movie_id):
        """Get full movie details with keywords, credits, and release dates."""
        return self.get(f"/movie/{movie_id}", {
            "language": "en-US",
            "append_to_response": "keywords,credits,release_dates",
        })

    def get_popular(self, page=1):
        return self.get("/movie/popular", {"language": "en-US", "page": page})

    def get_top_rated(self, page=1):
        return self.get("/movie/top_rated", {"language": "en-US", "page": page})

    def discover(self, **filters):
        params = {"language": "en-US", "include_adult": False, **filters}
        return self.get("/discover/movie", params)