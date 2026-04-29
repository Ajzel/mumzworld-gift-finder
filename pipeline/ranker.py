import os
import json
from openai import OpenAI
from google import genai
from dotenv import load_dotenv
from pipeline.schemas import GiftIntent, GiftRecommendation

load_dotenv()

openrouter_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)
gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

RANKER_PROMPT = """
You are a gift advisor for Mumzworld, a baby and mother e-commerce platform in the Middle East.
Given a parsed gift intent and candidate products, select the best 1-3 gifts.

Intent: {intent}
Candidates: {candidates}

Rules:
- You MUST recommend products from the candidates list. Do not return empty array unless ZERO candidates are provided.
- Only recommend products where age_suitable is true AND within_budget is true.
- confidence: float 0.0-1.0.
- reason_en: 1-2 warm natural English sentences.
- reason_ar: 1-2 sentences in native Arabic, not a translation.
- Never invent product details not in the candidates list.
- Return ONLY a valid JSON array. No markdown, no backticks, no explanation.

Format:
[{{"product_id":"...","name_en":"...","name_ar":"...","price_aed":0.0,"reason_en":"...","reason_ar":"...","confidence":0.0,"age_suitable":true,"within_budget":true}}]
"""

OPENROUTER_MODELS = [
    "google/gemma-3-27b-it:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "google/gemma-3-12b-it:free",
    "nousresearch/hermes-3-llama-3.1-405b:free",
    "google/gemma-3-4b-it:free",
]


def _parse_raw(raw: str):
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()
    data = json.loads(raw)
    if isinstance(data, list) and len(data) > 0:
        return data
    return None


def rank_products(intent: GiftIntent, candidates: list) -> list:
    eligible = [c for c in candidates if c["age_suitable"] and c["within_budget"]]
    if not eligible:
        return []

    if intent.child_age_months is not None and intent.child_age_months > 96:
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

    # Try Gemini first
    try:
        response = gemini_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        )
        data = _parse_raw(response.text)
        if data:
            return [GiftRecommendation(**item) for item in data[:3]]
    except Exception:
        pass

    # Fallback: OpenRouter models
    for model in OPENROUTER_MODELS:
        try:
            response = openrouter_client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
            )
            data = _parse_raw(response.choices[0].message.content)
            if data:
                return [GiftRecommendation(**item) for item in data[:3]]
        except Exception:
            continue

    # Hard fallback: pick top 2 by similarity score
    fallback = sorted(eligible, key=lambda x: x.get("similarity_score", 0), reverse=True)[:2]
    results = []
    for c in fallback:
        results.append(GiftRecommendation(
            product_id=c["id"],
            name_en=c["name"],
            name_ar=c["name_ar"],
            price_aed=c["price_aed"],
            reason_en=f"This {c['category']} product is suitable for a {c['age_min_months']}-{c['age_max_months']} month old and fits your budget.",
            reason_ar=f"هذا المنتج مناسب للأطفال من {c['age_min_months']} إلى {c['age_max_months']} شهراً ويتناسب مع ميزانيتك.",
            confidence=round(c.get("similarity_score", 0.7), 2),
            age_suitable=True,
            within_budget=True,
        ))
    return results