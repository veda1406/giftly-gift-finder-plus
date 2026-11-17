# Giftly – Gift Finder Plus: Project Audit

**Audit scope:** the supplied `Giftly_Gift_Finder_Plus.zip` source archive. This is a read-only code audit; no application code was changed and no runtime behavior was exercised.

## Executive summary

Giftly is a single-page, same-origin Flask application with a vanilla JavaScript frontend and a SQLite-backed demo catalog. Its core path is present: a four-step brief, a rule-based recommendation endpoint, cards, wishlist, comparison, search history, and a keyword-based assistant. It is a coherent classroom/demo foundation, but it is not yet a reliable shopping product. The catalog is illustrative rather than actionable; ranking has coarse heuristics and misleading percentages; user data is shared across everyone who reaches one database; and the Flask development server, broad CORS, static-file configuration, validation, error reporting, accessibility, and operational controls need work before deployment.

The archive contains `index.html`, `style.css`, `app.js`, `server.py`, `requirements.txt`, and `README.md`, plus a Python bytecode cache. It contains no database file, migrations, tests, deployment configuration, or product/retailer integration. `server.py` creates and seeds `giftly.db` on import/first run.

## Architecture and frontend-to-Flask communication

- **Frontend:** `index.html` defines all views in one document; `style.css` contains the complete visual system and responsive rules; `app.js` owns application state, event handlers, fetch calls, rendering, and navigation. There is no frontend framework or build step.
- **Backend:** `server.py` serves `/` from the same directory as static assets and exposes Flask JSON routes under `/api`. The browser helper `api()` in `app.js:15` calls relative URLs (`const API = '/api'` at line 1), so normal use is same-origin through Flask as documented in `README.md`.
- **Persistence:** `server.py:40-55` opens SQLite and initializes three tables. The default database path is adjacent to `server.py`, but `GIFTFINDER_DB` can override it.
- **Startup:** module import calls `init_db()` (`server.py:185`), then direct execution starts Flask on loopback and enables debug (`server.py:186-189`).

**Issue — `server.py`, `home()` and `app = Flask(...)` (lines 9, 70-72):** static serving points at the entire source directory with an empty URL prefix. This makes every file in that directory a candidate static asset, including a generated `giftly.db`, source files, and bytecode files, depending on Flask's static path rules. **Why it matters:** local database contents may be retrievable over HTTP and source/internal files are exposed. **Recommendation:** serve frontend assets from a dedicated public/static directory and explicitly exclude database, configuration, and source artifacts; put persistent data outside the web root.

**Issue — `app.js`, `api()` (line 15):** there is no request timeout, cancellation, retry policy, or shared user-facing error state. Several callers catch and suppress errors. **Why it matters:** slow/offline requests can look like a dead UI or stale data. **Recommendation:** add bounded timeouts, consistent error rendering, and loading/disabled states for every asynchronous action.

## Existing database, catalog, and API

### Schema and seed data

`server.py:12-38` defines 24 demo gift records (name, integer price in INR, emoji, category list, occasion list, and a short rationale). `init_db()` at lines 46-55 creates:

- `gifts(id, name UNIQUE, price, emoji, categories, occasions, why)`; category and occasion arrays are JSON text.
- `wishlists(id, gift_id UNIQUE REFERENCES gifts ON DELETE CASCADE, created_at)`; one global wishlist with no user/owner key.
- `searches(id, brief, request_json, created_at)`; full brief and submitted request as JSON, with no retention or owner key.

There are no migrations, explicit indexes beyond primary/unique constraints, check constraints, timestamps on catalog records, stock/URL/image/source fields, or database lifecycle tooling. Seed insertion occurs only when the table is empty; changes to `SEED` do not update an already-created catalog.

### Routes

- `GET /api/health`: confirms a SQLite connection and reports `catalog_count=len(SEED)`, not the live catalog count (`server.py:74-77`).
- `GET /api/gifts`: returns every catalog entry (`server.py:79-82`).
- `POST /api/recommend`: validates a few required fields and an interests list, scores catalog rows, records a search, and returns at most nine entries (`server.py:84-112`).
- `GET/POST /api/wishlist`, `DELETE /api/wishlist/<gift_id>`: list, insert-if-missing, and remove globally shared saved gifts (`server.py:113-135`).
- `GET /api/history`: returns the latest 30 search records (`server.py:137-140`); the database itself is not capped.
- `POST /api/assistant`: keyword parses a message, filters/scores the catalog, and returns prose plus up to three ideas (`server.py:142-171`).
- `GET /api/stats`: returns live catalog, wishlist, and total search counts (`server.py:173-179`).

