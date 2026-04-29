# EVALS.md

## Eval philosophy

The goal is not to prove the system always works — it is to prove we know exactly when and why it fails. Every test case has a declared expectation. A pass means the system behaved as designed. A fail means either a logic bug or a rate-limit interruption, both of which are documented honestly below.

---

## Rubric

A test case **passes** if all of the following hold:

| Check | Description |
|---|---|
| Match expectation | If `expect_match: true`, at least 1 recommendation returned. If `expect_match: false`, 0 recommendations returned. |
| Budget respected | Every returned product's `price_aed` ≤ `expect_max_price` (if specified) |
| Language correct | `intent.query_language` matches `expect_language` |
| Mom intent | `intent.is_for_mom` is True when `expect_is_for_mom: true` |
| Arabic quality | Every `reason_ar` is ≥ 10 characters (guards against empty or stub Arabic) |

---

## Test cases

| ID | Description | Type | expect_match | Budget | Notes |
|---|---|---|---|---|---|
| TC01 | Standard EN — age + budget + preference | Easy | true | 200 AED | Core happy path |
| TC02 | Arabic query — newborn gift | Multilingual | true | 300 AED | Arabic input + Arabic output |
| TC03 | Mom gift — breast pump | Edge | true | 100 AED | is_for_mom detection |
| TC04 | Impossibly low budget (10 AED) | Adversarial | false | 10 AED | No product under 10 AED exists |
| TC05 | Very high age (10-year-old) | Adversarial | false | — | Catalog maxes at ~8 years |
| TC06 | Educational toy — toddler | Easy | true | 150 AED | Mid-range budget |
| TC07 | Arabic — toddler toy with budget | Multilingual | true | 200 AED | Arabic input, age + budget |
| TC08 | Baby shower — no age, no budget | Easy | true | — | Open-ended, should still match |
| TC09 | Teenager gift (out of scope) | Adversarial | false | — | No catalog products for 13+ |
| TC10 | Sensory toy — 3-month-old, tight budget | Edge | true | 80 AED | Tight budget, early age |
| TC11 | Eid gift in Arabic — 8-month-old | Multilingual | true | 250 AED | Occasion + Arabic |
| TC12 | "Cheap gift" under 20 AED | Adversarial | false | 20 AED | Cheapest product is 29 AED |

---

## Results

**Full run score: 12/12 (100%)**

| ID | Status | Recs | Notes |
|---|---|---|---|
| TC01 | ✅ PASS | 2 | Returned age-appropriate, in-budget products |
| TC02 | ✅ PASS | 2 | Arabic query parsed correctly, Arabic reasons generated |
| TC03 | ✅ PASS | 1 | is_for_mom=True detected, breast pump recommended |
| TC04 | ✅ PASS | 0 | Correctly refused — budget too low, no_match_reason returned |
| TC05 | ✅ PASS | 0 | Correctly refused — age out of catalog range |
| TC06 | ✅ PASS | 1 | Educational toddler toy within budget returned |
| TC07 | ✅ PASS | 2 | Arabic input handled, correct products returned |
| TC08 | ✅ PASS | 2 | Open query returned popular gift-tagged products |
| TC09 | ✅ PASS | 0 | Teenager age detected, refused with explicit reason |
| TC10 | ✅ PASS | 2 | Sensory toys under 80 AED found |
| TC11 | ✅ PASS | 2 | Eid occasion + Arabic query handled correctly |
| TC12 | ✅ PASS | 0 | Correctly refused — cheapest product (29 AED) over 20 AED budget |
---

## Known failure modes

**TC11 — Arabic occasion extraction:** The intent parser occasionally misses the occasion field when the Arabic query uses `عيد` (Eid) without explicit budget context. The downstream effect is minor (recommendations still return correctly) but the occasion field comes back null. Fix: add explicit Eid examples to the INTENT_PROMPT few-shot section.

**Rate limits during batch evals:** OpenRouter free tier allows 16 requests/minute and 50/day. Running 12 cases × 2 LLM calls each = 24 calls, which hits the per-minute limit without delays. The 5s sleep between cases resolves per-minute limits; the daily limit requires spreading runs across days or adding credits.

**Arabic reason quality variance:** Smaller fallback models (gemma-3-4b) produce weaker Arabic — sometimes grammatically correct but stylistically stiff. The primary model (gemma-3-27b) consistently produces natural Arabic. The eval guards against empty Arabic but not against low-quality Arabic — a future eval should include a native speaker quality rubric.

---

## What the evals do NOT cover (honest gaps)

- Arabic output fluency beyond length check (no native speaker review automated)
- Hallucinated product details (we guard against this in the prompt but don't assert it in evals)
- Response latency (not measured; would matter in production)
- Edge case: query in mixed Arabic/English (Arabizi) — not tested
