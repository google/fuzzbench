"""Add experiment type

Revision ID: 5f03d8df1e6e
Revises: 26dcc0e12872
Create Date: 2020-10-15 09:42:44.993253

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5f03d8df1e6e'
down_revision = '26dcc0e12872'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('experiment', sa.Column('type', sa.String(), nullable=True))


def downgrade():
    op.drop_column('experiment', 'type')
