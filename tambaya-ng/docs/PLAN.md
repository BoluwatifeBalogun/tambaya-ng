# Tambaya NG: Implementation Plan

**Project:** Indigenous Language Chatbot for Public Services (YabaTech ND Computer Science seminar report; Dhikrullahi, Alabebe, Oche, Adeniyi, Alabi; supervisor Dr. Okiki)
**Working name:** Tambaya NG ("Tambaya" is Hausa for "question/ask")
**Case study:** Nigeria as a whole; four federal services: NIN (NIMC), international passport (NIS), driver's licence (FRSC), birth and civil registration (NPC)
**Languages:** English + Hausa fully native in the knowledge base (per report §3.18 and Sprint 1). Yoruba and Igbo are enabled as response languages through the language layer (generation in that language from English evidence) and have a smaller seeded set of native entries. The language layer is isolated so more languages can be added without touching retrieval (report §3.12.5).
**Stack (report §3.16):** Python 3.11+ / FastAPI, PostgreSQL 15+ with pgvector, Groq API for generation (report names Gemini; switched to Groq by project decision), local embeddings, plain HTML/CSS/JavaScript front end, Git/GitHub, optional Firecrawl refresh (§3.19 step 6).

---

## 1. What the report commits us to (traceability)

| Report item | Where it lands in the build |
|---|---|
| §1.4 Obj. 2: structured KB from official sources | `backend/data/knowledge/*.json` with `source_url`, `last_verified`, agency, domain, language |
| §1.4 Obj. 3: RAG in English + indigenous language | `services/pipeline.py` hybrid retrieval + grounded generation |
| §1.4 Obj. 4: safeguards, reduce misleading responses, direct to official channels | Grounding gate, strict system prompt, citation verification, fallback templates with official links |
| §2.5.2 ten RAG components | Collection → cleaning → chunking → embedding → vector store → query embedding → similarity retrieval → context construction → generation → source/fallback handling; each is a named function |
| §3.12.6 System boundary | Boundary rules in the system prompt + `needs_official_action` flag rendered as an "Official channel" card in the UI |
| §3.13.1 Functional requirements (10) | Mapped one-to-one in §6 below |
| §3.14.5 ERD + §3.15 tables 3.2 to 3.7 and conversation tables | `models.py`: agency, service_domain, knowledge_document, source, language, knowledge_entry (with `embedding_vector VECTOR`), app_user, conversation, message |
| §3.19 KB update process with review before approval | Admin API: Firecrawl/manual imports land as `is_active=false` staged entries until an admin approves |
| §3.20 Table 3.11 TC-01 to TC-08 | `backend/tests/test_report_cases.py` one test per TC, plus latency recording for TC-08 |
| §3.19 Evaluation metrics | `scripts/evaluate.py` computes retrieval relevance (hit@k), source accuracy, latency; SUS/Chatbot Usability Scale form template in `docs/EVALUATION.md` |

---

## 2. Core algorithm (the RAG pipeline)

Input: `message`, `language` (`auto | en | pcm | ha | yo | ig`), optional `conversation_id`.

