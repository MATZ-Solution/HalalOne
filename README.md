# HalalOne

HalalOne is a halal verification platform built around a single question people actually ask every day: *"is this okay for me to eat / use?"* Instead of leaving that question to a barcode app that just checks a static allowed-list, HalalOne puts an agent in the loop that can search a certified product database, reason about ingredients and certification bodies, and fall back to the open web when the database comes up empty — then explains its answer instead of just returning a badge.

Under the hood it's a Next.js frontend talking to a FastAPI backend over WebSockets, with a LangGraph-based agent doing the actual product reasoning against a Typesense-backed catalog of 200,000+ halal-certified products.

## Why this exists

Halal status isn't a single boolean. The same additive (E471, gelatin, certain enzymes) can be halal, haram, or "depends on the source" — and the honest answer usually needs a certification body, a country of sale, or a manufacturer's own disclosure to resolve.

HalalOne instead treats it as a search + reasoning problem: pull matching products from a certified database, apply the filters the user actually specified (never ones it assumed), search conceptually when the query is descriptive rather than exact, and only reach for the open web when the database has nothing. The user gets a plain-language answer plus the actual product records it was based on — not a black-box verdict.

## The agent

This is the core of the product, so it's worth walking through how it actually works rather than just naming it.

Chat requests come in over a WebSocket (`backend/main.py`) and are handed to a LangGraph state machine (`backend/agents/langgraph_agent/`) with four nodes:

