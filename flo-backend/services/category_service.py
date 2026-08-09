from typing import List
from sqlalchemy.orm import Session
from fastapi import HTTPException

from models import Category
from schemas import CategoryCreate


class CategoryService:
    @staticmethod
    def get_user_categories(db: Session, user_id: int) -> List[Category]:
        return db.query(Category).filter(Category.user_id == user_id).all()

    @staticmethod
    def create_category(db: Session, user_id: int, category_data: CategoryCreate) -> Category:
        existing_category = db.query(Category).filter(
            Category.user_id == user_id,
            Category.name == category_data.name
        ).first()
        if existing_category:
            raise HTTPException(status_code=400, detail="Category with this name already exists for your account")

        new_category = Category(
            name=category_data.name,
            keywords=category_data.keywords,
            monthly_limit=category_data.monthly_limit,
            user_id=user_id
        )
        db.add(new_category)
        db.commit()
        db.refresh(new_category)
        return new_category

    @staticmethod
    def update_category(db: Session, user_id: int, category_id: int, category_data: CategoryCreate) -> Category:
        category = db.query(Category).filter(Category.id == category_id).first()
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")

        if category.user_id != user_id:
            raise HTTPException(status_code=403, detail="You can only edit your own categories")

        existing_category = db.query(Category).filter(
            Category.user_id == user_id,
            Category.name == category_data.name,
            Category.id != category_id
        ).first()
        if existing_category:
            raise HTTPException(status_code=400, detail="Another category with this name already exists for your account")

        category.name = category_data.name
        category.keywords = category_data.keywords
        category.monthly_limit = category_data.monthly_limit

        db.commit()
        db.refresh(category)
        return category

    @staticmethod
    def delete_category(db: Session, user_id: int, category_id: int) -> None:
        category = db.query(Category).filter(Category.id == category_id).first()
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")

        if category.user_id != user_id:
            raise HTTPException(status_code=403, detail="You can only delete your own categories")

        db.delete(category)
        db.commit()
