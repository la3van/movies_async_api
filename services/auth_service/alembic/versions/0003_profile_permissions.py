"""Read-only profile access; no existing user receives it automatically."""

from alembic import op

revision = "auth_profiles_3"
down_revision = "auth_notifications_2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        INSERT INTO public.permissions(id, code, description)
        VALUES ('6b9f3331-d061-4213-9b52-aa24ef7aa001', 'profiles:read',
                'Read customer profiles in the admin panel')
        ON CONFLICT (code) DO NOTHING
    """)
    op.execute("""
        INSERT INTO public.roles(id, name, description, is_default)
        VALUES ('6b9f3331-d061-4213-9b52-aa24ef7aa002', 'profile_reader',
                'Read-only customer profile access', false)
        ON CONFLICT (name) DO NOTHING
    """)
    op.execute("""
        INSERT INTO public.role_permissions(role_id, permission_id)
        SELECT r.id, p.id FROM public.roles r, public.permissions p
        WHERE r.name = 'profile_reader' AND p.code = 'profiles:read'
        ON CONFLICT DO NOTHING
    """)


def downgrade() -> None:

    pass
