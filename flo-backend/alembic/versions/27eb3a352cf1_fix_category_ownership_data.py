"""fix_category_ownership_data

Revision ID: 27eb3a352cf1
Revises: d766ea812916
Create Date: 2026-08-12 17:10:14.384420

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '27eb3a352cf1'
down_revision: Union[str, Sequence[str], None] = 'd766ea812916'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    session = sa.orm.Session(bind=bind)

    # We need to use raw SQL with SQLAlchemy to avoid importing models which might change
    # Find transactions where transaction.user_id != category.user_id
    mismatched = bind.execute(sa.text("""
        SELECT t.id as tx_id, t.user_id as tx_user_id, c.name, c.keywords, c.monthly_limit
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        WHERE t.user_id != c.user_id
    """)).fetchall()

    for row in mismatched:
        tx_id, tx_user_id, cat_name, cat_keywords, cat_monthly_limit = row
        
        # Check if the correct category already exists for this user
        existing_cat = bind.execute(sa.text("""
            SELECT id FROM categories WHERE user_id = :user_id AND name = :name
        """), {"user_id": tx_user_id, "name": cat_name}).fetchone()

        if existing_cat:
            new_cat_id = existing_cat[0]
        else:
            # Create the category for this user
            result = bind.execute(sa.text("""
                INSERT INTO categories (name, keywords, monthly_limit, user_id)
                VALUES (:name, :keywords, :monthly_limit, :user_id)
                RETURNING id
            """), {
                "name": cat_name,
                "keywords": cat_keywords,
                "monthly_limit": cat_monthly_limit,
                "user_id": tx_user_id
            })
            new_cat_id = result.fetchone()[0]

        # Update the transaction to point to the correct category
        bind.execute(sa.text("""
            UPDATE transactions SET category_id = :category_id WHERE id = :tx_id
        """), {"category_id": new_cat_id, "tx_id": tx_id})
    
    session.commit()


def downgrade() -> None:
    """Downgrade schema."""
    pass
