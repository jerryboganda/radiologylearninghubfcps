"""Enforce tenant RLS and runtime grants for the M0 foundation.

Revision ID: 20260924_0002
Revises: 20260924_0001
Create Date: 2026-09-24
"""

from __future__ import annotations

from apps.api.migrations.sql import execute_script

revision = "20260924_0002"
down_revision = "20260924_0001"
branch_labels = None
depends_on = None

_CORE_TENANT_ID = "00000000-0000-0000-0000-000000000001"
_MIGRATOR_ROLE = "radbrain_migrator"
_RUNTIME_ROLE = "radbrain_app"


def upgrade() -> None:
    execute_script(
        f"""
        INSERT INTO tenants (id, kind, name, plan)
        VALUES ('{_CORE_TENANT_ID}'::uuid, 'core', 'Core Library', 'core')
        ON CONFLICT (id) DO NOTHING;

        DO $$
        BEGIN
            IF to_regrole('{_RUNTIME_ROLE}') IS NULL THEN
                RAISE EXCEPTION
                    'required runtime role % must exist before migration', '{_RUNTIME_ROLE}';
            END IF;
            IF to_regrole('{_MIGRATOR_ROLE}') IS NULL THEN
                RAISE EXCEPTION
                    'required migrator role % must exist before migration', '{_MIGRATOR_ROLE}';
            END IF;
            IF current_user <> '{_MIGRATOR_ROLE}' THEN
                RAISE EXCEPTION 'migrations must run as %', '{_MIGRATOR_ROLE}';
            END IF;
            IF current_user = '{_RUNTIME_ROLE}' THEN
                RAISE EXCEPTION 'migrations must not run as runtime role %', '{_RUNTIME_ROLE}';
            END IF;
            IF EXISTS (
                SELECT 1 FROM pg_roles
                WHERE rolname = '{_RUNTIME_ROLE}'
                  AND (rolsuper OR rolbypassrls OR rolcreaterole OR rolcreatedb)
            ) THEN
                RAISE EXCEPTION 'runtime role % has forbidden attributes', '{_RUNTIME_ROLE}';
            END IF;
            IF EXISTS (
                WITH RECURSIVE role_memberships(roleid, member) AS (
                    SELECT roleid, member
                    FROM pg_auth_members
                    UNION
                    SELECT granted.roleid, memberships.member
                    FROM pg_auth_members AS granted
                    JOIN role_memberships AS memberships
                      ON memberships.roleid = granted.member
                )
                SELECT 1
                FROM role_memberships
                JOIN pg_roles AS runtime ON runtime.oid = role_memberships.member
                JOIN pg_roles AS migrator ON migrator.oid = role_memberships.roleid
                WHERE runtime.rolname = '{_RUNTIME_ROLE}'
                  AND migrator.rolname = '{_MIGRATOR_ROLE}'
            ) THEN
                RAISE EXCEPTION
                    'runtime role % inherits migrator role %',
                    '{_RUNTIME_ROLE}', '{_MIGRATOR_ROLE}';
            END IF;
            IF EXISTS (
                WITH RECURSIVE role_memberships(roleid, member) AS (
                    SELECT roleid, member
                    FROM pg_auth_members
                    UNION
                    SELECT granted.roleid, memberships.member
                    FROM pg_auth_members AS granted
                    JOIN role_memberships AS memberships
                      ON memberships.roleid = granted.member
                )
                SELECT 1
                FROM role_memberships
                JOIN pg_roles AS runtime ON runtime.oid = role_memberships.member
                JOIN pg_roles AS privileged ON privileged.oid = role_memberships.roleid
                WHERE runtime.rolname = '{_RUNTIME_ROLE}'
                  AND (privileged.rolsuper OR privileged.rolbypassrls)
            ) THEN
                RAISE EXCEPTION 'runtime role % inherits a privileged role', '{_RUNTIME_ROLE}';
            END IF;
        END
        $$;

        ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;
        ALTER TABLE tenants FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenants_select_own ON tenants
            FOR SELECT USING (id = app.current_tenant_id() AND id <> '{_CORE_TENANT_ID}'::uuid);
        CREATE POLICY tenants_update_own ON tenants
            FOR UPDATE
            USING (id = app.current_tenant_id() AND id <> '{_CORE_TENANT_ID}'::uuid)
            WITH CHECK (id = app.current_tenant_id() AND id <> '{_CORE_TENANT_ID}'::uuid);

        ALTER TABLE users ENABLE ROW LEVEL SECURITY;
        ALTER TABLE users FORCE ROW LEVEL SECURITY;
        CREATE POLICY users_tenant_all ON users
            FOR ALL
            USING (tenant_id = app.current_tenant_id())
            WITH CHECK (tenant_id = app.current_tenant_id());
        CREATE POLICY users_migrator_resolver_read ON users
            FOR SELECT TO radbrain_migrator USING (true);
        """
    )
    execute_script(
        f"""
        ALTER TABLE memberships ENABLE ROW LEVEL SECURITY;
        ALTER TABLE memberships FORCE ROW LEVEL SECURITY;
        CREATE POLICY memberships_tenant_all ON memberships
            FOR ALL USING (tenant_id = app.current_tenant_id())
            WITH CHECK (tenant_id = app.current_tenant_id());
        CREATE POLICY memberships_migrator_resolver_read ON memberships
            FOR SELECT TO radbrain_migrator USING (true);

        ALTER TABLE sources ENABLE ROW LEVEL SECURITY;
        ALTER TABLE sources FORCE ROW LEVEL SECURITY;
        CREATE POLICY sources_select_own_or_core ON sources
            FOR SELECT USING (
                app.current_tenant_id() IS NOT NULL
                AND (
                    tenant_id = app.current_tenant_id()
                    OR (
                        scope = 'core'
                        AND tenant_id = '{_CORE_TENANT_ID}'::uuid
                        AND status = 'ready'
                        AND rights_status IN ('authored', 'licensed')
                        AND deleted_at IS NULL
                    )
                )
            );
        CREATE POLICY sources_insert_own_private ON sources
            FOR INSERT WITH CHECK (
                tenant_id = app.current_tenant_id()
                AND tenant_id <> '{_CORE_TENANT_ID}'::uuid
                AND scope = 'private'
            );
        CREATE POLICY sources_update_own_private ON sources
            FOR UPDATE
            USING (
                tenant_id = app.current_tenant_id()
                AND tenant_id <> '{_CORE_TENANT_ID}'::uuid
                AND scope = 'private'
            ) WITH CHECK (
                tenant_id = app.current_tenant_id()
                AND tenant_id <> '{_CORE_TENANT_ID}'::uuid
                AND scope = 'private'
            );
        CREATE POLICY sources_delete_own_private ON sources
            FOR DELETE USING (
                tenant_id = app.current_tenant_id()
                AND tenant_id <> '{_CORE_TENANT_ID}'::uuid
                AND scope = 'private'
            );
        """
    )
    execute_script(
        f"""
        ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;
        ALTER TABLE jobs FORCE ROW LEVEL SECURITY;
        CREATE POLICY jobs_tenant_all ON jobs
            FOR ALL USING (
                tenant_id = app.current_tenant_id()
                AND tenant_id <> '{_CORE_TENANT_ID}'::uuid
            ) WITH CHECK (
                tenant_id = app.current_tenant_id()
                AND tenant_id <> '{_CORE_TENANT_ID}'::uuid
            );

        ALTER TABLE job_steps ENABLE ROW LEVEL SECURITY;
        ALTER TABLE job_steps FORCE ROW LEVEL SECURITY;
        CREATE POLICY job_steps_tenant_all ON job_steps
            FOR ALL USING (
                tenant_id = app.current_tenant_id()
                AND tenant_id <> '{_CORE_TENANT_ID}'::uuid
            ) WITH CHECK (
                tenant_id = app.current_tenant_id()
                AND tenant_id <> '{_CORE_TENANT_ID}'::uuid
            );

        ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;
        ALTER TABLE audit_log FORCE ROW LEVEL SECURITY;
        CREATE POLICY audit_log_select_tenant ON audit_log
            FOR SELECT USING (
                tenant_id = app.current_tenant_id()
                AND tenant_id <> '{_CORE_TENANT_ID}'::uuid
            );
        CREATE POLICY audit_log_insert_tenant ON audit_log
            FOR INSERT WITH CHECK (
                tenant_id = app.current_tenant_id()
                AND tenant_id <> '{_CORE_TENANT_ID}'::uuid
            );
        """
    )
    execute_script(
        f"""
        REVOKE ALL ON SCHEMA public FROM PUBLIC;
        REVOKE ALL ON ALL TABLES IN SCHEMA public FROM PUBLIC;
        REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM PUBLIC;
        REVOKE ALL ON app.current_tenant_id() FROM PUBLIC;
        REVOKE ALL ON app.touch_updated_at() FROM PUBLIC;
        REVOKE ALL ON FUNCTION app.resolve_memberships(text) FROM PUBLIC;
        GRANT USAGE ON SCHEMA public, app TO {_RUNTIME_ROLE};
        GRANT EXECUTE ON FUNCTION app.current_tenant_id() TO {_RUNTIME_ROLE};
        GRANT EXECUTE ON FUNCTION app.resolve_memberships(text) TO {_RUNTIME_ROLE};
        GRANT SELECT, UPDATE ON tenants TO {_RUNTIME_ROLE};
        GRANT SELECT, INSERT, UPDATE, DELETE ON users, memberships TO {_RUNTIME_ROLE};
        GRANT SELECT, INSERT, UPDATE, DELETE ON sources, jobs, job_steps TO {_RUNTIME_ROLE};
        GRANT SELECT, INSERT ON audit_log TO {_RUNTIME_ROLE};
        GRANT USAGE, SELECT ON SEQUENCE audit_log_id_seq TO {_RUNTIME_ROLE};
        """
    )