```
1. VALIDATE
   trim; reject empty / > 1000 chars; strip control chars  → FR "handle basic errors"

1b. SMALL TALK
   if every word is a greeting / thanks / acknowledgement / goodbye (any of the five languages, emoji too):
       reply instantly from a localized template; store the turn with no topic; stop

2. IDENTIFY LANGUAGE
   if language == auto:
       lexicon detector (Hausa / Yoruba / Igbo stop-words, diacritics; Nigerian Pidgin scored separately as its own language,
       orthography cues) → confidence
       if confidence < 0.6 and Groq available → take the language code returned by the rewrite call
   target_language = selected or detected

3. BUILD RETRIEVAL QUERY  (handles follow-ups, topic switches, SMS spellings and code-switching)
   SMS spellings rewritten in place for English and Pidgin ("hw much is d pasport")
   if the message names a different service than the previous turn: no topic carried; previous intent
   (fee, documents, renewal...) carried only if the message states none
   context = last 6 messages of the conversation
   if Groq available:
       Groq rewrites (message + context) into ONE standalone English search query
       e.g. "nawa ne kudin?" after a NIN-modification turn → "NIN data modification fee"
   else:
       glossary normalisation (fasfo→passport, lasisin tuki→driver's licence,
       takardar haihuwa→birth certificate, ...) + append domain of previous turn

4. ROUTE DOMAIN (soft)
   keyword + embedding classification into {nin, passport, drivers_licence,
   civil_registration, general, out_of_scope}; used as a score boost, never a hard filter

5. HYBRID RETRIEVAL
   a. dense: pgvector cosine similarity on knowledge_entry.embedding_vector  (top 12)
      searches English entries AND entries in target_language
   b. lexical: PostgreSQL full-text search (tsvector, websearch_to_tsquery)  (top 12)
   c. fuse with Reciprocal Rank Fusion  score = Σ 1/(60 + rank)   (+0.05 if domain match)
   d. keep top 5; carry document title, agency, source_url, last_verified

6. GROUNDING GATE
   if best cosine < 0.45 AND no lexical hit  → FALLBACK (step 9)
   if routed domain == out_of_scope and best cosine < 0.6 → FALLBACK

7. GENERATE (Groq, openai/gpt-oss-120b → fallback openai/gpt-oss-20b, JSON mode)
   system prompt: answer ONLY from numbered context; cite [n]; respond in
   target_language; keep official names/acronyms; never invent fees or steps;
   if context insufficient say so; flag when the user must go to an official channel.
   response_schema (JSON): {answer, cited: [n...], needs_official_action, official_channel, confidence}
   temperature 0.2

8. VERIFY
   drop citations not in context; if answer empty or confidence < 0.4 → FALLBACK
   if Groq unavailable (timeout / 4xx / 5xx / non-JSON) or the answer fails verification → EXTRACTIVE COMPOSER:
       return the top entry's answer_text in target_language (or English with a
       notice) + source card  (this is what TC-06 exercises)

9. FALLBACK (controlled, templated, per language)
   "I could not confidently find this in the verified knowledge base" + the
   official site(s) for the most likely domain. No LLM free text.

10. PERSIST + RESPOND
   store user + assistant messages (text, language, latency, cited entry ids; no PII)
   return {answer, language, domain, sources[], needs_official_action,
           official_channel, fallback: bool, latency_ms: {retrieval, generation, total}}
```

Embeddings: Groq serves chat models only, so embeddings are local: a deterministic 768-dim hashed n-gram embedder by default (no downloads; used for every audit), or any sentence-transformers model via `LOCAL_EMBED_MODEL` (e.g. `intfloat/multilingual-e5-small`). The embedder name is stored per entry and reported by `/api/health`.

## 3. Request flow (sequence, §3.14.3)

```
Browser (index.html)
  └─ POST /api/chat {message, language, conversation_id}
       FastAPI router → pipeline.answer()
          ├─ language.detect / rewrite        (language-processing layer)
          ├─ retrieval.hybrid_search          (RAG layer → pgvector + FTS in PostgreSQL)
          ├─ generation.generate (Groq) | extractive
          └─ repository.save_turn             (conversation tables)
       ← JSON response (answer + sources + flags + timings)
  └─ render: streamed-looking reveal, source cards, "official channel" card, language chip
```

Admin flow: `admin.html` → `/api/admin/*` (token header) → list/create/update/deactivate entries, re-embed, import JSON, trigger Firecrawl refresh → staged entries pending approval.

## 4. Data model (PostgreSQL + pgvector)

```
language(language_id, language_name, language_code, is_active)
agency(agency_id, agency_name, agency_description, website_url, contact_info, is_active)
service_domain(domain_id, agency_id→agency, domain_name, slug, description, is_active)
knowledge_document(document_id, domain_id→service_domain, title, document_type,
                   source_url, publish_date, last_updated, is_active)
source(source_id, document_id→knowledge_document, source_name, source_url, source_type, accessed_at)
knowledge_entry(entry_id, document_id→knowledge_document, language_id→language,
                section_title, question_text, answer_text, embedding_vector VECTOR(768),
                search_vector TSVECTOR (generated), page_reference, is_active,
                review_status, created_at)
app_user(user_id, created_at, last_seen_at)             -- anonymous, no PII
conversation(conversation_id, user_id→app_user, started_at, language_code)
message(message_id, conversation_id→conversation, role, text, language_code,
        domain, cited_entry_ids[], latency_ms, created_at)
```
Indexes: HNSW (cosine) on `embedding_vector`, GIN on `search_vector`, btree on FKs.

