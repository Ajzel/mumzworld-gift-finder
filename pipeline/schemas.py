from pydantic import BaseModel, Field, field_validator
from typing import Optional


class GiftIntent(BaseModel):
    child_age_months: Optional[int] = Field(None)
    budget_aed: Optional[float] = Field(None)
    occasion: Optional[str] = Field(None)
    preferences: list[str] = Field(default_factory=list)
    query_language: str = Field(default="en")
    is_for_mom: bool = Field(default=False)

    @field_validator("query_language")
    @classmethod
    def validate_language(cls, v):
        if v not in ("en", "ar"):
            raise ValueError("query_language must be 'en' or 'ar'")
        return v


class GiftRecommendation(BaseModel):
    product_id: str
    name_en: str
    name_ar: str
    price_aed: float
    reason_en: str
    reason_ar: str
    confidence: float = Field(ge=0.0, le=1.0)
    age_suitable: bool
    within_budget: bool


class GiftFinderResponse(BaseModel):
    query: str
    intent: GiftIntent
    recommendations: list[GiftRecommendation] = Field(default_factory=list)
    no_match_reason: Optional[str] = Field(None)
    response_language: str = Field(default="en")

    @field_validator("recommendations")
    @classmethod
    def validate_recommendations(cls, v):
        if len(v) > 3:
            raise ValueError("Maximum 3 recommendations allowed")
        return v