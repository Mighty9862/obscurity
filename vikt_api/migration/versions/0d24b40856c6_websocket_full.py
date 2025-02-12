"""WebSocket full

Revision ID: 0d24b40856c6
Revises: 2fc10aa00f9c
Create Date: 2025-02-13 01:56:11.732279

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0d24b40856c6'
down_revision: Union[str, None] = '2fc10aa00f9c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('gamestatus',
    sa.Column('sections', sa.Text(), nullable=True),
    sa.Column('current_section_index', sa.Integer(), nullable=True),
    sa.Column('current_question', sa.Text(), nullable=True),
    sa.Column('answer_for_current_question', sa.Text(), nullable=True),
    sa.Column('current_question_image', sa.String(length=1000), nullable=False),
    sa.Column('current_answer_image', sa.String(length=1000), nullable=False),
    sa.Column('game_started', sa.Boolean(), nullable=True),
    sa.Column('game_over', sa.Boolean(), nullable=True),
    sa.Column('spectator_display_mode', sa.Text(), nullable=True),
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.add_column('answers', sa.Column('question', sa.Text(), nullable=False))
    op.add_column('answers', sa.Column('username', sa.String(length=255), nullable=True))
    op.alter_column('answers', 'answer',
               existing_type=sa.VARCHAR(length=255),
               type_=sa.Text(),
               existing_nullable=False)
    op.drop_constraint('answers_question_id_fkey', 'answers', type_='foreignkey')
    op.drop_constraint('answers_user_id_fkey', 'answers', type_='foreignkey')
    op.drop_column('answers', 'user_id')
    op.drop_column('answers', 'question_id')
    op.add_column('questions', sa.Column('section', sa.String(length=1000), nullable=False))
    op.drop_column('questions', 'chapter')
    op.alter_column('users', 'username',
               existing_type=sa.VARCHAR(length=12),
               type_=sa.String(length=100),
               existing_nullable=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('users', 'username',
               existing_type=sa.String(length=100),
               type_=sa.VARCHAR(length=12),
               existing_nullable=False)
    op.add_column('questions', sa.Column('chapter', sa.VARCHAR(length=1000), autoincrement=False, nullable=False))
    op.drop_column('questions', 'section')
    op.add_column('answers', sa.Column('question_id', sa.INTEGER(), autoincrement=False, nullable=False))
    op.add_column('answers', sa.Column('user_id', sa.INTEGER(), autoincrement=False, nullable=True))
    op.create_foreign_key('answers_user_id_fkey', 'answers', 'users', ['user_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('answers_question_id_fkey', 'answers', 'questions', ['question_id'], ['id'], ondelete='CASCADE')
    op.alter_column('answers', 'answer',
               existing_type=sa.Text(),
               type_=sa.VARCHAR(length=255),
               existing_nullable=False)
    op.drop_column('answers', 'username')
    op.drop_column('answers', 'question')
    op.drop_table('gamestatus')
    # ### end Alembic commands ###
