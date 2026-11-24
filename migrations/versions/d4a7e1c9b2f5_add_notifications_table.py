"""add notifications table

Revision ID: d4a7e1c9b2f5
Revises: c5e8a1f3b7d2
Create Date: 2026-11-23 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd4a7e1c9b2f5'
down_revision: Union[str, Sequence[str], None] = 'c5e8a1f3b7d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('notifications',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
    sa.Column('user_id', sa.BigInteger(), nullable=False),
    sa.Column('actor_id', sa.BigInteger(), nullable=False),
    sa.Column('post_id', sa.BigInteger(), nullable=False),
    sa.Column('comment_id', sa.BigInteger(), nullable=False),
    sa.Column('kind', sa.String(length=30), nullable=False),
    sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("kind IN ('new_comment')", name=op.f('ck_notifications_kind')),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_notifications_user_id_users'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['actor_id'], ['users.id'], name=op.f('fk_notifications_actor_id_users'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['post_id'], ['posts.id'], name=op.f('fk_notifications_post_id_posts'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['comment_id'], ['comments.id'], name=op.f('fk_notifications_comment_id_comments'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_notifications'))
    )
    op.create_index('idx_notifications_user_id_created_at', 'notifications', ['user_id', sa.literal_column('created_at DESC')], unique=False)


def downgrade() -> None:
    op.drop_index('idx_notifications_user_id_created_at', table_name='notifications')
    op.drop_table('notifications')