1. `classify_intent` — a cheap LLM call decides if the message needs a product search at all, or if it's a direct response (greeting, follow-up question about something already shown, off-topic). Skips the whole search pipeline when it isn't needed.
2. `search_node` — the model picks from three tools and can call them repeatedly (capped at 4 iterations so a confused model can't loop forever):
  - `KeywordFilterSearch` — exact/keyword matching on product name, brand, health info, and typical use, combined with hard filters (halal status, certification body, country, marketplace, barcode, etc.)
  - `SemanticFilterSearch` — vector search over product embeddings for descriptive queries like *"a calcium-rich snack for kids"* or *"natural red food coloring"*
  - `WebSearch` — a last resort, used only when the certified database returns nothing. Results from this path are explicitly marked `verified: false` and carry per-field grounding citations, so the frontend can visually distinguish "we're sure" from "we think, and here's why"
3. `tool_node` — executes whatever the model called and streams live status updates back to the client ("Searching keywords", "Applying filters", "Searching the web") so the UI isn't just a spinner.
4. `response_node` — writes the final natural-language answer and selects which product records to attach. Deliberately doesn't let the LLM re-emit product data itself — it only returns IDs, which are then resolved back to the actual database records. This keeps the numbers, certification numbers, and barcodes the user sees exactly what's in the database, with no chance of the model quietly hallucinating a field.

A few things about the surrounding harness that matter more than they might look at first glance:

- **Typo and filter normalization** happens before anything hits the search layer — "hlal" → `Halal`, "dubai" → `UAE`, etc. — and if a filter value is too ambiguous to correct, the agent asks the user to clarify rather than guessing.
- **Conversation compaction**: long chats get automatically folded into a rolling summary once they cross a token threshold, so sessions don't degrade or blow past context limits. The user gets a chance to confirm or defer it, and declining raises the threshold rather than nagging on every message.
- **Image input**: a vision model can read a product label or ingredient list directly from a photo and route the extracted fields into the same search pipeline.
- **Streaming is resilient to reconnects** — the pipeline that answers a prompt runs detached from the WebSocket connection that started it, so a page reload mid-answer doesn't kill the agent or lose the reply; it's persisted and delivered over pub/sub whenever the user reconnects.



## Architecture

```
frontend/   Next.js 16 (App Router) + React 19 + Tailwind — chat UI, directories, auth
backend/    FastAPI + WebSockets — the agent, search, chat persistence, rate limiting
```

**Backend building blocks:**

- `agents/langgraph_agent/` — the LangGraph agent described above (nodes, tools, prompts, models)
- `collection/` — Typesense collection lifecycle: create, insert (bulk/single/cloud), retrieve, delete, search
- `search_products/` — the product search engine used outside the agent's own tools
- `llms/` — vision model wrapper for reading product photos, plus the shared LLM client
- `chat_store.py`, `session_state.py`, `pubsub.py` — Supabase-backed chat persistence, Valkey-backed session/history caching, and pub/sub fan-out for multi-instance deployments
- `rate_limit.py` — per-user and global rate limiting so one user (or the agent itself) can't drain shared LLM budget
- `evaluations/` — single-step and trajectory evals for the agent's tool-calling behavior
- `sql/`, `models/` — schema and Pydantic models shared between the agent and the API

**Frontend building blocks:**

- `components/HalalifyChat.tsx` — the chat interface, wired to the backend over a WebSocket
- `components/QRBarcodeScanner.tsx`, `ImageExtractionDialog.tsx` — barcode/photo capture flow into the agent
- `components/halalone/` — the shared design-system primitives (buttons, cards, badges, logo)
- `components/product/` — product detail rendering for results the agent returns



## Pages

- `/` — public landing page: product pitch, live-feeling demo data, and the entry point into the app.
- `/login`**,** `/signup` — Supabase-backed auth, including Google sign-in.
- `/chat` — the gated core product: conversational product search, barcode/photo scanning, and result cards backed by the agent above.
- `/directory/business-directory` — searchable directory of halal-certified manufacturers, exporters, food service, ingredient suppliers, pharma, cosmetics, retail, finance, and logistics businesses.
- `/directory/certification-authority-directory` — reference directory of the world's halal certification bodies across nine regions, with their standards, product scope, and international recognition.
- `/directory/standards-library` — international, regional, and national halal standards (OIC/SMIIC, MS, GSO, SNI, SFDA, SANS, PS, TSE) with their key requirements, cross-referenced and filterable.
- `/directory/regulatory-intelligence` — country-by-country import rules: national standards, accepted certifiers, labelling requirements, and import documentation across OIC and key non-OIC markets.
- `/directory/trade-intelligence` — halal trade corridors scored for opportunity, with exporter-to-importer flow value, YoY growth, and the certification needed to access each market.
- `/directory/news-alerts` — curated halal industry news and regulatory alerts: certification changes, standard updates, recalls, and market moves.



## Running it locally

**Backend**

```bash
cd backend
python -m venv venv && source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env   # fill in API keys, Supabase, Valkey, etc.
uvicorn main:app --reload
```

**Frontend**

```bash
cd frontend
npm install
cp .env.example .env.local   # backend URL + Supabase keys
npm run dev
```

Or bring up backend, frontend, and Typesense together:

```bash
docker compose up
```

### Backend `.env`

Copy `backend/.env.example` to `backend/.env` and fill in:

| Variable | Required | What it's for |
|---|---|---|
| `GROQ_API_KEY` | Yes | Runs the agent's LLMs (intent classification, search, response, summarization) — all served through Groq. |
| `CEREBRAS_API_KEY` | Yes | Loaded alongside Groq at startup (`llm.py` fails fast if it's missing); Cerebras is currently kept as a swappable backend rather than the active one. |
| `FIREWORKS_AI_API_KEY` | Yes | Generates the embeddings used by `SemanticFilterSearch` against the product catalog. |
| `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` | Yes | Auth (validating user JWTs) and chat history/session storage. |
| `VALKEY_URL` | Yes | Session/history caching, rate limiting, pub/sub fan-out across backend instances. Defaults to `redis://localhost:6379/0` if unset. |
| `FRONTEND_URL` | Yes | Added to the CORS allow-list alongside the local dev ports. |
| `EXA_API_KEY` | Recommended | Powers `WebSearch`, the agent's last-resort tool when the certified database has no match. Without it, that tool just fails quietly and the agent answers from the database alone. |
| `TYPESENSE_HOST` / `TYPESENSE_PORT` / `TYPESENSE_PROTOCOL` / `TYPESENSE_API_KEY` | No | Not in `.env.example` but read by `config/typesense_client.py`; defaults (`localhost:8108`, http, key `abcd`) match the bundled `docker-compose.yml` Typesense service, so local dev works without setting these. Point them at Typesense Cloud for anything beyond local. |
| `RL_MAX_CONNECTIONS`, `RL_MSG_RATE_PER_SEC`, `RL_LLM_RATE_PER_MIN`, `RL_CONN_TTL`, `RL_CONN_HEARTBEAT` | No | Tune the fleet-wide connection cap and per-user rate limits; sensible defaults are baked in. |
| `SUMMARY_TOKEN_THRESHOLD`, `SUMMARY_KEEP_TURNS` | No | Tune when a chat gets prompted to compact and how many recent turns stay verbatim. |
| `SHUTDOWN_DRAIN_TIMEOUT` | No | How long a graceful shutdown waits for in-flight agent answers to finish and persist. |
| `APP_ENV` | No | `development` or `production`; picked up by `log/logger.py` to switch between colored and JSON log output. |

### Frontend `.env.local`

Copy `frontend/.env.example` to `frontend/.env.local` and fill in:

| Variable | Required | What it's for |
|---|---|---|
| `NEXT_PUBLIC_BACKEND_URL` | Yes | Base URL of the FastAPI backend (health check, image extraction). |
| `NEXT_PUBLIC_BACKEND_WS_URL` | Yes | WebSocket URL the chat UI connects to for the agent conversation. |
| `NEXT_PUBLIC_SUPABASE_URL` / `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | Yes | Client-side Supabase auth (login/signup, session token used on the WebSocket). |
| `SUPABASE_AUTH_EXTERNAL_GOOGLE_CLIENT_SECRET` | Only if using Google sign-in | Server-side secret for the Google OAuth flow behind `GoogleButton.tsx`. |