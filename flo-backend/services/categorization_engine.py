import re
from typing import List, Optional
from dataclasses import dataclass
from models import Category

CONFIDENCE_THRESHOLD = 0.8


@dataclass
class CategorizationResult:
    category_id: Optional[int]
    category_name: Optional[str]
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
        user_categories: List[Category]
    ) -> CategorizationResult:
        normalized_desc = cls._normalize_text(description)
        if not normalized_desc or not user_categories:
            return CategorizationResult(
                category_id=None,
                category_name=None,
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

        if not candidates:
            return CategorizationResult(
                category_id=None,
                category_name=None,
                confidence_score=0.0,
                is_confident=False,
                reason="No confident match found among user categories."
            )

        # Sort candidates by score descending, then keyword length descending
        candidates.sort(key=lambda c: (c["score"], c["kw_len"]), reverse=True)

        top_match = candidates[0]
        top_score = top_match["score"]
        
        # Check for ambiguity: different categories matching with identical top score
        tied_categories = {c["category"].id for c in candidates if c["score"] == top_score}
        if len(tied_categories) > 1 and top_score >= CONFIDENCE_THRESHOLD:
            cat_names = list({c["category"].name for c in candidates if c["score"] == top_score})
            return CategorizationResult(
                category_id=None,
                category_name=None,
                confidence_score=0.5,
                is_confident=False,
                reason=f"Ambiguous keyword match between categories: {', '.join(cat_names)}"
            )

        is_confident = top_score >= CONFIDENCE_THRESHOLD
        reason = f"Matched keyword '{top_match['keyword']}' in category '{top_match['category'].name}' ({top_match['match_type']} match)"

        return CategorizationResult(
            category_id=top_match["category"].id if is_confident else None,
            category_name=top_match["category"].name if is_confident else None,
            confidence_score=top_score,
            is_confident=is_confident,
            reason=reason
        )
