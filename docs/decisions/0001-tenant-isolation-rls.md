# ADR 0001: Tenant isolation with PostgreSQL RLS

Status: **Accepted as the M0 security boundary; implementation verification pending**
Date: 2026-09-24
Decision owners: engineering and security reviewers
Scope: multi-tenant database, object storage, caches, background jobs, and tests

## Context

radbrain must prevent one user or tenant from reading or mutating another tenant's
uploads, pages, figures, embeddings, extracted claims, generated questions, chats,
jobs, and study activity. Filtering in FastAPI is necessary for usability but is
not a sufficient security boundary: a missing filter, background path, or direct
database query could cross tenants.

The product also has a reserved Core Library readable alongside tenant-private data.
Superadministration, migrations, analytics, exports, and deletion need privileged
operations without making the normal API role a universal bypass. PostgreSQL 16
RLS is already part of the chosen stack and supports the required fail-closed and
negative-test model.

## Decision

1. **Database is authoritative.** Every tenant-scoped table has a non-null
   `tenant_id`, enables RLS, and has explicit read/write policies. New tenant tables
   cannot merge without a two-tenant negative test.
2. **Separate database identities.** The runtime API/worker role does not own
   protected tables and has neither `SUPERUSER`, `BYPASSRLS`, nor membership in a
   role that bypasses RLS. A separate migration role owns/schema-migrates but is not
   supplied to the application.
3. **Transaction-local context.** After validating the authenticated membership,
   each request/job transaction sets `app.tenant_id` using `set_config(..., true)`
   before the first tenant query. The value is scoped to that transaction and
   restored/reset at the boundary. Pooled sessions must never retain it.
4. **Fail closed.** Policies compare `tenant_id` with a safely parsed value derived
   from transaction-local context. Missing or malformed context matches no tenant
   row and must not fall back to a default tenant.
5. **Policies cover every mutation.** `SELECT`, `INSERT`, `UPDATE`, and `DELETE`
   are authorized by tenant-aware policies; `WITH CHECK` prevents changing a row out
   of the active tenant. `FORCE ROW LEVEL SECURITY` protects against accidental
   owner-path bypass where PostgreSQL supports the intended ownership model.
6. **No request-selected trust.** A client body/query tenant ID is never sufficient.
   The server resolves active tenant from the token subject and a current membership
   (or explicit switch flow that verifies membership). Development identity headers
   are disabled outside local development.
7. **Core is an explicit exception.** Only reviewed, read-only Core policies may
   expose reserved Core rows. There is no blanket policy that makes all rows for the
   Core tenant visible, and tenant content cannot be promoted into it.
8. **Application authorization remains.** RLS limits tenants; roles limit actions
   within a tenant. Student/editor/org-admin/superadmin checks occur in a shared
   dependency/service layer, and mutations are audited.
9. **Object isolation mirrors RLS.** Buckets are private; keys start with
   `tenants/{tenant_id}/`; authorization is checked before signing a URL; signatures
   expire (target: five minutes). A key is never treated as proof of access.
10. **Cache isolation mirrors RLS.** Cache keys include tenant UUID and scope.
    Redis, LLM output caches, rate limits, job deduplication, and in-process
    memoization must not cross tenants except for explicit Core content.
11. **Workers are trusted application actors, not bypasses.** Jobs persist the owning
    tenant and set the same transaction-local context on every database transaction.
    Queue messages cannot supply an unchecked override.
12. **Privileged service paths are narrow.** Migrations, break-glass support, exports,
    deletion, and aggregate analytics use separately reviewed credentials/functions
    with least privilege, time limits, and audit records. A runtime superadmin does
    not gain `BYPASSRLS`.

## RLS test contract

The test suite must connect through the same non-privileged role as the application.
Using a superuser, table owner, or `BYPASSRLS` role is not evidence.

At minimum it proves:

- Tenant A and Tenant B each exist, and the Core tenant is distinct.
- A can create/read/update/delete only A-owned rows; the same holds for B.
- Explicitly targeting B's UUID in a path or request parameter does not reveal or
  mutate B's row: reads are empty/not found and writes are rejected or zero rows.
