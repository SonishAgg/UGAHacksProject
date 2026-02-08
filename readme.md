# 🎥 Media Search

A Streamlit web app that lets you search for **movies**, **anime**, and **manga** using a single keyword. Powered by the [TMDB API](https://www.themoviedb.org/documentation/api) and [AniList API](https://anilist.gitbook.io/anilist-apiv2-docs/).

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.30%2B-FF4B4B)
![License](https://img.shields.io/badge/License-MIT-green)

---

## ✨ Features

- 🎬 **Movie Search** — Search movies via TMDB with genre tags and descriptions
- 📺 **Anime Search** — Search anime via AniList with genre tags and descriptions
- 📖 **Manga Search** — Search manga via AniList with genre tags and descriptions
- 🔀 **Toggle Results** — Show/hide movies, anime, or manga with checkboxes
- ⚡ **Cached Requests** — API responses are cached for fast repeat searches
- 🎨 **Clean UI** — Simple, responsive layout built with Streamlit

---

## 📸 Preview

| Search View | Results |
|---|---|
| Enter a keyword and toggle media types | Movies, anime, and manga displayed with tags |

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10 or higher
- A [TMDB API Key](https://www.themoviedb.org/settings/api) (free)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/media-recommender.git
   cd media-recommender
Create a virtual environment:


python3 -m venv .venv
source .venv/bin/activate   # macOS/Linux
.venv\Scripts\activate      # Windows
Install dependencies:


pip install -r requirements.txt
Add your TMDB API key:

Create a file at .streamlit/secrets.toml:


mkdir -p .streamlit
echo 'TMDB_API_KEY = "your_api_key_here"' > .streamlit/secrets.toml
Then update line 13 in app.py:


TMDB_API_KEY = "TMDB_API_KEY"
Run the app:


streamlit run app.py
The app will open at https://ugahacksproject-fsjdj8xjt38azbhbhnjqdi.streamlit.app/#romance

📁 Project Structure

media-recommender/
├── .streamlit/
│   └── secrets.toml       # API keys (not committed)
├── app.py                 # Main Streamlit application
├── requirements.txt       # Python dependencies
├── README.md              # This file
└── .gitignore
📦 Dependencies
Package	Purpose
streamlit	Web app framework
requests	HTTP requests to TMDB and AniList APIs
Create a requirements.txt:


streamlit
requests
🔌 APIs Used
API	Used For	Auth
TMDB API v3	Movie search & genre data	API key (query param)
AniList GraphQL	Anime & manga search	None (public)
🛡️ Security
⚠️ Never commit your API keys to GitHub.

Make sure your .gitignore includes:


.streamlit/secrets.toml
📝 Usage
Type a keyword (e.g., cyberpunk, romance, fantasy)
Check/uncheck Movies, Anime, or Manga
View results with descriptions and genre tags
🤝 Contributing
Fork the repo
Create a feature branch (git checkout -b feature/new-feature)
Commit your changes (git commit -m "Add new feature")
Push to the branch (git push origin feature/new-feature)
Open a Pull Request
📄 License
This project is licensed under the MIT License. See LICENSE for details.

🙏 Acknowledgments
TMDB for the movie database API
AniList for the anime/manga GraphQL API
Streamlit for the web framework
Built with ❤️ at UGA Hacks



---

To create it, run:

```bash
cd /Users/sonish/Desktop/UGAHacks/media-recommender
nano README.md
