from typing import Optional, List
from sqlalchemy.orm import Session
from fastapi import HTTPException

from models import Transaction, Category
from schemas import TransactionCreate


class TransactionService:
    @staticmethod
    def get_user_transactions(
        db: Session, 
        user_id: int, 
        category_id: Optional[int] = None, 
        limit: int = 5
    ) -> List[Transaction]:
        query = db.query(Transaction).filter(Transaction.user_id == user_id)
        if category_id:
            query = query.filter(Transaction.category_id == category_id)
        return query.order_by(Transaction.id.desc()).limit(limit).all()

    @staticmethod
    def create_transaction(db: Session, user_id: int, transaction_data: TransactionCreate) -> Transaction:
        if transaction_data.category_id is not None:
            category = db.query(Category).filter(
                Category.id == transaction_data.category_id,
                Category.user_id == user_id
            ).first()
            if not category:
                raise HTTPException(status_code=400, detail="Invalid category ID or category does not belong to you")

        new_transaction = Transaction(
            amount=transaction_data.amount,
            type=transaction_data.type,
            description=transaction_data.description,
            transaction_date=transaction_data.transaction_date,
            category_id=transaction_data.category_id,
            user_id=user_id
        )
        db.add(new_transaction)
        db.commit()
        db.refresh(new_transaction)
        return new_transaction

    @staticmethod
    def update_transaction(
        db: Session, 
        user_id: int, 
        transaction_id: int, 
        transaction_data: TransactionCreate
    ) -> Transaction:
        transaction_to_update = db.query(Transaction).filter(Transaction.id == transaction_id).first()
        if not transaction_to_update:
            raise HTTPException(status_code=404, detail="Transaction not found")

        if transaction_to_update.user_id != user_id:
            raise HTTPException(status_code=403, detail="You can only edit your own transactions")

        if transaction_data.category_id is not None:
            category = db.query(Category).filter(
                Category.id == transaction_data.category_id,
                Category.user_id == user_id
            ).first()
            if not category:
                raise HTTPException(status_code=400, detail="Invalid category ID or category does not belong to you")

        transaction_to_update.amount = transaction_data.amount
        transaction_to_update.type = transaction_data.type
        transaction_to_update.description = transaction_data.description
        transaction_to_update.transaction_date = transaction_data.transaction_date
        transaction_to_update.category_id = transaction_data.category_id

        db.commit()
        db.refresh(transaction_to_update)
        return transaction_to_update

    @staticmethod
    def delete_transaction(db: Session, user_id: int, transaction_id: int) -> None:
        transaction_to_delete = db.query(Transaction).filter(Transaction.id == transaction_id).first()
        if not transaction_to_delete:
            raise HTTPException(status_code=404, detail="Transaction not found")

        if transaction_to_delete.user_id != user_id:
            raise HTTPException(status_code=403, detail="You can only delete your own transactions")

        db.delete(transaction_to_delete)
        db.commit()
