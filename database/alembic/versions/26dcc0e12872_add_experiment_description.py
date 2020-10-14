"""Add experiment description

Revision ID: 26dcc0e12872
Revises: c83ac04855b4
Create Date: 2020-10-13 09:04:25.881798

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '26dcc0e12872'
down_revision = 'c83ac04855b4'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('experiment', sa.Column(
        'description', sa.UnicodeText(), nullable=True))


def downgrade():
    op.drop_column('experiment', 'description')
