# Tambaya NG

**Indigenous Language Chatbot for Public Services**: a retrieval-augmented conversational assistant that answers questions about four Nigerian public services in English, Nigerian Pidgin, Hausa, Yorùbá and Igbo, grounded in verified information from the responsible agencies.

| Service | Agency |
|---|---|
| National Identification Number (NIN) | National Identity Management Commission (NIMC) |
| International passport | Nigeria Immigration Service (NIS) |
| National Driver's Licence | Federal Road Safety Corps (FRSC) |
| Birth and civil registration | National Population Commission (NPC) |

Seminar project, Department of Computer Science, Yaba College of Technology (ND). *Tambaya* is Hausa for "ask".

## Stack

Python 3.11+ / FastAPI · PostgreSQL 15+ with pgvector · Groq API (`openai/gpt-oss-120b`, falling back to `openai/gpt-oss-20b`) for query rewriting and grounded generation · local embeddings (Groq has no embeddings endpoint) · plain HTML/CSS/JavaScript front end · optional Firecrawl for staged knowledge refreshes.

## How it works

```
message ─► validate ─► detect language ─► rewrite to one English search query (uses conversation history)
        ─► hybrid retrieval: pgvector cosine + PostgreSQL full-text, fused with Reciprocal Rank Fusion
        ─► grounding gate (low similarity = no generation)
        ─► Groq generates in the user's language from the numbered context only, returns JSON
           {answer, cited, needs_official_action, official_channel, confidence}
        ─► numbers, URLs, citations, language verified ─► (Groq down or answer fails a check? verified entry verbatim)
        ─► (nothing grounded? templated fallback naming the official channel)
        ─► conversation stored without personal data ─► answer + source cards + timings
```

Full algorithm, data model, requirement traceability and sprint plan: [`docs/PLAN.md`](docs/PLAN.md). Audit of retrieval quality: [`docs/AUDIT.md`](docs/AUDIT.md). Design system: [`docs/DESIGN.md`](docs/DESIGN.md). Evaluation instrument and latest automated results: [`docs/EVALUATION.md`](docs/EVALUATION.md), [`docs/evaluation-results.md`](docs/evaluation-results.md).

**Groq vs offline mode.** With `GROQ_API_KEY` set, Groq rewrites follow-ups into standalone queries and writes the answer from the retrieved entries; every generated answer then passes a verification step (figures, URLs, citation markers, answer language, instruction leaks) before it is shown. Without a key the system still runs end to end and answers with the verified entry verbatim in the user's language. `/api/health` reports `llm_enabled` and the model in use. **Note for the write-up:** the seminar report names the Gemini API; this implementation uses Groq's OpenAI-compatible API instead (project decision), and the retrieval design, prompts and safeguards are model-agnostic.

## Run locally

1. PostgreSQL with pgvector. Easiest: `docker compose up -d db` (uses the `pgvector/pgvector:pg16` image). Or install the extension on your own server; the app runs `CREATE EXTENSION IF NOT EXISTS vector` itself.
2. Backend:
   ```bash
   cd backend
   python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   cp .env.example .env                                   # set DATABASE_URL, GROQ_API_KEY, ADMIN_TOKEN
   python -m scripts.init_db                              # creates tables + indexes, loads the knowledge base
   uvicorn app.main:app --reload --port 8000
   ```
3. Open http://localhost:8000 (chat) and http://localhost:8000/admin (knowledge base, needs `ADMIN_TOKEN`). API docs at http://localhost:8000/docs.

Everything in one go with Docker: `docker compose up --build` then open http://localhost:8000.

## Deploy (free, from GitHub)

Render allows **one free Postgres per account**, so the blueprint does not create a database; you supply `DATABASE_URL`.

