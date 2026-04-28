# TRADEOFFS.md

## Why this problem

Gift discovery is a high-intent, high-AOV moment on Mumzworld. A mom searching for a baby shower gift is ready to buy — she just needs confidence that the product fits the child's age, her budget, and the occasion. The current catalog search is keyword-based: if she types "thoughtful gift for a 6-month-old under 200 AED" she gets zero results or irrelevant ones. This is a direct revenue leak.

The gift finder solves this with natural language understanding + semantic retrieval. It also handles Arabic natively, which matters because a significant portion of Mumzworld's GCC customer base searches and thinks in Arabic, not English.

**Why this over the other options:**

| Problem | Why I passed |
|---|---|
| Return reason classifier | Strong eval story but low creativity — straightforward classification with no retrieval component |
| Review synthesizer | Interesting but requires real review data; mock data weakens the demo significantly |
| Product comparison blog | Hard to eval rigorously in 5 hours; Arabic blog quality is difficult to assert |
| CS email triage | No multilingual complexity; lower business leverage than gift discovery |

The gift finder has the best combination of: real revenue impact, genuine AI engineering challenge (RAG + structured output + multilingual), and a demo that immediately makes sense to any evaluator.

---

## Architecture decisions

**Why FAISS over a hosted vector DB (Pinecone, Weaviate):**
FAISS runs locally with zero cost and zero latency overhead. For a 50-product catalog it is more than sufficient. A hosted DB would add setup complexity and a paid dependency without improving result quality at this scale. In production at 250K+ products, the switch to a hosted DB is straightforward — the retriever interface doesn't change.

**Why two LLM calls instead of one:**
Separating intent parsing from ranking makes each call simpler and easier to debug. A single prompt that does both parsing and ranking becomes hard to control — the model has to simultaneously understand the query and evaluate products against it. Two focused prompts with clear schemas produce more reliable JSON output and make failure attribution obvious: if intent is wrong, the parser failed; if ranking is wrong, the ranker failed.

**Why Pydantic for schema validation:**
LLMs return malformed JSON occasionally, especially smaller free-tier models. Without schema validation, a missing field or wrong type silently corrupts the response. Pydantic raises explicitly, which means failures surface immediately rather than causing confusing downstream errors. It also self-documents the output contract.

**Why OpenRouter over direct Gemini/OpenAI:**
OpenRouter gives a single API with a fallback chain across multiple free models. When one model is rate-limited, the pipeline automatically tries the next. This was critical during development — free tier limits hit frequently when testing.

**Why Streamlit over FastAPI + React:**
The brief asks for a 3-minute Loom showing 5 inputs end to end. Streamlit delivers a working bilingual UI in ~50 lines of code. A React frontend would take 2-3x longer to build and add no evaluation value. The time saved went into evals and documentation.

---

## What I cut and why

**Product image support:** The brief mentions multimodal as a possible component. I cut it because the core gift finder already satisfies the "at least two AI engineering techniques" requirement (RAG + structured output + evals) and adding image input would require product images in the mock catalog that don't exist. It would have been cosmetic complexity.

**Conversation memory / follow-up queries:** A real gift finder would support "show me something cheaper" as a follow-up. Cut because it would double the UI complexity and the brief scope is a single-turn demo.

**Personalization from purchase history:** Would meaningfully improve recommendation quality but requires user data infrastructure that doesn't exist in a 5-hour prototype.

**Fine-tuning for Arabic quality:** The ranker prompt produces good Arabic with large models but weaker Arabic with small fallback models. Fine-tuning a small model on Arabic product descriptions would fix this. Cut for time.

---

## What I would build next

1. **Arabizi support** — many GCC users type Arabic in Latin script (e.g. "hadiya l baby shower"). The intent parser should detect and normalize this before processing.

2. **Confidence-based fallback UI** — if all recommendations have confidence < 0.5, show a "we're not sure, here's what we found" message rather than presenting weak matches with false confidence.

3. **Native Arabic eval** — hire a native Arabic speaker to rate 50 Arabic outputs on a 1-5 fluency scale. The current eval only checks length, not quality.

4. **A/B test harness** — swap the ranker model (gemma-27b vs llama-70b) and measure recommendation click-through rate on a sample of real queries.

5. **Production catalog integration** — replace the 50-product mock with a live Mumzworld catalog API call. The retriever interface is already abstracted — this is a one-file change.

---

## Uncertainty handling approach

The system expresses uncertainty in two ways:

**Structural uncertainty (no match):** When no product passes both age and budget filters, the formatter diagnoses the specific reason (budget too low vs age out of range vs generic mismatch) and returns it in `no_match_reason` in the query's language. The recommendations list is empty — never padded with out-of-budget or age-inappropriate products.

**Confidence scores:** Every recommendation carries a `confidence` float (0.0–1.0) generated by the ranker. This lets the UI surface how strongly the model believes the product fits — a 0.95 match looks different from a 0.6 match. In future, confidence < 0.5 could trigger a "not confident" UI state.

The system never fabricates products. The ranker is explicitly instructed to use only products from the candidate list and never invent details. The FAISS retriever only returns products that exist in `catalog.json`. Schema validation ensures the `product_id` field is always present, making it possible to verify every recommendation against the source catalog.

---

## Time log

| Phase | Time |
|---|---|
| Problem selection + architecture planning | 30 min |
| Catalog data + Pydantic schemas | 45 min |
| Intent parser + FAISS retriever | 60 min |
| Ranker + formatter + pipeline orchestrator | 45 min |
| Streamlit UI | 30 min |
| Debugging (SDK deprecation, model fallbacks, rate limits) | 60 min |
| Evals — writing test cases + runner | 45 min |
| Evals — running + re-running after rate limits | 30 min |
| README + EVALS.md + TRADEOFFS.md | 45 min |
| **Total** | **~6.5 hours** |

Went ~1.5 hours over due to unexpected issues: the `google.generativeai` SDK was deprecated mid-build, Gemini free tier exhausted quickly, and OpenRouter per-minute limits required adding delays to the eval runner. All three issues are documented in the Tooling section of the README.
