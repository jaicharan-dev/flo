import os
import json
import logging
from typing import List, Optional
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

from models import Category

logger = logging.getLogger(__name__)


class LLMCategorizationResponse(BaseModel):
    category_id: Optional[int] = Field(
        default=None, 
        description="The ID of an existing category that matches the transaction, or null if no existing category fits."
    )
    proposed_category_name: Optional[str] = Field(
        default=None, 
        description="A concise proposed category name if no existing category fits."
    )
    confidence: float = Field(
        default=0.0,
        description="Confidence score between 0.0 and 1.0."
    )
    reason: str = Field(
        default="",
        description="Explanation for why this existing category was selected or new category proposed."
    )


class LLMCategorizer:
    DEFAULT_MODEL = "gemini-2.0-flash"

    @classmethod
    def categorize(
        cls, 
        description: str, 
        user_categories: List[Category],
        api_key: Optional[str] = None,
        model_name: Optional[str] = None
    ) -> LLMCategorizationResponse:
        key = api_key or os.getenv("GEMINI_API_KEY")
        if not key:
            logger.warning("GEMINI_API_KEY not configured. LLM fallback unavailable.")
            return LLMCategorizationResponse(
                category_id=None,
                proposed_category_name=None,
                confidence=0.0,
                reason="LLM API key not configured."
            )

        model = model_name or os.getenv("LLM_MODEL", cls.DEFAULT_MODEL)

        categories_data = [
            {"id": cat.id, "name": cat.name, "keywords": cat.keywords or ""}
            for cat in user_categories
        ]

        prompt = f"""You are a personal finance assistant. Analyze the given transaction description and categorize it based on the user's existing categories.

Transaction Description: "{description}"

User's Existing Categories:
{json.dumps(categories_data, indent=2)}

Instructions:
1. If one of the existing categories fits the transaction description, select its category_id.
2. If NONE of the existing categories fit, set category_id to null and suggest a clear, concise new category name in proposed_category_name.
3. Assign a confidence score between 0.0 and 1.0.
4. Provide a clear reason explaining your decision.
5. Do NOT output SQL, code, or attempt to modify the database. Return strictly JSON matching the required schema.
"""

        try:
            client = genai.Client(api_key=key)
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=LLMCategorizationResponse,
                    temperature=0.1
                )
            )

            if hasattr(response, "parsed") and response.parsed:
                parsed_res = response.parsed
                if isinstance(parsed_res, LLMCategorizationResponse):
                    return cls._validate_response(parsed_res, user_categories)

            raw_text = getattr(response, "text", None)
            if raw_text:
                data = json.loads(raw_text)
                res = LLMCategorizationResponse(**data)
                return cls._validate_response(res, user_categories)

            return LLMCategorizationResponse(
                category_id=None,
                proposed_category_name=None,
                confidence=0.0,
                reason="LLM returned an empty response."
            )

        except Exception as e:
            logger.error(f"LLMCategorizer error: {e}")
            return LLMCategorizationResponse(
                category_id=None,
                proposed_category_name=None,
                confidence=0.0,
                reason=f"LLM categorizer error: {str(e)}"
            )

    @staticmethod
    def _validate_response(
        res: LLMCategorizationResponse, 
        user_categories: List[Category]
    ) -> LLMCategorizationResponse:
        valid_cat_ids = {c.id for c in user_categories}
        
        # If category_id returned is invalid (does not belong to user categories), invalidate it safely
        if res.category_id is not None and res.category_id not in valid_cat_ids:
            logger.warning(f"LLM returned invalid category_id {res.category_id} not in user categories.")
            return LLMCategorizationResponse(
                category_id=None,
                proposed_category_name=res.proposed_category_name,
                confidence=0.0,
                reason=f"LLM proposed invalid category_id {res.category_id}."
            )
        return res
