"""Create the M0 tenant-isolated foundation.

Revision ID: 20260924_0001
Revises:
Create Date: 2026-09-24
"""

from __future__ import annotations

from apps.api.migrations.sql import execute_script

revision = "20260924_0001"
down_revision = None
branch_labels = None
depends_on = None

_CORE_TENANT_ID = "00000000-0000-0000-0000-000000000001"
_MIGRATOR_ROLE = "radbrain_migrator"
_RUNTIME_ROLE = "radbrain_app"


def upgrade() -> None:
    execute_script(
        f"""
        DO $$
        BEGIN
            IF to_regrole('{_MIGRATOR_ROLE}') IS NULL
               OR to_regrole('{_RUNTIME_ROLE}') IS NULL THEN
                RAISE EXCEPTION 'required migrator/runtime roles must exist before migration';
            END IF;
            IF current_user <> '{_MIGRATOR_ROLE}' THEN
                RAISE EXCEPTION 'migrations must run as %', '{_MIGRATOR_ROLE}';
            END IF;
        END
        $$;
        """
    )
    execute_script("CREATE EXTENSION IF NOT EXISTS vector")
    execute_script("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    execute_script(
        """
        CREATE SCHEMA IF NOT EXISTS app;

        CREATE FUNCTION app.current_tenant_id()
        RETURNS uuid
        LANGUAGE sql
        STABLE
        PARALLEL SAFE
        SET search_path = pg_catalog, pg_temp
        AS $$
            SELECT CASE
                WHEN context.tenant_setting ~* (
                    '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-'
                    '[0-9a-f]{4}-[0-9a-f]{12}$'
                )
                    THEN context.tenant_setting::uuid
                ELSE NULL
            END
            FROM (
                SELECT NULLIF(
                    pg_catalog.current_setting('app.tenant_id', true), ''
                ) AS tenant_setting
            ) AS context
        $$;

        CREATE FUNCTION app.touch_updated_at()
        RETURNS trigger
        LANGUAGE plpgsql
        SET search_path = pg_catalog, pg_temp
        AS $$
        BEGIN
            NEW.updated_at = pg_catalog.clock_timestamp();
            RETURN NEW;
        END
        $$;
        """
    )
    execute_script(
        """
        CREATE TABLE tenants (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            kind text NOT NULL CHECK (kind IN ('personal', 'organization', 'core')),
            name text NOT NULL CHECK (length(btrim(name)) BETWEEN 1 AND 200),
            CHECK (
                (id = '00000000-0000-0000-0000-000000000001'::uuid AND kind = 'core')
                OR (id <> '00000000-0000-0000-0000-000000000001'::uuid AND kind <> 'core')
            ),
            plan text NOT NULL DEFAULT 'unconfigured',
            monthly_cost_cap_usd numeric(12, 4) CHECK (
                monthly_cost_cap_usd IS NULL OR monthly_cost_cap_usd >= 0
            ),
            settings jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(settings) = 'object'),
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            deleted_at timestamptz
        );

        CREATE TABLE users (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id uuid NOT NULL REFERENCES tenants(id),
            oidc_subject text NOT NULL CHECK (length(btrim(oidc_subject)) > 0),
            email text NOT NULL CHECK (length(btrim(email)) > 0),
            display_name text CHECK (display_name IS NULL OR length(display_name) <= 200),
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            deleted_at timestamptz,
            UNIQUE (tenant_id, oidc_subject),
            UNIQUE (tenant_id, id),
            CHECK (tenant_id <> '00000000-0000-0000-0000-000000000001'::uuid)
        );

        CREATE TABLE memberships (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id uuid NOT NULL,
            user_id uuid NOT NULL,
            role text NOT NULL CHECK (
                role IN ('student', 'editor', 'org_admin', 'superadmin')
            ),
            active boolean NOT NULL DEFAULT true,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            deleted_at timestamptz,
            UNIQUE (tenant_id, user_id),
            UNIQUE (tenant_id, id),
            FOREIGN KEY (tenant_id, user_id) REFERENCES users(tenant_id, id),
            FOREIGN KEY (tenant_id) REFERENCES tenants(id),
            CHECK (tenant_id <> '00000000-0000-0000-0000-000000000001'::uuid)
        );

        CREATE INDEX users_tenant_oidc_idx
            ON users (tenant_id, oidc_subject)
            WHERE deleted_at IS NULL;
        CREATE INDEX memberships_user_active_idx
            ON memberships (tenant_id, user_id, active)
            WHERE deleted_at IS NULL;
        CREATE INDEX memberships_tenant_role_idx
            ON memberships (tenant_id, role)
            WHERE deleted_at IS NULL;
        """
    )
    execute_script(
        """
        CREATE TRIGGER tenants_touch_updated_at
            BEFORE UPDATE ON tenants
            FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();
        CREATE TRIGGER users_touch_updated_at
            BEFORE UPDATE ON users
            FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();
        CREATE TRIGGER memberships_touch_updated_at
            BEFORE UPDATE ON memberships
            FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();
        """
    )


    execute_script(
        """
        CREATE TABLE sources (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id uuid NOT NULL REFERENCES tenants(id),
            uploaded_by uuid,
            kind text NOT NULL CHECK (kind IN ('pdf', 'docx', 'pptx', 'image', 'note')),
            scope text NOT NULL CHECK (scope IN ('private', 'core')),
            sha256 char(64) NOT NULL CHECK (sha256 ~ '^[0-9a-f]{64}$'),
            storage_key text,
            title text NOT NULL CHECK (length(btrim(title)) BETWEEN 1 AND 500),
            page_count integer CHECK (page_count IS NULL OR page_count >= 0),
            status text NOT NULL DEFAULT 'uploaded' CHECK (
                status IN (
                    'uploaded', 'quarantined', 'processing', 'ready', 'failed', 'deleted'
                )
            ),
            rights_status text NOT NULL DEFAULT 'unverified' CHECK (
                rights_status IN ('unverified', 'authored', 'licensed', 'takedown')
            ),
            legal_hold boolean NOT NULL DEFAULT false,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            deleted_at timestamptz,
            UNIQUE (tenant_id, id),
            FOREIGN KEY (tenant_id, uploaded_by)
                REFERENCES users(tenant_id, id),
            CHECK (
                (scope = 'core' AND tenant_id = '00000000-0000-0000-0000-000000000001'::uuid)
                OR (scope = 'private' AND tenant_id <> '00000000-0000-0000-0000-000000000001'::uuid)
            ),
            CHECK (
                (scope = 'core' AND uploaded_by IS NULL)
                OR (
                    scope = 'private'
                    AND uploaded_by IS NOT NULL
                    AND storage_key LIKE 'tenants/' || tenant_id::text || '/%'
                )
            )
        );

        CREATE TABLE jobs (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id uuid NOT NULL REFERENCES tenants(id),
            entity_id uuid NOT NULL,
            kind text NOT NULL CHECK (kind IN ('ingest_source', 'export_user', 'delete_user')),
            status text NOT NULL DEFAULT 'queued' CHECK (
                status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')
            ),
            idempotency_key text NOT NULL CHECK (length(btrim(idempotency_key)) > 0),
            pipeline_version integer NOT NULL DEFAULT 1 CHECK (pipeline_version >= 1),
            attempts integer NOT NULL DEFAULT 0 CHECK (attempts >= 0),
            output_ref text,
            error_code text,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            deleted_at timestamptz,
            UNIQUE (tenant_id, id),
            UNIQUE (tenant_id, id, entity_id, pipeline_version),
            UNIQUE (tenant_id, idempotency_key)
        );

        CREATE TABLE job_steps (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id uuid NOT NULL,
            job_id uuid NOT NULL,
            entity_id uuid NOT NULL,
            step text NOT NULL CHECK (
                step IN (
                    'upload_dedupe_scan', 'render_pages', 'parse_layout',
                    'extract_figures', 'extract_tables', 'chunk', 'embed_index',
                    'knowledge_extraction', 'ready_notify'
                )
            ),
            pipeline_version integer NOT NULL CHECK (pipeline_version >= 1),
            status text NOT NULL DEFAULT 'pending' CHECK (
                status IN ('pending', 'running', 'succeeded', 'failed', 'skipped')
            ),
            attempts integer NOT NULL DEFAULT 0 CHECK (attempts >= 0),
            output_ref text,
            error_code text,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            deleted_at timestamptz,
            FOREIGN KEY (tenant_id, job_id, entity_id, pipeline_version)
                REFERENCES jobs(tenant_id, id, entity_id, pipeline_version)
                ON DELETE CASCADE,
            UNIQUE (tenant_id, entity_id, step, pipeline_version),
            UNIQUE (tenant_id, job_id, step, pipeline_version)
        );

        CREATE TABLE audit_log (
            id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            tenant_id uuid NOT NULL REFERENCES tenants(id),
            actor_user_id uuid,
            action text NOT NULL CHECK (length(btrim(action)) > 0),
            target_type text NOT NULL CHECK (length(btrim(target_type)) > 0),
            target_id text,
            request_id uuid,
            ip inet,
            metadata jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(metadata) = 'object'),
            created_at timestamptz NOT NULL DEFAULT now(),
            FOREIGN KEY (tenant_id, actor_user_id) REFERENCES users(tenant_id, id)
        );

        CREATE INDEX sources_tenant_status_idx
            ON sources (tenant_id, status) WHERE deleted_at IS NULL;
        CREATE UNIQUE INDEX sources_active_dedupe_idx
            ON sources (tenant_id, sha256)
            WHERE deleted_at IS NULL;
        CREATE INDEX jobs_tenant_status_idx
            ON jobs (tenant_id, status) WHERE deleted_at IS NULL;
        CREATE INDEX job_steps_resume_idx
            ON job_steps (tenant_id, entity_id, pipeline_version, status)
            WHERE deleted_at IS NULL;
        CREATE INDEX audit_log_tenant_created_idx
            ON audit_log (tenant_id, created_at DESC);
        """
    )
    execute_script(
        """
        CREATE FUNCTION app.resolve_memberships(oidc_subject text)
        RETURNS TABLE (tenant_id uuid, role text)
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path = pg_catalog, pg_temp
        AS $$
            SELECT m.tenant_id, m.role
            FROM public.memberships AS m
            JOIN public.users AS u
              ON u.tenant_id = m.tenant_id
             AND u.id = m.user_id
            WHERE u.oidc_subject = $1
              AND u.deleted_at IS NULL
              AND m.active
              AND m.deleted_at IS NULL
        $$;
        REVOKE ALL ON FUNCTION app.resolve_memberships(text) FROM PUBLIC;
        """
    )

    execute_script(
        """
        CREATE TRIGGER sources_touch_updated_at
            BEFORE UPDATE ON sources
            FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();
        CREATE TRIGGER jobs_touch_updated_at
            BEFORE UPDATE ON jobs
            FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();
        CREATE TRIGGER job_steps_touch_updated_at
            BEFORE UPDATE ON job_steps
            FOR EACH ROW EXECUTE FUNCTION app.touch_updated_at();
        """
    )


def downgrade() -> None:
    execute_script(
        """
        DROP TABLE IF EXISTS audit_log;
        DROP TABLE IF EXISTS job_steps;
        DROP TABLE IF EXISTS jobs;
        DROP TABLE IF EXISTS sources;
        DROP TABLE IF EXISTS memberships;
        DROP TABLE IF EXISTS users;
        DROP TABLE IF EXISTS tenants;
        DROP FUNCTION IF EXISTS app.resolve_memberships(text);
        DROP FUNCTION IF EXISTS app.touch_updated_at();
        DROP FUNCTION IF EXISTS app.current_tenant_id();
        DROP SCHEMA IF EXISTS app;
        """
    )