**Issue — `server.py`, `health()` (line 76):** `catalog_count` reports seed-list length even if catalog data has been edited or expanded. **Why it matters:** health metrics can disagree with the catalog endpoint. **Recommendation:** query the database count and distinguish seed/version metadata from live counts.

**Issue — `server.py`, `init_db()` (lines 46-55):** schema creation is embedded in startup and there is no migration path or seed update mechanism. **Why it matters:** safe changes to tables/catalog become manual and existing databases can silently retain stale demo content. **Recommendation:** add versioned migrations and explicit catalog import/update tooling with stable product identifiers.

**Issue — `server.py`, wishlist/history routes (lines 113-140):** data is global, history has no delete/clear endpoint, and only the API response—not storage—is limited to 30. **Why it matters:** multiple visitors share saved items and briefs; old personal data accumulates indefinitely. **Recommendation:** establish ownership (accounts or anonymous per-browser identifiers), add clear/delete and retention controls, and index history by owner and creation time.

**Issue — `server.py`, `connect()` (lines 40-44):** connections use SQLite defaults and the context manager commits/rolls back but does not itself close a connection. There is no busy timeout, WAL configuration, or explicit close lifecycle. **Why it matters:** concurrency and resource behavior are not deliberately managed. **Recommendation:** use a connection helper with guaranteed close, configure timeouts, and move to a managed database when traffic or multi-user writes warrant it.

## Recommendation engine and scoring

`recommend()` in `server.py:84-112` applies a maximum price based on the selected budget, counts exact interest/category matches at +5 each, adds +4 for an occasion match, +2 for Partner+Anniversary matching gifts, +2 for Classmate gifts priced at or below ₹1,000, and +1 for Under 18 gifts below ₹1,000. It removes items above the selected ceiling, sorts by descending score then ascending price, assigns ranks to the first nine, and returns them. Age otherwise has no effect. Relationship affects only two hard-coded cases. `match_percent` is calculated as `clamp(65 + score*3, 62, 99)`, a presentation number rather than a calibrated probability or measured match quality.

**Issue — `server.py`, `BUDGETS` and `recommend()` (lines 38, 91-92):** range keys are treated only as upper limits. For example, the ₹500–₹1,000 choice also includes items under ₹500, while ₹1,000–₹2,000 includes all cheaper products. **Why it matters:** the selected option’s displayed price band does not describe the actual result constraint. **Recommendation:** model each selection as explicit minimum/maximum values, or rename UI selections to “up to” ceilings; allow a custom amount.

**Issue — `server.py`, `recommend()` (lines 96-105):** scoring rules are sparse, exact-match only, and do not explain their contribution; relationship/age effects are arbitrary and narrow. All interests are equally weighted, no preference can be excluded, and there is no diversity control. **Why it matters:** rankings feel generic and the same popular item can dominate. **Recommendation:** define a transparent, tested scoring model with normalized features, relevance explanations, configurable weights, tie-breaking/diversity, and feedback signals.

**Issue — `server.py`, `recommend()` (lines 100-101):** `match_percent` is an invented score transform, capped at 99, even for weak/no matches. **Why it matters:** it presents unsupported precision and can mislead users into reading it as confidence. **Recommendation:** remove the percentage or label it as a transparent relative score with a clear methodology; calibrate only if outcome data supports a probability.

**Issue — `server.py`, `recommend()` and `app.js`, `filteredGifts()` (server lines 106-110; client line 19):** only the top nine are returned, with no pagination or total; the client’s “Best match” resorts by raw score and does not use server `rank` as a tie-breaker. **Why it matters:** users cannot browse a real catalog, and ranking can shift on ties. **Recommendation:** add pagination/filtering on the server and make ranking order deterministic and consistent end to end.

