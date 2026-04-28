import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from pipeline.schemas import GiftIntent

load_dotenv()
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

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


MODELS = [
    "google/gemma-3-27b-it:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "google/gemma-3-12b-it:free",
    "nousresearch/hermes-3-llama-3.1-405b:free",
    "google/gemma-3-4b-it:free",
]


def parse_intent(query: str) -> GiftIntent:
    prompt = INTENT_PROMPT.format(query=query)
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
            return GiftIntent(**data)
        except Exception as e:
            last_error = e
            continue
    raise ValueError(f"All models failed. Last error: {last_error}")