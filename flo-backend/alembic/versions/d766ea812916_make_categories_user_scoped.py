"""make_categories_user_scoped

Revision ID: d766ea812916
Revises: 84445d5dd00a
Create Date: 2026-08-09 16:11:38.491799

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd766ea812916'
down_revision: Union[str, Sequence[str], None] = '84445d5dd00a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Add user_id column as nullable first to allow data backfilling
    op.add_column('categories', sa.Column('user_id', sa.Integer(), nullable=True))
    
    # 2. Backfill existing categories safely without losing data
    bind = op.get_bind()
    # Backfill category user_id from linked transactions if any exist
    bind.execute(sa.text("""
        UPDATE categories c
        SET user_id = sub.user_id
        FROM (
            SELECT category_id, MIN(user_id) AS user_id
            FROM transactions
            WHERE category_id IS NOT NULL
            GROUP BY category_id
        ) sub
        WHERE c.id = sub.category_id AND c.user_id IS NULL;
    """))

    # Backfill remaining orphan categories to the first registered user
    bind.execute(sa.text("""
        UPDATE categories
        SET user_id = (SELECT id FROM users ORDER BY id LIMIT 1)
        WHERE user_id IS NULL AND (SELECT COUNT(*) FROM users) > 0;
    """))

    # If categories still exist without user_id (e.g., categories exist but no users exist), delete unowned orphan categories
    bind.execute(sa.text("""
        DELETE FROM categories WHERE user_id IS NULL;
    """))

    # 3. Enforce nullable=False now that all existing rows have valid user_id
    op.alter_column('categories', 'user_id', existing_type=sa.Integer(), nullable=False)

    # 4. Drop global name unique constraint and create composite unique constraint + foreign key
    op.drop_constraint('categories_name_key', 'categories', type_='unique')
    op.create_unique_constraint('uq_user_category_name', 'categories', ['user_id', 'name'])
    op.create_foreign_key('fk_categories_user_id_users', 'categories', 'users', ['user_id'], ['id'], ondelete='CASCADE')


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_categories_user_id_users', 'categories', type_='foreignkey')
    op.drop_constraint('uq_user_category_name', 'categories', type_='unique')
    op.create_unique_constraint('categories_name_key', 'categories', ['name'])
    op.drop_column('categories', 'user_id')