**Issue — `server.py`, `request_brief()` and `recommend()` (lines 66-68, 108-111):** `recipientName` is accepted without type, length, or content limits and is retained in search history. The API accepts arbitrary relationship, age, occasion, and interest values except for budget. **Why it matters:** malformed input, misleading scores, oversized records, and unnecessary personal-data retention. **Recommendation:** validate all values against allowlists, cap/normalize text, and minimize or anonymize stored personal details.

## Wishlist, comparison, and search history

- **Wishlist:** persisted in SQLite and reloaded at startup via `refreshData()` in `app.js:35-36`; cards toggle add/remove through the delegated click handler at line 22. It is deduplicated by `gift_id` and has an empty state.
- **Comparison:** supports a maximum of three gifts and a side-by-side table via `state.compare` and `renderCompare()` in `app.js:2,25`. It is memory-only and disappears on reload; it has no server persistence.
- **Search history:** each successful recommendation request is stored server-side. `refreshData()` maps API history and `renderHistory()` displays/replays it (`app.js:27-28,35`). Replaying restores form state but does not automatically show the prior result set.

**Issue — `app.js`, `state` and `renderCompare()` (lines 2, 25):** comparison selection is browser-memory only. **Why it matters:** users lose the comparison when navigating away via refresh or opening another device. **Recommendation:** persist per user/browser and provide an explicit remove/clear affordance and durable product references.

**Issue — `app.js`, `findBtn` handler and `refreshData()` (lines 14, 35):** the client first inserts a locally formatted optimistic history row, then refreshes from the server; if the API history is empty it leaves the optimistic row, and its date format differs from persisted ISO timestamps. **Why it matters:** history can vary between local and backend state or display inconsistent dates. **Recommendation:** use the response as the single source of truth, format timestamps consistently, and render explicit error/loading states.

**Issue — `app.js`, `renderHistory()` and replay handler (lines 27-28):** history is limited to a list of the API's latest 30 entries but has no delete/clear controls, and replay rebuilds the brief only. **Why it matters:** no privacy control and no direct return to a previous result list. **Recommendation:** offer clear/delete, retention controls, and a deliberate “run this brief again” or saved-results behavior.

## Gift Assistant

`assistant()` in `server.py:142-171` is a deterministic keyword parser, not generative AI. It extracts interests using substring matches from a fixed dictionary; recognizes a limited “under/below/less than/within” number pattern; detects the first matching occasion from a short fixed list; ranks by category and occasion; and creates a templated response. The browser’s `sendChat()` in `app.js:32-34` renders user/bot bubbles with `textContent`, shows up to three clickable recommendations, and offers preset prompts. The UI correctly discloses this limitation in `index.html:48`.

**Issue — `server.py`, `assistant()` (lines 143-168):** parsing is English-only, case-insensitive substring matching with a small vocabulary; `words` is computed but unused. Budget phrases such as “around ₹1,000”, “between ₹500 and ₹1,000”, or “my budget is 1000” are not handled, while incidental number text can be mistaken for a budget. **Why it matters:** many natural requests return irrelevant/default results. **Recommendation:** improve structured extraction with clear supported examples, validate and show extracted constraints for confirmation, and provide graceful fallback questions.

**Issue — `server.py`, `assistant()` (lines 154-163):** assistant scoring ignores relationship and age, scores occasion only +3, returns zero-score products, and does not record assistant searches. **Why it matters:** assistant and wizard behave inconsistently and assistant interactions cannot be revisited. **Recommendation:** share validated profile/scoring services across both endpoints and make tracking opt-in and consistent.

**Issue — `app.js`, `sendChat()` (lines 32-34):** there is no send-in-progress state or message limit; a user can submit multiple overlapping requests. The chat transcript is not persisted, and click-through temporarily splices assistant results into current results without representing the original search brief. **Why it matters:** ordering and result context can be confusing. **Recommendation:** disable/queue submissions, cap message length, preserve conversation/search context if desired, and make recommendation navigation state explicit.

## Frontend interactions, validation, navigation, and accessibility

