import os
import json
import logging
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


class ParsedTransaction(BaseModel):
    amount: Optional[float] = Field(
        default=None,
        description="Numerical transaction amount in currency units, e.g. 350.0. Null if amount is missing or invalid."
    )
    type: str = Field(
        default="Expense",
        description="Type of transaction: 'Expense' or 'Income'."
    )
    description: str = Field(
        default="",
        description="Clean, meaningful description or merchant name extracted from text, e.g. 'cycle tire puncher'."
    )
    transaction_date: str = Field(
        description="ISO formatted date string (YYYY-MM-DD) derived from input relative to reference_date."
    )
    confidence: float = Field(
        default=0.0,
        description="Confidence score between 0.0 and 1.0."
    )
    needs_clarification: bool = Field(
        default=False,
        description="True if critical information (such as amount) is missing or ambiguous."
    )
    clarification_reason: Optional[str] = Field(
        default=None,
        description="Explanation of what information is missing or ambiguous."
    )


class TransactionParser:
    DEFAULT_MODEL = "gemini-2.0-flash"

    @classmethod
    def parse(
        cls, 
        text: str, 
        reference_date: Optional[date] = None,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None
    ) -> ParsedTransaction:
        ref_date = reference_date or date.today()
        ref_date_str = ref_date.strftime("%Y-%m-%d")
        ref_weekday_str = ref_date.strftime("%A")

        if not text or not text.strip():
            return ParsedTransaction(
                amount=None,
                type="Expense",
                description="",
                transaction_date=ref_date_str,
                confidence=0.0,
                needs_clarification=True,
                clarification_reason="Empty input text provided."
            )

        key = api_key or os.getenv("GEMINI_API_KEY")
        if not key:
            logger.warning("GEMINI_API_KEY not configured. Natural language transaction parsing unavailable.")
            return ParsedTransaction(
                amount=None,
                type="Expense",
                description=text.strip(),
                transaction_date=ref_date_str,
                confidence=0.0,
                needs_clarification=True,
                clarification_reason="GEMINI_API_KEY not configured."
            )

        model = model_name or os.getenv("LLM_MODEL", cls.DEFAULT_MODEL)

        prompt = f"""You are an expert financial transaction extraction parser.

Analyze the user's natural language transaction message and extract structured transaction details.

Input Text: "{text}"
Reference Current Date: {ref_date_str} ({ref_weekday_str})

Instructions:
1. Extract numerical amount. If currency symbols like ₹, $, € appear, parse the numeric value. If amount is missing or unclear (e.g. "spent some money"), set amount to null, needs_clarification to true, and specify clarification_reason (e.g. "Amount missing").
2. Determine transaction type: "Expense" (e.g. spent, paid, bought) or "Income" (e.g. got salary, received, earned).
3. Extract clean description summarizing what the money was spent on or received for.
4. Calculate transaction_date in YYYY-MM-DD format based on Reference Current Date:
   - "today" -> {ref_date_str}
   - "yesterday" -> 1 day before {ref_date_str}
   - relative days like "last Friday", "2 days ago" -> compute exact YYYY-MM-DD.
   - explicit dates like "August 5" -> compute YYYY-MM-DD using reference date year unless stated otherwise.
   - if no date expression is mentioned, default to {ref_date_str}.
5. Assign a confidence score between 0.0 and 1.0.
6. Do NOT generate code, SQL, or database commands. Return strictly JSON matching the required schema.
"""

        try:
            client = genai.Client(api_key=key)
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ParsedTransaction,
                    temperature=0.1
                )
            )

            if hasattr(response, "parsed") and response.parsed:
                parsed_res = response.parsed
                if isinstance(parsed_res, ParsedTransaction):
                    return cls._post_process(parsed_res, ref_date_str)

            raw_text = getattr(response, "text", None)
            if raw_text:
                data = json.loads(raw_text)
                res = ParsedTransaction(**data)
                return cls._post_process(res, ref_date_str)

            return ParsedTransaction(
                amount=None,
                type="Expense",
                description=text.strip(),
                transaction_date=ref_date_str,
                confidence=0.0,
                needs_clarification=True,
                clarification_reason="LLM returned empty response."
            )

        except Exception as e:
            logger.error(f"TransactionParser error: {e}")
            return ParsedTransaction(
                amount=None,
                type="Expense",
                description=text.strip(),
                transaction_date=ref_date_str,
                confidence=0.0,
                needs_clarification=True,
                clarification_reason=f"Parser error: {str(e)}"
            )

    @staticmethod
    def _post_process(res: ParsedTransaction, default_date_str: str) -> ParsedTransaction:
        # Enforce needs_clarification if amount is missing
        if res.amount is None or res.amount <= 0:
            res.needs_clarification = True
            if not res.clarification_reason:
                res.clarification_reason = "Transaction amount is missing or invalid."
            res.confidence = min(res.confidence, 0.4)

        if not res.transaction_date:
            res.transaction_date = default_date_str

        return res