- INSERT, UPDATE, and DELETE cannot attach/move a row to another tenant.
- No transaction context produces zero tenant rows, including a reused pooled
  connection after a prior tenant request.
- Invalid context fails closed and does not poison the next transaction.
- Every privileged tenant switch is rejected without current membership.
- Only approved read paths can see Core rows; a tenant cannot update/publish them.
- Service-role access is tested separately and is impossible with runtime settings.

The suite also checks migrations under a production-like role split and proves the
runtime role has no bypass attribute. Record the test command, app role name (not
credentials), migration revision, and pass/fail evidence.


## Threat model and required controls

| Threat | Required control | Verification |
| --- | --- | --- |
| Missing endpoint filter | RLS on every tenant table | Two-tenant read/write suite |
| Pooled-session context leak | Transaction-local set/reset and reuse test | Sequential tenant requests on one connection |
| Forged tenant ID | Membership-derived context | Switch/endpoint negative test |
| Runtime elevated role | Separate owner/migrator and app role | PostgreSQL role-attribute inspection |
| Object-key guessing | Private bucket, authorization, short signature | Cross-prefix signed-URL test |
| Shared cache poisoning | Tenant/scope-prefixed key and invalidation | Two-tenant cache test |
| Worker message tampering | Authorized queue boundary plus context validation | Job ownership and replay tests |
| Core tenant promotion | Reserved scope, editorial workflow, write denial | Core write negative test |
| Support privilege abuse | Separate audited break-glass path | Access review and audit assertion |

## Consequences

### Positive

- A forgotten application filter does not by itself become a cross-tenant breach.
- Isolation is uniform across API, workers, exports, and future services.
- Negative tests directly demonstrate the product's highest-priority invariant.
- Core access can coexist with strict private scopes without mixing private rows.

### Costs and risks

- Every query needs authenticated tenant context; missing context is a bug, not a
  usability fallback.
- Connection pooling, transactions, migrations, admin jobs, and tests need extra care.
- Cross-tenant analytics and support operations need deliberately reviewed paths.
- Policy mistakes (owner bypass, permissive policy, missing `WITH CHECK`) are serious;
  static review and live negative tests are both required.
- Connection-pool reset behavior must be verified against the chosen driver.

## Alternatives rejected

- **Application filters only:** one missing predicate or new path can leak data.
- **Separate database/schema per tenant:** stronger physical separation, but operationally
  expensive for SaaS; not selected for v1.
- **Encrypt every tenant with a different key:** does not replace row/query isolation.
- **Rely on JWT tenant claims alone:** claims can be stale/forged without membership
  and do not protect background jobs or direct queries.
- **Give superadmin `BYPASSRLS`:** couples product administration to unrestricted raw
  data access and makes compromise too broad.

## Rollout and rollback

1. Add schema and restrictive RLS in an expand migration; deploy an RLS-bound role.
2. Backfill tenant ownership and validate null/orphan rows before enabling writes.
3. Deploy context-setting application code, then enforce policies.
4. Run the role-attribute audit and two-tenant suite in CI/staging.
5. Observe denied-access metrics without logging source data.

A release that breaks authorized application traffic must roll back application
code first. Do **not** disable RLS, grant `BYPASSRLS`, or reuse a superuser as a hotfix.
Fix forward with a reviewed policy/migration after restoring service. RLS rollback is
an emergency security decision requiring the security owner and a time-boxed plan.

## Verification before M0 acceptance

- [ ] Migration enables and forces RLS on every tenant-scoped table
- [ ] Runtime role has no bypass/owner privilege
- [ ] Every request/job path sets transaction-local context before querying
- [ ] Two-tenant and no-context suites pass as the runtime role
- [ ] Core read policy is narrow and writes are denied
- [ ] Object/cache isolation has matching negative tests
- [ ] Security review accepts the role split and privileged paths

Until these boxes have evidence, M0 tenant isolation is **not complete**, even if
context unit tests pass.