## 5. Knowledge base plan (Sprint 1)

Sources: nimc.gov.ng (NIN, enrolment, modification, re-issuance, NIN slip, free enrolment notice), immigration.gov.ng + passport.immigration.gov.ng (standard/official passport, fresh vs renewal, fees by booklet, documents, processing), nigeriadriverslicence.org / frsc.gov.ng (fresh, renewal, re-issue, learner's permit, documents, driving school, validity), nationalpopulation.gov.ng (birth registration, late registration, birth attestation, death/marriage registration pointers).

Each entry: `question_text` (natural question in that language), `answer_text` (verified, concise, includes conditions), `section_title`, `page_reference`, plus the document's `source_url` and `last_verified` date. English entries are the canonical layer; Hausa entries are full native counterparts; Yoruba/Igbo get a core seed set (greetings, "what is NIN", top-asked question per domain) so language quality can be evaluated by competent speakers later (report §3.19 risk management).

## 6. Functional requirement coverage (§3.13.1)

| FR | Implementation |
|---|---|
| Accept user questions | `POST /api/chat` + chat composer |
| Support language interaction | language selector, auto-detect, per-language generation and fallback |
| Retrieve relevant information | hybrid pgvector + FTS, RRF |
| Generate responses | Groq grounded generation, JSON contract, post-generation verification |
| Support follow-up questions | conversation memory + query rewriting |
| Provide source information | source cards (title, agency, URL, last verified) |
| Handle unavailable information | grounding gate + templated fallback |
| Provide official-service guidance | `needs_official_action` + `official_channel` card |
| Manage KB information | admin API + admin.html |
| Handle basic errors | validation layer, friendly error UI, timeouts |

## 7. Work plan (mirrors Table 3.9 sprints, compressed into this build)

| Sprint | Build step | Output |
|---|---|---|
| 1 | Knowledge base sourcing + structuring (EN/HA, YO/IG seed) | `backend/data/knowledge/` JSON |
| 2 | Front end: landing + chat + admin, design system, motion | `frontend/` |
| 3 | FastAPI backend: schema, ingestion, hybrid RAG, Groq, fallback, conversation storage, admin API | `backend/app/` |
| 4 | Firecrawl refresh hook, tests TC-01 to TC-08, evaluation script, README, docker-compose | `tests/`, `scripts/`, `docs/` |

## 8. Front-end direction (from ui-ux-pro-max + 21st.dev + Awwwards + Framer research)

- Skill output: style "AI-Native UI" blended with "Accessible & Ethical" (government audience): minimal chrome, streaming text, typing indicator, context cards, 4.5:1 contrast, visible focus, reduced-motion support, 44px targets, no emoji icons (Lucide-style inline SVG).
- Theme: dark "midnight forest" with a refined Nigerian green (not flag green), warm kola/gold accent, grain overlay, glass panels, conic-gradient border beams on the composer, spotlight hover on cards, staggered word reveal on the hero (short headline only), fade-up on scroll (8 to 16px offsets, 300 to 450ms, expo-out), typing dots and token-by-token reveal in chat.
- Typography: display + body pairing from Google Fonts chosen in the design report; base 16px, line-height 1.5, fluid clamp() display scale.
- Full details and tokens: `docs/DESIGN.md`.

## 9. Testing and evaluation

- `pytest`: unit (language detection, glossary, RRF, grounding gate), integration (DB + retrieval), system (TC-01 to TC-08 via FastAPI TestClient), performance (latency recorded per TC-08).
- `scripts/evaluate.py`: runs a gold question set (EN + HA, paraphrases, out-of-scope) and reports hit@1/hit@3, source accuracy, fallback precision, mean latency, written to `docs/evaluation-results.md` for Chapter Four.
- `docs/EVALUATION.md`: SUS + Chatbot Usability Scale instrument for the 15-participant evaluation.
