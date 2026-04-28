# Mumzworld Gift Finder

**Track A — AI Engineering Intern Assessment**

A bilingual (English + Arabic) gift recommendation engine for Mumzworld. Type a natural language request like *"thoughtful gift for a friend with a 6-month-old, under 200 AED"* and get a curated shortlist of 1–3 products with reasoning in both languages, validated against a strict schema.

---

## One-paragraph summary

Mumzworld Gift Finder is a RAG-powered agentic pipeline that turns a natural language gift query into a structured, bilingual product shortlist. It extracts intent (age, budget, occasion, preferences) via an LLM, retrieves semantically relevant candidates from a 50-product catalog using FAISS vector search, ranks and reasons about eligible products using a second LLM call, and validates every output against a Pydantic schema before returning it. When no product matches the budget or age constraints, it returns an explicit `no_match_reason` in the query's language rather than an empty list. The UI is built in Streamlit with bilingual tabs, confidence scores, and budget/age badges per recommendation.

---

## Setup and run (under 5 minutes)

**Prerequisites:** Python 3.10+, Git

```bash
git clone https://github.com/YOUR_USERNAME/mumzworld-gift-finder.git
cd mumzworld-gift-finder
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```
OPENROUTER_API_KEY=your_openrouter_key_here
```

Get a free OpenRouter key at https://openrouter.ai — no credit card required.

Run the app:

```bash
streamlit run app.py
```

Open http://localhost:8501 in your browser. That's it.

---

## Project structure

```
mumzworld-gift-finder/
├── app.py                  # Streamlit UI
├── pipeline/
│   ├── schemas.py          # Pydantic models: GiftIntent, GiftRecommendation, GiftFinderResponse
│   ├── intent_parser.py    # LLM: extract structured intent from query
│   ├── retriever.py        # FAISS: semantic search over product catalog
│   ├── ranker.py           # LLM: score and reason about candidates
│   ├── formatter.py        # Assemble final response, handle no-match
│   └── gift_finder.py      # Pipeline orchestrator
├── data/
│   └── catalog.json        # 50 mock Mumzworld products (EN + AR names, AED prices)
├── evals/
│   ├── test_cases.json     # 12 test cases (easy + adversarial + Arabic)
│   ├── run_evals.py        # Automated eval runner with scoring
│   └── eval_results.json   # Last run results (auto-generated)
├── .env                    # API keys (gitignored)
├── requirements.txt
├── README.md
├── EVALS.md
└── TRADEOFFS.md
```

---

## Pipeline architecture

```
User Query (EN or AR)
        │
        ▼
  Intent Parser          LLM extracts: age, budget, occasion, preferences, language, is_for_mom
        │
        ▼
  FAISS Retriever        Embeds query → cosine search over 50-product catalog → top-10 candidates
        │                Tags each candidate: within_budget, age_suitable
        ▼
  Ranker                 LLM scores eligible candidates → returns 1-3 with reason_en + reason_ar
        │
        ▼
  Formatter              Detects no-match cause → populates no_match_reason in query language
        │
        ▼
  Pydantic Validator     GiftFinderResponse schema enforced — malformed output raises explicitly
        │
        ▼
  Streamlit UI           Bilingual tabs, confidence %, price, budget/age badges
```

---

## Running evals

```bash
python evals/run_evals.py
```

Results print to terminal and save to `evals/eval_results.json`. See EVALS.md for full rubric and scores.

---

## Tooling

| Tool | Role |
|---|---|
| OpenRouter (free tier) | LLM gateway — routes to `google/gemma-3-27b-it:free` with 4-model fallback chain |
| sentence-transformers `all-MiniLM-L6-v2` | Embedding model for FAISS index — runs locally, no API cost |
| FAISS (faiss-cpu) | Local vector index — cosine similarity search over product catalog |
| Pydantic v2 | Schema validation — every LLM output validated before use |
| Streamlit | UI — chosen for fastest path to a demo-able bilingual interface |
| Claude (Anthropic) | Pair-coding and architecture review during development |

**How AI tools were used:** Claude was used as a pair-coding assistant throughout — writing boilerplate, debugging import errors, and iterating on prompt structure. All prompts, schema design, pipeline architecture, and eval rubric were authored and reviewed by me. The ranker and intent parser prompts went through 3+ iterations to improve Arabic output quality and JSON reliability. Claude helped diagnose the `google.generativeai` deprecation issue and suggested switching to `google.genai` SDK, then to OpenRouter when Gemini free tier was exhausted.

**What worked:** The fallback model chain was essential — free tier rate limits hit hard when running 12 eval cases sequentially. The 5-second sleep between eval calls solved per-minute limits.

**What didn't:** `gemini-1.5-flash` via the old SDK returned 404 (model deprecated). `google/gemma-3-27b-it:free` on OpenRouter was the most reliable free model for Arabic output quality.

**Key prompts:** See `pipeline/intent_parser.py` (INTENT_PROMPT) and `pipeline/ranker.py` (RANKER_PROMPT) — both committed in full.