The wizard in `index.html:32-40` and `app.js:9-13` has four steps, back/next controls, a live brief, required-field checks, interest toggles, and a surprise sample. The main navigation switches among five in-document views (`app.js:23`). Results offer category filtering, price sorting, wishlist, comparison, and a short “Why this gift?” toast. The theme switch toggles a class but does not save the choice. The profile modal exposes a backend health check rather than account/profile management.

**Issue — `index.html`, choice groups (lines 35-38) and `app.js`, selection handler (lines 10-12):** relationship, occasion, interests, and budget choices are styled buttons without radio/checkbox semantics, `aria-pressed`, fieldset/legend grouping, or accessible selected-state announcements. **Why it matters:** screen-reader and keyboard users may not understand or operate selections reliably. **Recommendation:** use native radio/checkbox controls or implement complete ARIA keyboard/state behavior and group labels.

**Issue — `index.html`, chat and name controls (lines 35, 48):** text inputs lack programmatic labels (placeholder-only chat; recipient name has an adjacent visual label but no `for`/id association). **Why it matters:** placeholders are not reliable labels. **Recommendation:** add explicit labels and accessible descriptions.

**Issue — `index.html`, modal (line 53):** modal lacks dialog semantics, labelled relationship, focus management/trap, Escape handling, and focus return. **Why it matters:** keyboard and assistive-technology users can lose context. **Recommendation:** implement an accessible dialog pattern or native `<dialog>`.

**Issue — `index.html`, results/chat updates and `app.js`, `renderResults()`/`sendChat()` (index lines 42, 48; JS lines 20, 32-34):** dynamic result counts and chat updates have no live-region announcements; after navigation, focus is not moved to the new view heading. **Why it matters:** state changes are not clearly conveyed to non-visual users. **Recommendation:** use suitable live regions and predictable focus management.

**Issue — `style.css` (single-line stylesheet; responsive rules near the end):** responsive breakpoints exist at 1100px, 760px, and 420px, reduced-motion support is present, and visible focus rings are defined. However, much of the typography is 8–11px with pale text, and the low-contrast palette is used for labels, controls, and helper copy. Mobile hides the sidebar and provides no replacement navigation menu; theme colors are only partly overridden. **Why it matters:** readability, touch use, contrast, and navigation may fail in real conditions. **Recommendation:** establish accessible type and contrast tokens, test real viewport widths/zoom, add mobile navigation, and complete the theme token system.

**Issue — `app.js`, `switchView()` and `editBrief` handler (lines 21, 23):** client-side view changes do not update the URL/history or support browser back/deep links. The “Edit my brief” click scrolls the view rather than the wizard itself. **Why it matters:** navigation is harder to share, restore, and use with browser controls; editing can land at the wrong place. **Recommendation:** use hash/history state and scroll/focus to the actual form.

**Issue — `index.html`, navigation and decorative graphics (lines 13-30):** navigation is an `<aside>` rather than a labelled `<nav>`; decorative emoji/characters have no consistent hiding strategy, and icon-only controls rely on `title`. **Why it matters:** landmarks and control names are inconsistent. **Recommendation:** add semantic navigation, accessible labels, and hide decorative elements from assistive technology.

## Error handling, validation, and security

**Issue — `server.py`, `CORS(app)` (line 10):** CORS is enabled globally with defaults although the documented frontend and API are same-origin. **Why it matters:** unnecessary cross-origin access expands the attack surface and may expose future user-specific endpoints. **Recommendation:** remove CORS for same-origin deployment or restrict it to known origins and methods.

**Issue — `server.py`, startup block (lines 186-189):** `debug=True` is unconditional when run directly; host is fixed to `127.0.0.1`. **Why it matters:** the debug server is not a production server and debug mode can expose sensitive diagnostics if deployment configuration changes. Fixed loopback also prevents normal container hosting. **Recommendation:** use a production WSGI server, make debug opt-in only for local development, and configure host/port through deployment settings.

**Issue — `server.py`, `recommend()` and `assistant()` (lines 85-96, 143-153):** request bodies are weakly validated. Recommendation requires truthy fields but does not validate their types or allowed values; non-string interests can raise errors, and assistant coerces arbitrary input to string without a maximum length. **Why it matters:** malformed requests can trigger 500s, inconsistent rankings, resource abuse, or noisy logs. **Recommendation:** enforce JSON object schemas, types, allowlists, limits, and structured 4xx responses.

