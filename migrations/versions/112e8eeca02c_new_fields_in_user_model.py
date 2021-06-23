"""new fields in user model

Revision ID: 112e8eeca02c
Revises: 988e04d91b93
Create Date: 2020-11-20 11:49:07.419251

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '112e8eeca02c'
down_revision = '988e04d91b93'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('user', sa.Column('about_me', sa.String(length=140), nullable=True))
    op.add_column('user', sa.Column('last_seen', sa.DateTime(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('user', 'last_seen')
    op.drop_column('user', 'about_me')
    # ### end Alembic commands ###