import os
import json
from openai import OpenAI
from google import genai
from dotenv import load_dotenv
from pipeline.schemas import GiftIntent

load_dotenv()

openrouter_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)
gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

INTENT_PROMPT = """
You are an intent parser for Mumzworld, a baby and mother e-commerce platform in the Middle East.
Extract structured gift-search intent from the user query below.

Return ONLY a valid JSON object with these exact fields:
{{
  "child_age_months": <integer or null>,
  "budget_aed": <float or null>,
  "occasion": <string or null>,
  "preferences": [<list of keyword strings>],
  "query_language": "<en or ar>",
  "is_for_mom": <true or false>
}}

Rules:
- child_age_months: convert years to months. null if not mentioned.
- budget_aed: extract number from price mentions. null if not mentioned.
- occasion: one of [baby shower, birthday, eid, newborn, just because] or null.
- preferences: extract keywords like educational, sensory, organic, soft, travel.
- query_language: ar if Arabic, else en.
- is_for_mom: true only if gift is clearly for the mother.
- Return null for missing fields. Never invent values.
- Return ONLY raw JSON. No markdown, no backticks.

User query: {query}
"""

OPENROUTER_MODELS = [
    "google/gemma-3-27b-it:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "google/gemma-3-12b-it:free",
    "nousresearch/hermes-3-llama-3.1-405b:free",
    "google/gemma-3-4b-it:free",
]


def parse_intent(query: str) -> GiftIntent:
    prompt = INTENT_PROMPT.format(query=query)

    # Try Gemini first
    try:
        response = gemini_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        )
        raw = response.text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()
        data = json.loads(raw)
        return GiftIntent(**data)
    except Exception:
        pass

    # Fallback: OpenRouter models
    for model in OPENROUTER_MODELS:
        try:
            response = openrouter_client.chat.completions.create(
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
            return GiftIntent(**data)
        except Exception:
            continue

    # Hard fallback: rule-based intent parsing
    import re
    lang = "ar" if any("\u0600" <= c <= "\u06ff" for c in query) else "en"
    is_for_mom = any(w in query.lower() for w in ["mom", "mother", "breastfeed", "pump", "أم", "ماما"])

    age = None
    age_month = re.search(r"(\d+)\s*[-\s]?month", query.lower())
    age_year = re.search(r"(\d+)\s*[-\s]?year", query.lower())
    age_teen = re.search(r"teen", query.lower())
    if age_teen:
        age = 156  # 13 years — forces out-of-range refusal
    elif age_month:
        age = int(age_month.group(1))
    elif age_year:
        age = int(age_year.group(1)) * 12

    budget = None
    budget_match = re.search(r"under\s+(\d+)|(\d+)\s*(aed|درهم|dhs)", query.lower())
    if budget_match:
        val = budget_match.group(1) or budget_match.group(2)
        if val:
            budget = float(val)

    prefs = []
    for kw in ["educational", "sensory", "organic", "soft", "travel", "wooden", "music"]:
        if kw in query.lower():
            prefs.append(kw)

    return GiftIntent(
        child_age_months=age,
        budget_aed=budget,
        occasion=None,
        preferences=prefs,
        query_language=lang,
        is_for_mom=is_for_mom,
    )