**Issue — `server.py`, `row_gift()` and routes (lines 57-61, 79-82):** malformed JSON stored in category/occasion columns raises during serialization; unexpected exceptions return a generic message but are not logged with a request ID or handled by an operational logging policy. **Why it matters:** one bad row can break catalog or wishlist requests, while production diagnosis is difficult. **Recommendation:** validate catalog writes/imports, add centralized structured logging, and use appropriate error response schemas.

**Issue — `app.js`, `card()` (line 17):** most text fields are escaped, but `emoji` and numeric-ish values are inserted into HTML/style without escaping or validation. Current seed content is trusted, but future catalog/admin input could become a DOM injection vector. **Why it matters:** a future editable catalog changes the trust boundary. **Recommendation:** validate catalog fields server-side and build DOM nodes or escape all interpolated values; never rely on current seed-only assumptions.

**Issue — `app.js`, `api()` and errors (lines 14-15, 22, 35):** error handling is inconsistent; `refreshData()` suppresses all failures, so wishlist/history may silently appear empty while the backend is unavailable. **Why it matters:** users may think data was deleted or saved when it was not. **Recommendation:** distinguish offline, empty, loading, and failed states and confirm persistence only after the server responds.

**Issue — `server.py`, search storage and stats (lines 108-111, 137-140, 173-179):** no authentication, rate limiting, CSRF strategy, consent, retention, or privacy controls exist. CSRF risk becomes material if cookie-based identity is later added; current unauthenticated endpoints permit anyone reaching the app to modify the shared wishlist and flood search storage. **Why it matters:** abuse and privacy exposure. **Recommendation:** establish identity/ownership, request limits, retention/consent controls, and an appropriate CSRF/CORS policy before multi-user use.

## Dependencies, configuration, and deployment readiness

`requirements.txt` pins broad compatible ranges for Flask and Flask-Cors, but does not pin a lockfile or define dev/test/runtime groups. There is no `.env.example`, production server, Docker/container definition, CI workflow, logging configuration, secret management, backup/restore procedure, or deployment documentation. `README.md` is useful for local setup and accurately warns that values are illustrative and the app is a local demo, but it calls the theme a “toggle” without persistence and advertises history persistence without explaining global/single-user behavior.

**Issue — `requirements.txt`:** open-ended minor/patch ranges can yield different installs and Flask-Cors is currently used more broadly than needed. **Why it matters:** reproducibility and supply-chain changes are uncontrolled. **Recommendation:** define reproducible dependency locking and separate dev/runtime dependencies; remove unused dependencies when architecture permits.

**Issue — `README.md` and `server.py`:** configuration and run instructions cover local development only, while the app has no production entry point or operational checklist. **Why it matters:** a user can mistake a working local demo for a deployable service. **Recommendation:** keep local instructions explicit and add deployment-specific configuration, migrations, health/readiness behavior, backups, and observability before launch.

## Feature status

### Fully implemented for the current local demo

- Four-step wizard with required selections, live brief, back/next, and sample brief (`index.html:32-40`; `app.js:9-14,29`).
- Seed catalog and same-origin catalog/recommendation APIs (`server.py:12-38,79-112`).
- Recommendation card rendering, category filter, price ordering, wishlist toggle, and three-item comparison (`app.js:17-26`).
- SQLite persistence for a single shared wishlist and search records (`server.py:46-55,113-140`).
- Recent search listing and form brief restoration (`app.js:27-28,35`).
- Deterministic keyword-based assistant with suggestion buttons (`server.py:142-171`; `app.js:32-34`).
- Local health check, stats endpoint, empty states, reduced-motion stylesheet rule, and basic responsive layouts.

“Fully implemented” here means the described demo behavior exists; it does not mean production-grade quality.

### Partially implemented or incomplete