1. Push the repo to GitHub (GitHub Desktop: File → Add local repository → Publish repository).
2. Get a Postgres URL. Recommended: **Neon** (https://neon.tech, free, no expiry, supports `vector`, `pg_trgm` and `unaccent`). Create a project, then copy the connection string from the dashboard with **"Pooled connection" turned off** (direct URL; it ends in `?sslmode=require`). Alternatives: an existing Render Postgres (use its *Internal Database URL*; the app creates its own tables and extensions), or delete your other free Render database and use `render.with-db.yaml` instead.
3. On https://render.com: New → Blueprint → select the repo. Paste the URL into `DATABASE_URL`, and your Groq key into `GROQ_API_KEY` (optional; without it the app runs in offline mode). On every boot the container runs `start.sh`: `init_db` (creates extensions and tables, loads or updates the knowledge base without duplicating anything), then uvicorn on Render's `$PORT`.
4. Open `https://<service-name>.onrender.com/api/health`: `"database": true, "pgvector": true`, and with a key `"llm_enabled": true`. Copy `ADMIN_TOKEN` from the service's Environment tab for `/admin`.

Free Render web services sleep after 15 minutes idle; the first request afterwards takes about 30 seconds.

## Knowledge base

`backend/data/knowledge/`:

- `catalog.json`: languages, agencies, service domains (with routing keywords), knowledge documents with `source_url` and `last_verified`.
- `entries.en.json`, `entries.ha.json` (full native sets), `entries.yo.json`, `entries.ig.json` (seed sets). Entries with the same `id` across files are translations of the same fact, which lets retrieval run on the English canonical layer and present the user's language.

Edit the JSON and run `python -m scripts.init_db`, or use the admin page (add, edit, approve, deactivate, re-ingest, Firecrawl refresh). Refreshed content is staged as `pending` and never used in answers until approved.

Figures in the entries reflect the official schedules current at the stated `last_verified` date (NIMC fee schedule May 2025, NIS fees effective 1 Sept 2025, JTB driver's licence fees effective 1 Nov 2024, NPC eCRVS nationwide July 2026). Re-verify before a defence or deployment.

## Tests, audit and evaluation

```bash
cd backend
python -m pytest -q              # 122 tests: unit + TC-01 … TC-08 from Table 3.11 + admin + 557-question audit bank + Naija audit
python -m scripts.audit          # audit bank with per-failure report → docs/audit-results.md
python -m scripts.audit_holdout  # 62 held-out phrasings (generalisation check)
python -m scripts.audit_naija    # 195 messages typed the way Nigerians type: SMS spellings, Pidgin, code-mixing,
                                 # small talk, misuse, rambling, plus 11 multi-turn dialogues (--holdout, --holdout-b)
python -m scripts.evaluate       # gold-set metrics → docs/evaluation-results.md
```

The audit (what was tested, the 16 bugs it found and how each was fixed) is in [`docs/AUDIT.md`](docs/AUDIT.md).

## API

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/chat` | `{message, language: auto|en|ha|yo|ig, conversation_id?, user_id?}` → answer, sources, flags, timings |
| GET | `/api/health` | database, pgvector, `llm_enabled` / `llm_model` (Groq), embedder, active entries |
| GET | `/api/languages`, `/api/domains` | catalog for the UI |
| GET | `/api/conversations/{id}?user_id=` | transcript for resuming on the same device |
| * | `/api/admin/*` | entries CRUD, approve, deactivate, reingest, refresh, documents, stats (header `X-Admin-Token`) |

## Project layout

```
backend/
  app/            config, db, models (report tables 3.2–3.7 + conversation tables), schemas, routers, services/
  data/knowledge/ catalog + entries per language
  scripts/        init_db, evaluate
  tests/          pytest suite
frontend/
  index.html      landing + chat (single page, no build step)
  admin.html      knowledge-base management
  css/ js/ assets/
docs/             PLAN.md, DESIGN.md, EVALUATION.md, evaluation-results.md, screenshots/
```

## Boundaries

Tambaya NG is an information and guidance layer. It does not enrol, issue, verify, pay or access any government record, and it never asks for a NIN, passport number or other identifier. When an action is required it names the official channel.
