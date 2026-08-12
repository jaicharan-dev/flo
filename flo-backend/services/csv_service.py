import csv
import io
import re
from datetime import datetime, date
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, UploadFile

from models import Transaction, Category
from services.categorization_engine import CategorizationEngine


class CSVService:
    @staticmethod
    def _parse_amount(raw_amount: Any) -> float:
        if raw_amount is None:
            raise ValueError("Amount is missing")
        # Remove currency symbols, commas, spaces
        cleaned = re.sub(r'[^\d.-]', '', str(raw_amount).strip())
        val = float(cleaned)
        return abs(val)

    @staticmethod
    def _parse_date(raw_date: Any) -> date:
        if not raw_date:
            return date.today()
        date_str = str(raw_date).strip()
        
        # Try common date formats
        formats = [
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%m/%d/%Y",
            "%d-%m-%Y",
            "%Y/%m/%d",
            "%b %d, %Y",
            "%d %b %Y"
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        return date.today()

    @classmethod
    def process_csv_upload(
        cls, 
        db: Session, 
        user_id: int, 
        file: UploadFile
    ) -> Dict[str, Any]:
        if not file.filename.endswith(('.csv', '.txt')):
            raise HTTPException(status_code=400, detail="Only .csv files are supported")

        try:
            content = file.file.read().decode('utf-8-sig')
        except Exception:
            raise HTTPException(status_code=400, detail="Failed to decode CSV file. Ensure UTF-8 encoding.")

        reader = csv.DictReader(io.StringIO(content))
        if not reader.fieldnames:
            raise HTTPException(status_code=400, detail="CSV file appears to be empty or missing headers")

        # Map flexible header names
        header_map = {}
        for original in reader.fieldnames:
            norm = original.strip().lower()
            if norm in ["date", "transaction date", "txn date", "date"]:
                header_map["date"] = original
            elif norm in ["amount", "amt", "value", "transaction amount"]:
                header_map["amount"] = original
            elif norm in ["description", "desc", "narration", "details", "particulars", "remarks"]:
                header_map["description"] = original
            elif norm in ["type", "txn type", "transaction type", "cr/dr"]:
                header_map["type"] = original

        if "amount" not in header_map or "description" not in header_map:
            raise HTTPException(
                status_code=400, 
                detail=f"CSV must contain at least 'amount' and 'description' columns. Found columns: {reader.fieldnames}"
            )

        user_categories = db.query(Category).filter(Category.user_id == user_id).all()

        imported_count = 0
        skipped_count = 0
        errors = []

        for row_num, row in enumerate(reader, start=2):
            try:
                raw_amt = row.get(header_map["amount"])
                raw_desc = row.get(header_map["description"], "")
                raw_date = row.get(header_map.get("date"), "")
                raw_type = row.get(header_map.get("type"), "")

                if not raw_desc or not raw_amt:
                    skipped_count += 1
                    continue

                amount = cls._parse_amount(raw_amt)
                tx_date = cls._parse_date(raw_date)

                # Determine transaction type
                tx_type = "Expense"
                if raw_type:
                    t_lower = str(raw_type).strip().lower()
                    if t_lower in ["income", "cr", "credit", "deposit"]:
                        tx_type = "Income"

                # Auto-categorization
                cat_result = CategorizationEngine.categorize(
                    description=str(raw_desc).strip(),
                    user_categories=user_categories,
                    use_llm_fallback=True
                )
                category_id = cat_result.category_id if cat_result else None

                new_tx = Transaction(
                    amount=amount,
                    type=tx_type,
                    description=str(raw_desc).strip(),
                    transaction_date=tx_date,
                    category_id=category_id,
                    user_id=user_id
                )
                db.add(new_tx)
                imported_count += 1

            except Exception as e:
                skipped_count += 1
                errors.append(f"Row {row_num}: {str(e)}")

        db.commit()

        return {
            "imported_count": imported_count,
            "skipped_count": skipped_count,
            "errors": errors,
            "message": f"Successfully imported {imported_count} transactions ({skipped_count} skipped)."
        }
