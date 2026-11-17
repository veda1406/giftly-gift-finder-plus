# Giftly – Gift Finder Plus

Giftly helps people find thoughtful gift ideas. It combines a step-by-step gift finder, a small SQLite catalog, live retailer search links, a browser-local wishlist and search history, comparison, and a rule-based gift assistant.

The project uses **HTML, CSS, vanilla JavaScript, Flask, and SQLite**. There is no frontend build step.

## Features

- **Gift finder:** choose a recipient relationship and age range, an occasion, interests, and a budget band. Giftly ranks catalog ideas and explains why they matched.
- **Retailer searches:** recommendations include live Amazon.in search pages. Fashion briefs also include Myntra searches. Search links are generated from the selected interests and budget.
- **Wishlist:** save built-in Giftly ideas or add a direct HTTPS product URL from Amazon.in, Myntra, Flipkart, or AJIO. Optional product name and price are stored as entered.
- **Search history:** view and restore recent gift briefs; clear the history when you want. Up to 30 briefs are retained per browser profile.
- **Comparison:** compare up to three catalog gifts at a time.
- **Gift assistant:** enter a short natural-language request to get keyword-matched gift ideas and retailer searches.
- **Responsive interface:** navigation and the gift finder adapt to smaller screens. The design uses Bricolage Grotesque and DM Sans when Google Fonts are available, with system fallbacks.

## Important product limits

- The included catalog contains **illustrative gift examples and prices**. Retailer links open live search pages; Giftly does not retrieve or verify individual products, prices, stock, sizes, or delivery.
- The assistant is rule-based keyword matching. It is **not generative AI**.
- Saved retailer links are stored as entered. Giftly does not scrape or refresh retailer pages.
- Wishlist and history are scoped by a browser-generated profile ID sent in the `X-Giftly-Client` header. This is convenient browser separation, **not authentication**; the value can be forged. There are no user accounts or cross-device sync.
- The checked-in `giftly.db` contains the starter catalog. Running the app writes wishlist items, saved links, and search history to the local SQLite database. Do not commit a database containing real or personal user data. For local use, point `GIFTFINDER_DB` outside the repository.
- This project is a local demo. Do not expose Flask’s development server to the public internet.

## Requirements

- Python 3.10 or newer
- pip

## Run locally

Clone the repository and enter the project directory:

```powershell
git clone https://github.com/veda1406/giftly-gift-finder-plus.git
cd giftly-gift-finder-plus
```

Create a virtual environment, install the dependencies, and start Flask:

### Windows PowerShell

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe server.py
```

### macOS or Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python server.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000). Use the Flask URL rather than opening `index.html` directly; the page, static assets, and API are served from the same origin.

On the first run without an existing database, Giftly creates the database and seeds the starter catalog automatically.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `HOST` | `127.0.0.1` | Address for the local Flask development server. |
| `PORT` | `5000` | Port for the local Flask development server. |
| `GIFTFINDER_DB` | `giftly.db` next to `server.py` | SQLite database file path. Keep it outside `static/`; for local use, prefer a path outside the repository. |
| `GIFTFINDER_DEBUG` | `0` | Set to `1` for local debugging only. Never enable debug mode on a public server. |

Example for PowerShell:

```powershell
$env:GIFTFINDER_DB = "$env:LOCALAPPDATA\Giftly\giftly.db"
python server.py
```

Giftly creates the parent directory for the configured database path.

## How it works

- `index.html` contains the page and all app views.
- `static/app.js` manages browser state, navigation, rendering, local preferences, and requests to Flask.
- `static/style.css` defines the visual design, responsive behavior, and accessibility refinements.
- `static/hero-collage.png` is the decorative homepage collage.
- `server.py` serves the page, validates requests, ranks gift records, builds retailer searches, and exposes the JSON API.
- `giftly.db` stores the catalog and local wishlist, saved retailer links, and search history.
- `requirements.txt` lists the Python runtime dependency.
- `PROJECT_AUDIT.md` records the original project audit and recommended roadmap.

The default database has four tables: `gifts`, `wishlists`, `saved_links`, and `searches`. The browser stores comparison selections and the theme preference in local storage.

## Recommendation behavior

Recommendations must fit the selected budget band, then sort by interest matches, occasion fit, a small set of explicit recipient heuristics, price, and catalog ID. Cards show match reasons. These rules are transparent but simple; they do not learn from user behavior or represent an AI model’s confidence.

Retailer search links use a short list of category-specific queries. Giftly labels them as search pages rather than verified product picks. Always check the retailer page for the actual listing, price, variants, availability, and delivery details.

## API overview

All API routes are served under `/api`. Requests that read or change browser-owned wishlist/history data need a valid UUID in the `X-Giftly-Client` request header; the frontend creates and stores this ID automatically.

| Method | Route | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Check Flask/SQLite health and catalog count. |
| `GET` | `/api/gifts` | Return the gift catalog. |
| `POST` | `/api/recommend` | Validate a gift brief, store it in history, and return ranked ideas and retailer searches. |
| `GET` | `/api/wishlist` | Return saved catalog gifts and retailer links for the browser profile. |
| `POST` | `/api/wishlist` | Save a catalog gift with `{"gift_id": 1}`. |
| `DELETE` | `/api/wishlist/<gift_id>` | Remove a saved catalog gift. |
| `POST` | `/api/wishlist/links` | Save a supported HTTPS product URL with optional name and whole-number price. |
| `DELETE` | `/api/wishlist/links/<link_id>` | Remove a saved retailer URL. |
| `GET` | `/api/history` | Return the latest 30 saved gift briefs. |
| `DELETE` | `/api/history` | Clear search history for the browser profile. |
| `POST` | `/api/assistant` | Return rule-based gift ideas and retailer searches for a message up to 500 characters. |
| `GET` | `/api/stats` | Return catalog, wishlist, and search counts for the browser profile. |

A recommendation request body looks like this:

```json
{
  "relationship": "Friend",
  "age": "18–24",
  "recipientName": "Sam",
  "occasion": "Birthday",
  "interests": ["Fashion", "Music"],
  "budget": "2000-5000"
}
```

Valid budget values are `0-500`, `500-1000`, `1000-2000`, `2000-5000`, and `5000+`.

## Privacy and deployment notes

- Search briefs, wishlists, and saved retailer URLs can be personal. Keep the SQLite file private and out of public commits once it contains real user activity.
- The browser profile ID is not a login or security boundary. Add real authentication and authorization before serving multiple users.
- Use a production WSGI server, HTTPS, proper secret/configuration management, request limits, backups, and monitoring before deployment. The built-in Flask server is for local development only.
- Retailer links are outbound searches or user-supplied URLs. Giftly does not currently use affiliate tracking or provide price/stock guarantees.

## License

No license file is currently included. Ask the project owner before reusing or redistributing the code.