def downgrade() -> None:
    execute_script("DROP POLICY IF EXISTS audit_log_insert_tenant ON audit_log")
    execute_script("DROP POLICY IF EXISTS audit_log_select_tenant ON audit_log")
    execute_script("DROP POLICY IF EXISTS job_steps_tenant_all ON job_steps")
    execute_script("DROP POLICY IF EXISTS jobs_tenant_all ON jobs")
    execute_script("DROP POLICY IF EXISTS sources_delete_own_private ON sources")
    execute_script("DROP POLICY IF EXISTS sources_update_own_private ON sources")
    execute_script("DROP POLICY IF EXISTS sources_insert_own_private ON sources")
    execute_script("DROP POLICY IF EXISTS sources_select_own_or_core ON sources")
    execute_script("DROP POLICY IF EXISTS memberships_migrator_resolver_read ON memberships")
    execute_script("DROP POLICY IF EXISTS memberships_tenant_all ON memberships")
    execute_script("DROP POLICY IF EXISTS users_migrator_resolver_read ON users")
    execute_script("DROP POLICY IF EXISTS users_tenant_all ON users")
    execute_script("DROP POLICY IF EXISTS tenants_update_own ON tenants")
    execute_script("DROP POLICY IF EXISTS tenants_select_own ON tenants")
