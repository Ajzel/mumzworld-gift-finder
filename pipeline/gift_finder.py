from pipeline.intent_parser import parse_intent
from pipeline.retriever import retrieve
from pipeline.ranker import rank_products
from pipeline.formatter import build_response
from pipeline.schemas import GiftFinderResponse


def run(query: str) -> GiftFinderResponse:
    intent = parse_intent(query)
    candidates = retrieve(intent, top_k=10)
    recommendations = rank_products(intent, candidates)
    response = build_response(query, intent, recommendations, candidates)
    return response