# Evaluation plan and instruments

Maps the report's planned metrics (§3.19) and test levels (§3.20) to what the build measures automatically and what the 15-participant study collects.

## Automated (run `python -m scripts.evaluate` from `backend/`)

| Report metric | How it is measured | Output |
|---|---|---|
| Retrieval relevance | hit@1 / hit@3 of the expected knowledge entry on a gold question set (EN, HA, YO, IG, paraphrases) | `docs/evaluation-results.md` |
| Source accuracy | top cited source equals the expected entry | same |
| Response relevance (proxy) | in-scope questions answered rather than falling back; out-of-scope questions falling back (fallback precision) | same |
| Language accuracy (automatic part) | detected language and answer language match the question's language | same |
| Response latency | per-request `timings` (language, retrieval, generation, total); mean and p95 over the gold set; every answer also shows its latency in the UI | same, and `/api/admin/stats` |

Add gold questions in `backend/scripts/evaluate.py` (`GOLD`). The expected-entry column tells you exactly which knowledge entry should win, so a miss points to either a wording gap (add an `alt_questions` phrasing) or a glossary gap (`services/language.py`).

## With participants (prototype evaluation sample, n = 15)

Tasks (one per domain plus one follow-up and one out-of-scope):

1. Find out what documents you need to enrol for a NIN.
2. Find out how much a 64-page, 10-year passport costs and where to apply.
3. You lost your driver's licence while it is still valid. Find out what to do.
4. Find out whether registering a newborn costs anything and where to go.
5. Ask a follow-up question about cost in the same conversation.
6. Ask one question in your indigenous language.
7. Ask something unrelated (for example the weather) and observe the response.

Record for each task: completed (yes/no), time to complete, whether the participant opened a source card, whether they understood the "official channel" prompt, and any confusion.

### System Usability Scale (SUS), 1 = strongly disagree … 5 = strongly agree

1. I think that I would like to use this chatbot frequently.
2. I found the chatbot unnecessarily complex.
3. I thought the chatbot was easy to use.
4. I think that I would need the support of a technical person to be able to use this chatbot.
5. I found the various functions in this chatbot were well integrated.
6. I thought there was too much inconsistency in this chatbot.
7. I would imagine that most people would learn to use this chatbot very quickly.
8. I found the chatbot very cumbersome to use.
9. I felt very confident using the chatbot.
10. I needed to learn a lot of things before I could get going with this chatbot.

Score: odd items contribute (response − 1), even items contribute (5 − response); sum and multiply by 2.5. 68 is the conventional average.

### Chatbot-specific items (Borsci et al. 2022 Chatbot Usability Scale, selected), same 1–5 scale

- The chatbot's responses were easy to understand.
- The chatbot understood what I was asking.
- The answers addressed my actual question.
- I trust the information the chatbot gave me.
- The sources shown made the answers more credible.
- The chatbot's language (Hausa / Yorùbá / Igbo) sounded natural.
- The chatbot made it clear what it could not do.

### Language quality (competent-speaker review)

For each indigenous-language entry a competent speaker rates: accuracy of meaning (1–5), naturalness (1–5), correct use of official terms. Record corrections directly in `backend/data/knowledge/entries.<lang>.json` and re-ingest.

## Analysis

Frequencies, percentages and means for closed items (Excel or equivalent); thematic grouping of open comments under ease of use, language accessibility, understanding of responses, relevance, trust in sources, problems encountered and suggestions (report §3.19 "Method of Data Analysis").
