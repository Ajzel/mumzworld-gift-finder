from pipeline.schemas import GiftFinderResponse, GiftIntent, GiftRecommendation

NO_MATCH = {
    "en": {
        "budget": "No products match your budget and the child's age together. Try increasing your budget.",
        "age": "No products found for this age within your budget. Try adjusting age or budget.",
        "generic": "No matching products found. Try different preferences or a higher budget.",
    },
    "ar": {
        "budget": "لا توجد منتجات تتناسب مع ميزانيتك وعمر الطفل. حاول رفع الميزانية.",
        "age": "لم نجد منتجات مناسبة لهذا العمر ضمن ميزانيتك. جرّب تعديل العمر أو الميزانية.",
        "generic": "لم يتم العثور على منتجات مطابقة. جرّب تفضيلات مختلفة أو ميزانية أعلى.",
    },
}


def build_response(query, intent, recommendations, candidates):
    lang = intent.query_language
    no_match_reason = None

    if not recommendations:
        has_budget = any(c["within_budget"] for c in candidates)
        has_age = any(c["age_suitable"] for c in candidates)
        if not has_budget:
            no_match_reason = NO_MATCH[lang]["budget"]
        elif not has_age:
            no_match_reason = NO_MATCH[lang]["age"]
        else:
            no_match_reason = NO_MATCH[lang]["generic"]

    return GiftFinderResponse(
        query=query,
        intent=intent,
        recommendations=recommendations,
        no_match_reason=no_match_reason,
        response_language=lang,
    )