- **Recommendation quality:** only coarse rules over 24 illustrative products; no measured fit, product diversity, availability, explanations by score component, or feedback.
- **Budget:** ceiling filtering does not honor the displayed bands; no custom budget.
- **Wishlist/history:** persist globally without users; history has no deletion/retention; no account sync.
- **Comparison:** limited to three and current tab memory; no persistence or comparison entry point for arbitrary catalog items.
- **Assistant:** narrow English keyword extraction; no context/memory, validation of extracted details, or shared ranking service.
- **Search UX:** no global catalog search, pagination, saved-result snapshot, or URL-addressable state.
- **Catalog/product journey:** no live prices, retailer links, inventory, images, attribution, delivery, or outbound click tracking.
- **Theme/profile:** theme is not remembered; profile is a demo modal, not a real profile/account.
- **Operational readiness:** no production server/config, migration tooling, monitoring, tests, or deployment/backup process.

## Database and API improvements

1. Create versioned schema migrations and catalog import/update tooling; add constraints and indexes aligned to owner, product, and date queries.
2. Define response/request schemas, consistent error envelopes, pagination, filtering, and API versioning before the product surface grows.
3. Add owner/user identity and per-owner wishlist/history; provide clear/delete and retention controls.
4. Normalize categories/occasions into relational tables or validated JSON with stable enums; add product attributes, provenance, currency, retailer URL, image, availability/price observation time, and active status.
5. Close connections explicitly, configure SQLite concurrency for a small single-instance deployment, and choose a server database when multi-instance writes or user volume require it.

## Features needed for a real-world gift product

- A maintained catalog with verified products, current prices, currency, availability, retailer links, images, shipping/region filters, and clear affiliate/merchant disclosures.
- Search and discovery across the complete catalog, robust filters, budget ceilings/custom ranges, and useful no-match recovery.
- Accounts or private anonymous profiles, persistent wishlist/comparison, history controls, privacy consent/retention, and accessible export/delete behavior.
- Better preference capture (occasion, recipient, budget, interests, style, constraints) with transparent explanations, feedback, and ranking quality measurement.
- Production operations: secure deployment, stable configuration, migrations, backup/restore, logs/metrics, error monitoring, rate limits, and ongoing dependency/security maintenance.
- Accessibility and usability work: keyboard-complete controls, screen-reader announcements, contrast/readability, mobile navigation, focus management, and testing at zoom and narrow widths.

## Prioritized implementation roadmap

### Critical fixes

1. **Close exposure and debug risks:** isolate public static assets from the database/source tree; disable debug mode outside local development; remove or restrict global CORS; establish input schemas and limits.
2. **Correct core product semantics:** fix budget band behavior; replace or relabel the fabricated match percentage; validate all wizard/API values; show no-results and offline/save failures clearly.
3. **Protect user data:** decide identity/ownership model; stop sharing wishlist/history across visitors; add history clear/delete and retention rules before collecting real personal briefs.
4. **Accessibility baseline:** semantic choice controls and labels, accessible modal/focus behavior, live announcements, mobile navigation, readable contrast/type.

### Product improvements

1. Build a real, maintainable catalog with verified links, images, availability, regional prices, and update workflow.
2. Expand discovery with catalog search, more filters, custom budgets, pagination, and useful empty/recovery states.
3. Improve ranking with transparent weighted features, diversity, explanations, shared scoring between wizard and assistant, and feedback capture.
4. Persist comparison/theme preferences and improve history replay into a prior search/results state.
5. Improve assistant extraction and make recognized budget/occasion/interest constraints visible and correctable.

### Advanced features

1. Accounts, cross-device saved gifts, recipient profiles, reminders for upcoming occasions, and collaborative lists.
2. User feedback signals and recommendation evaluation/experimentation, with privacy-aware analytics.
3. Contextual assistant conversation and multilingual support, introduced only with clear data handling and user controls.
4. Retail integrations, affiliate attribution, price/stock monitoring, and notifications for changes.

### Production-readiness work

1. Production WSGI deployment, environment-based configuration, secret management, HTTPS, security headers, strict CORS/CSRF policy, rate limiting, and abuse controls.
2. Versioned migrations, reproducible dependencies, automated tests/CI, backup/restore, and database concurrency plan.
3. Structured logs, request IDs, monitoring, alerting, readiness/liveness checks, error tracking, and operational runbooks.
4. Privacy policy/consent and retention implementation, data export/deletion, accessibility review, and security review before public launch.

**Approval gate:** this document is an audit only. No implementation changes have been made; the next step is to wait for approval before modifying the project.

