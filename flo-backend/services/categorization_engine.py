import re
from typing import List, Optional
from dataclasses import dataclass
from models import Category
from services.llm_categorizer import LLMCategorizer, LLMCategorizationResponse

CONFIDENCE_THRESHOLD = 0.8


@dataclass
class CategorizationResult:
    category_id: Optional[int]
    category_name: Optional[str]
    proposed_category_name: Optional[str]
    confidence_score: float
    is_confident: bool
    reason: str


class CategorizationEngine:
    @staticmethod
    def _normalize_text(text: str) -> str:
        if not text:
            return ""
        # Lowercase, replace non-alphanumeric characters (except spaces) with space
        cleaned = re.sub(r'[^\w\s]', ' ', text.lower())
        # Collapse multiple spaces
        return ' '.join(cleaned.split())

    @staticmethod
    def _extract_keywords(keywords_str: Optional[str]) -> List[str]:
        if not keywords_str:
            return []
        # Split by comma, semicolon, newline
        raw_list = re.split(r'[,;\n]', keywords_str)
        keywords = []
        for raw in raw_list:
            cleaned = CategorizationEngine._normalize_text(raw)
            if cleaned:
                keywords.append(cleaned)
        return keywords

    @classmethod
    def categorize(
        cls, 
        description: str, 
        user_categories: List[Category],
        use_llm_fallback: bool = True
    ) -> CategorizationResult:
        normalized_desc = cls._normalize_text(description)
        if not normalized_desc or not user_categories:
            return CategorizationResult(
                category_id=None,
                category_name=None,
                proposed_category_name=None,
                confidence_score=0.0,
                is_confident=False,
                reason="No input description or no user categories available."
            )

        desc_words = set(normalized_desc.split())
        candidates = []

        for category in user_categories:
            keywords = cls._extract_keywords(category.keywords)
            for kw in keywords:
                kw_words = kw.split()
                # 1. Exact Phrase Match (multi-word keyword in description)
                if len(kw_words) > 1 and kw in normalized_desc:
                    candidates.append({
                        "category": category,
                        "keyword": kw,
                        "score": 1.0,
                        "match_type": "exact_phrase",
                        "kw_len": len(kw)
                    })
                # 2. Exact Word Match (single-word keyword matching exact word token)
                elif len(kw_words) == 1 and kw in desc_words:
                    candidates.append({
                        "category": category,
                        "keyword": kw,
                        "score": 0.95,
                        "match_type": "exact_word",
                        "kw_len": len(kw)
                    })
                # 3. Substring / Partial Match (min keyword length 4 to avoid noise)
                elif len(kw) >= 4 and any(kw in word or word in kw for word in desc_words if len(word) >= 4):
                    candidates.append({
                        "category": category,
                        "keyword": kw,
                        "score": 0.5,
                        "match_type": "partial",
                        "kw_len": len(kw)
                    })

        if candidates:
            candidates.sort(key=lambda c: (c["score"], c["kw_len"]), reverse=True)
            top_match = candidates[0]
            top_score = top_match["score"]
            tied_categories = {c["category"].id for c in candidates if c["score"] == top_score}

            if top_score >= CONFIDENCE_THRESHOLD and len(tied_categories) == 1:
                return CategorizationResult(
                    category_id=top_match["category"].id,
                    category_name=top_match["category"].name,
                    proposed_category_name=None,
                    confidence_score=top_score,
                    is_confident=True,
                    reason=f"Matched keyword '{top_match['keyword']}' in category '{top_match['category'].name}' ({top_match['match_type']} match)"
                )

        # Deterministic match was not confident; fall back to LLM if enabled
        if not use_llm_fallback:
            return CategorizationResult(
                category_id=None,
                category_name=None,
                proposed_category_name=None,
                confidence_score=0.0,
                is_confident=False,
                reason="No confident deterministic match found."
            )

        llm_res: LLMCategorizationResponse = LLMCategorizer.categorize(description, user_categories)
        
        # If LLM selected an existing category ID
        if llm_res.category_id is not None:
            matched_cat = next((c for c in user_categories if c.id == llm_res.category_id), None)
            if matched_cat:
                is_conf = llm_res.confidence >= CONFIDENCE_THRESHOLD
                return CategorizationResult(
                    category_id=matched_cat.id if is_conf else None,
                    category_name=matched_cat.name if is_conf else None,
                    proposed_category_name=None,
                    confidence_score=llm_res.confidence,
                    is_confident=is_conf,
                    reason=f"LLM fallback selected category '{matched_cat.name}': {llm_res.reason}"
                )

        # If LLM proposed a new category
        if llm_res.proposed_category_name:
            return CategorizationResult(
                category_id=None,
                category_name=None,
                proposed_category_name=llm_res.proposed_category_name,
                confidence_score=llm_res.confidence,
                is_confident=False,
                reason=f"LLM proposed new category '{llm_res.proposed_category_name}': {llm_res.reason}"
            )

        return CategorizationResult(
            category_id=None,
            category_name=None,
            proposed_category_name=None,
            confidence_score=llm_res.confidence,
            is_confident=False,
            reason=f"LLM could not determine category: {llm_res.reason}"
        )
