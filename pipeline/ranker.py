import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from pipeline.schemas import GiftIntent, GiftRecommendation

load_dotenv()
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

RANKER_PROMPT = """
You are a gift advisor for Mumzworld, a baby and mother e-commerce platform in the Middle East.
Given a parsed gift intent and candidate products, select the best 1-3 gifts.

Intent: {intent}
Candidates: {candidates}

Rules:
- Only recommend products where age_suitable is true AND within_budget is true.
- If none qualify, return empty array [].
- confidence: float 0.0-1.0.
- reason_en: 1-2 warm natural English sentences.
- reason_ar: 1-2 sentences in native Arabic, not a translation.
- Never invent product details.
- Return ONLY a valid JSON array. No markdown, no backticks.

Format:
[{{"product_id":"...","name_en":"...","name_ar":"...","price_aed":0.0,"reason_en":"...","reason_ar":"...","confidence":0.0,"age_suitable":true,"within_budget":true}}]
"""

MODELS = [
    "google/gemma-3-27b-it:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "google/gemma-3-12b-it:free",
    "nousresearch/hermes-3-llama-3.1-405b:free",
    "google/gemma-3-4b-it:free",
]


def rank_products(intent: GiftIntent, candidates: list) -> list:
    eligible = [c for c in candidates if c["age_suitable"] and c["within_budget"]]
    if not eligible:
        return []

    intent_summary = {
        "child_age_months": intent.child_age_months,
        "budget_aed": intent.budget_aed,
        "occasion": intent.occasion,
        "preferences": intent.preferences,
        "is_for_mom": intent.is_for_mom,
    }

    slim = [
        {
            "product_id": c["id"],
            "name_en": c["name"],
            "name_ar": c["name_ar"],
            "price_aed": c["price_aed"],
            "description": c["description"],
            "tags": c["tags"],
            "age_min_months": c["age_min_months"],
            "age_max_months": c["age_max_months"],
            "age_suitable": c["age_suitable"],
            "within_budget": c["within_budget"],
        }
        for c in eligible
    ]

    prompt = RANKER_PROMPT.format(
        intent=json.dumps(intent_summary, ensure_ascii=False),
        candidates=json.dumps(slim, ensure_ascii=False, indent=2),
    )

    last_error = None
    for model in MODELS:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.choices[0].message.content.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            raw = raw.strip()
            data = json.loads(raw)
            return [GiftRecommendation(**item) for item in data[:3]]
        except Exception as e:
            last_error = e
            continue

    raise ValueError(f"All models failed. Last error: {last_error}")