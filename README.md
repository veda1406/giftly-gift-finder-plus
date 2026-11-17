# Giftly – Gift Finder Plus

Giftly is a single-page gift discovery demo built with Flask, SQLite, vanilla JavaScript, HTML, and CSS. The app keeps the existing four-step recipient → occasion → interests → budget flow and adds personalized recommendations, a saved wishlist, comparison, recent searches, and a rule-based gift assistant.

## Current product limits

- The built-in catalog contains illustrative examples and demo prices in INR. Giftly now generates Amazon.in search links and Myntra search links for fashion ideas, but it does not retrieve or verify individual listings, prices, sizes, stock, or delivery. Shoppers can paste a direct product URL into the wishlist after opening a retailer result.
- The assistant uses deterministic keyword rules; it is not generative AI.
- Wishlist and search history are scoped to a browser-generated local profile ID. This is convenient browser isolation, **not authentication or a security boundary**. Clearing browser storage creates a new profile; this demo does not offer account recovery or cross-device sync. It retains up to 30 recent briefs per profile and provides a clear-history action.
- Comparison and theme choice are stored in browser local storage.
- Do not expose the built-in Flask server to the public internet. Use a production WSGI server and add real identity, privacy, and abuse controls before launch.

## Requirements

- Python 3.10+
- pip

## Run locally

1. Extract this folder.
2. Open a terminal in this folder.
3. Create and activate a virtual environment (recommended):
   - Windows: `py -m venv .venv` then `.venv\\Scripts\\activate`
   - macOS/Linux: `python3 -m venv .venv` then `source .venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Start the backend: `python server.py`
6. Open **http://127.0.0.1:5000**.

Open the app through Flask, not by double-clicking `index.html`. Flask serves the page, `/static/` assets, and same-origin `/api/` routes. `GIFTFINDER_DB` can point to a different SQLite database file outside the public `static/` directory; `HOST` and `PORT` configure the local server. `GIFTFINDER_DEBUG=1` enables Flask debug mode for local development only.

On first run, SQLite creates `giftly.db` next to `server.py`. Existing databases are migrated to add browser profile ownership; existing records remain under a legacy owner and are not visible to new browser profiles. New catalog entries are inserted by stable unique name without overwriting existing catalog edits.

## Main API routes

- `GET /api/health` — backend/database health and live catalog count.
- `GET /api/gifts` — full catalog.
- `POST /api/recommend` — validated brief, ranked recommendations, and search history.
- `GET /api/wishlist` — this browser profile’s saved gifts.
- `POST /api/wishlist` — save a gift (`{"gift_id": 1}`).
- `DELETE /api/wishlist/<gift_id>` — remove a saved gift.
- `POST /api/wishlist/links` — save a user-provided HTTPS product URL from Amazon.in, Myntra, Flipkart, or AJIO, with optional name and price.
- `DELETE /api/wishlist/links/<link_id>` — remove a saved retailer URL.
- `GET /api/history` — latest 30 searches for this browser profile.
- `DELETE /api/history` — clear this browser profile’s searches.
- `POST /api/assistant` — rule-based ideas from a message.
- `GET /api/stats` — catalog count and this browser profile’s wishlist/search counts.

The app sends an `X-Giftly-Client` UUID header to owner-scoped routes. A caller can forge this header, so it must not be treated as user authentication. The wishlist stores the URL and optional price/name as entered; it does not scrape or refresh saved retailer pages.

## Recommendation behavior

Recommendations must be in the selected price band (`Under ₹500`, `₹500` to under `₹1,000`, `₹1,000` to under `₹2,000`, `₹2,000` to under `₹5,000`, or `₹5,000+`), then are ordered by interest matches, occasion fit, a small number of explicit recipient heuristics, price, and stable catalog ID. Cards show matching reasons. The former percentage-style “match score” was removed because the rules do not support a calibrated confidence percentage. The separate retailer links open current merchant search pages from a fixed list of idea keywords; Giftly does not promise those search pages enforce the brief’s budget.

## Architecture

- `server.py` — Flask routes, validation, SQLite schema/upgrade, seeding, and rule-based recommendation logic.
- `index.html` — page structure and app views.
- `static/app.js` — frontend state, API client, rendering, navigation, and interactions.
- `static/style.css` — visual system, responsive layout, focus styles, and reduced-motion behavior.
- `requirements.txt` — runtime Python dependencies.


