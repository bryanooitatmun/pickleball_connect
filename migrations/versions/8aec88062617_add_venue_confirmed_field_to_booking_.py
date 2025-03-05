"""Add venue_confirmed field to Booking model

Revision ID: 8aec88062617
Revises: 0e2fd56d0751
Create Date: 2025-03-05 07:14:30.847013

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8aec88062617'
down_revision = '0e2fd56d0751'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('booking', schema=None) as batch_op:
        batch_op.add_column(sa.Column('venue_confirmed', sa.Boolean(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('booking', schema=None) as batch_op:
        batch_op.drop_column('venue_confirmed')

    # ### end Alembic commands ###
