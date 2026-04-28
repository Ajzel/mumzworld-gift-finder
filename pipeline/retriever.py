import json
import os
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from pipeline.schemas import GiftIntent

_model = SentenceTransformer("all-MiniLM-L6-v2")
_index = None
_products = []


def _build_index():
    global _index, _products

    catalog_path = os.path.join(
        os.path.dirname(__file__), "..", "data", "catalog.json"
    )
    with open(catalog_path, "r", encoding="utf-8") as f:
        _products = json.load(f)

    texts = []
    for p in _products:
        blob = (
            f"{p['name']}. {p['description']}. "
            f"Category: {p['category']}. "
            f"Tags: {', '.join(p['tags'])}. "
            f"Age: {p['age_min_months']} to {p['age_max_months']} months."
        )
        texts.append(blob)

    embeddings = _model.encode(texts, show_progress_bar=False)
    embeddings = np.array(embeddings, dtype="float32")
    faiss.normalize_L2(embeddings)

    dim = embeddings.shape[1]
    _index = faiss.IndexFlatIP(dim)
    _index.add(embeddings)


def retrieve(intent: GiftIntent, top_k: int = 10) -> list[dict]:
    global _index, _products

    if _index is None:
        _build_index()

    query_parts = []
    if intent.child_age_months is not None:
        query_parts.append(f"gift for {intent.child_age_months} month old baby")
    if intent.is_for_mom:
        query_parts.append("gift for new mother mom")
    if intent.occasion:
        query_parts.append(intent.occasion)
    if intent.preferences:
        query_parts.append(" ".join(intent.preferences))
    if not query_parts:
        query_parts.append("baby gift")

    query_text = " ".join(query_parts)

    query_vec = _model.encode([query_text], show_progress_bar=False)
    query_vec = np.array(query_vec, dtype="float32")
    faiss.normalize_L2(query_vec)

    scores, indices = _index.search(query_vec, top_k)

    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx == -1:
            continue
        product = dict(_products[idx])
        product["similarity_score"] = float(score)
        product["within_budget"] = (
            intent.budget_aed is None
            or product["price_aed"] <= intent.budget_aed
        )
        product["age_suitable"] = (
            intent.child_age_months is None
            or (
                product["age_min_months"] <= intent.child_age_months
                <= product["age_max_months"]
            )
        )
        results.append(product)

    return results