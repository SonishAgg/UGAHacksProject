"""
Movie data collector using TMDb API.
Collects, cleans, and builds rich profiles for ML embeddings.
"""

import os
import json
from datetime import datetime
from .tmdb_client import TMDbClient


class MovieCollector:
    def __init__(self, output_dir="data/processed"):
        self.tmdb = TMDbClient()
        self.collected = []
        self.errors = []
        self.seen_ids = set()
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    # =========================================
    # Collect one film
    # =========================================

    def collect_film(self, tmdb_id):
        """Pull full details for one film and build a unified profile."""
        raw = self.tmdb.get_movie(tmdb_id)
        return self._build_profile(raw)

    def _build_profile(self, raw):
        """Transform raw TMDb response into a clean profile."""

        # --- Genres ---
        genres = [g["name"] for g in raw.get("genres", [])]

        # --- Keywords ---
        keywords = [
            k["name"]
            for k in raw.get("keywords", {}).get("keywords", [])
        ]

        # --- Crew ---
        crew = raw.get("credits", {}).get("crew", [])
        directors = [c["name"] for c in crew if c.get("job") == "Director"]
        writers = [c["name"] for c in crew if c.get("department") == "Writing"][:3]
        composers = [
            c["name"] for c in crew
            if c.get("job") in ("Original Music Composer", "Music")
        ]
        cinematographers = [
            c["name"] for c in crew
            if c.get("job") == "Director of Photography"
        ]

        # --- Cast ---
        cast = []
        for actor in raw.get("credits", {}).get("cast", [])[:10]:
            cast.append({
                "name": actor["name"],
                "character": actor.get("character", ""),
            })

        # --- Certification ---
        certification = ""
        for country in raw.get("release_dates", {}).get("results", []):
            if country.get("iso_3166_1") == "US":
                for release in country.get("release_dates", []):
                    cert = release.get("certification", "")
                    if cert:
                        certification = cert
                        break

        # --- Release year ---
        release_date = raw.get("release_date", "")
        year = release_date[:4] if release_date else ""

        profile = {
            # IDs
            "tmdb_id": raw.get("id"),
            "imdb_id": raw.get("imdb_id"),

            # Core
            "title": raw.get("title", ""),
            "original_title": raw.get("original_title", ""),
            "year": year,
            "release_date": release_date,
            "runtime": raw.get("runtime", 0),
            "certification": certification,
            "tagline": raw.get("tagline", ""),

            # Categorization
            "genres": genres,
            "keywords": keywords,

            # People
            "directors": directors,
            "writers": writers,
            "composers": composers,
            "cinematographers": cinematographers,
            "cast": cast,

            # Description
            "overview": raw.get("overview", ""),

            # Ratings
            "rating": round(raw.get("vote_average", 0), 1),
            "vote_count": raw.get("vote_count", 0),
            "popularity": raw.get("popularity", 0),

            # Financial
            "budget": raw.get("budget", 0),
            "revenue": raw.get("revenue", 0),

            # Production
            "countries": [
                c.get("name", "") for c in raw.get("production_countries", [])
            ],
            "languages": [
                l.get("english_name", l.get("name", ""))
                for l in raw.get("spoken_languages", [])
            ],
            "companies": [
                c.get("name", "") for c in raw.get("production_companies", [])
            ],

            # Images
            "poster_path": raw.get("poster_path", ""),
            "backdrop_path": raw.get("backdrop_path", ""),
        }

        # Rich text for embeddings
        profile["embedding_text"] = self._build_embedding_text(profile)

        return profile

    def _build_embedding_text(self, p):
        """
        Combine all meaningful text into one rich string.
        This gets converted into a vector embedding later.
        """
        parts = []

        # Title
        parts.append(f"{p['title']} ({p['year']}).")

        # Tagline
        if p["tagline"]:
            parts.append(p["tagline"])

        # Overview
        if p["overview"]:
            parts.append(p["overview"])

        # Genres
        if p["genres"]:
            parts.append(f"Genres: {', '.join(p['genres'])}.")

        # Keywords
        if p["keywords"]:
            parts.append(f"Keywords: {', '.join(p['keywords'])}.")

        # Director
        if p["directors"]:
            parts.append(f"Directed by {', '.join(p['directors'])}.")

        # Cast with characters
        if p["cast"]:
            cast_parts = []
            for a in p["cast"][:5]:
                if a["character"]:
                    cast_parts.append(f"{a['name']} as {a['character']}")
                else:
                    cast_parts.append(a["name"])
            parts.append(f"Starring {', '.join(cast_parts)}.")

        # Certification
        if p["certification"]:
            parts.append(f"Rated {p['certification']}.")

        # Country
        if p["countries"]:
            parts.append(f"Produced in {', '.join(p['countries'][:2])}.")

        return " ".join(parts)

    # =========================================
    # Batch collection
    # =========================================

    def collect_popular(self, pages=5):
        """Collect popular movies."""
        print(f"\n📥 Collecting popular movies ({pages} pages)...")
        self._collect_from_list("popular", pages)

    def collect_top_rated(self, pages=5):
        """Collect top rated movies."""
        print(f"\n📥 Collecting top rated movies ({pages} pages)...")
        self._collect_from_list("top_rated", pages)

    def collect_by_genre(self, genre_id, genre_name="", pages=3):
        """
        Collect movies filtered by genre.
        
        Genre IDs:
            28=Action, 12=Adventure, 16=Animation, 35=Comedy,
            80=Crime, 99=Documentary, 18=Drama, 14=Fantasy,
            27=Horror, 10402=Music, 9648=Mystery, 10749=Romance,
            878=Sci-Fi, 53=Thriller, 10752=War, 37=Western
        """
        label = genre_name or f"genre:{genre_id}"
        print(f"\n📥 Collecting {label} movies ({pages} pages)...")

        for page in range(1, pages + 1):
            response = self.tmdb.discover(
                with_genres=str(genre_id),
                sort_by="vote_count.desc",
                vote_count_gte=100,
                page=page,
            )
            self._process_page(response, page, pages)

    def collect_by_decade(self, decade, pages=3):
        """Collect top movies from a decade (e.g. 1990, 2000, 2010)."""
        print(f"\n📥 Collecting {decade}s movies ({pages} pages)...")

        for page in range(1, pages + 1):
            response = self.tmdb.discover(
                primary_release_date_gte=f"{decade}-01-01",
                primary_release_date_lte=f"{decade + 9}-12-31",
                sort_by="vote_count.desc",
                vote_count_gte=200,
                page=page,
            )
            self._process_page(response, page, pages)

    def _collect_from_list(self, list_type, pages):
        """Collect from a TMDb list endpoint."""
        for page in range(1, pages + 1):
            if list_type == "popular":
                response = self.tmdb.get_popular(page)
            else:
                response = self.tmdb.get_top_rated(page)
            self._process_page(response, page, pages)

    def _process_page(self, response, page, total_pages):
        """Process one page of results."""
        results = response.get("results", [])
        print(f"  Page {page}/{total_pages} ({len(results)} movies)")

        for movie in results:
            tmdb_id = movie["id"]
            title = movie.get("title", "?")

            # Skip duplicates
            if tmdb_id in self.seen_ids:
                continue
            self.seen_ids.add(tmdb_id)

            try:
                profile = self.collect_film(tmdb_id)
                self.collected.append(profile)
                print(f"    ✓ {profile['title']} ({profile['year']}) "
                      f"★{profile['rating']} — "
                      f"{len(profile['keywords'])} keywords, "
                      f"{len(profile['cast'])} cast")

            except Exception as e:
                self.errors.append({
                    "tmdb_id": tmdb_id,
                    "title": title,
                    "error": str(e),
                })
                print(f"    ✗ {title}: {e}")

    # =========================================
    # Save and load
    # =========================================

    def save(self, filename="movies.json"):
        """Save collected movies to JSON."""
        filepath = os.path.join(self.output_dir, filename)

        output = {
            "metadata": {
                "total_movies": len(self.collected),
                "collected_at": datetime.utcnow().isoformat(),
                "source": "tmdb",
                "errors": len(self.errors),
            },
            "movies": self.collected,
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        print(f"\n{'='*50}")
        print(f"✓ Saved {len(self.collected)} movies to {filepath}")
        print(f"  Errors: {len(self.errors)}")
        if self.errors:
            print(f"  Failed: {[e['title'] for e in self.errors[:5]]}")
        print(f"{'='*50}")

    def load(self, filename="movies.json"):
        """Load previously collected movies."""
        filepath = os.path.join(self.output_dir, filename)

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.collected = data["movies"]
        self.seen_ids = {m["tmdb_id"] for m in self.collected}

        print(f"Loaded {len(self.collected)} movies from {filepath}")
        return self.collected

    def stats(self):
        """Print collection statistics."""
        if not self.collected:
            print("No movies collected yet.")
            return

        movies = self.collected
        rated = [m for m in movies if m["rating"] > 0]
        has_keywords = [m for m in movies if m["keywords"]]
        has_overview = [m for m in movies if m["overview"]]

        print(f"\n📊 Collection Stats")
        print(f"  Total movies:      {len(movies)}")
        print(f"  With ratings:      {len(rated)}")
        print(f"  With keywords:     {len(has_keywords)}")
        print(f"  With overviews:    {len(has_overview)}")

        if rated:
            ratings = [m["rating"] for m in rated]
            print(f"  Avg rating:        {sum(ratings)/len(ratings):.1f}")
            print(f"  Rating range:      {min(ratings)} — {max(ratings)}")

        genres_count = {}
        for m in movies:
            for g in m["genres"]:
                genres_count[g] = genres_count.get(g, 0) + 1
        top_genres = sorted(genres_count.items(), key=lambda x: -x[1])[:10]
        print(f"  Top genres:")
        for genre, count in top_genres:
            print(f"    {genre}: {count}")

        decades = {}
        for m in movies:
            if m["year"]:
                decade = m["year"][:3] + "0s"
                decades[decade] = decades.get(decade, 0) + 1
        for decade in sorted(decades.keys()):
            print(f"    {decade}: {decades[decade]}")