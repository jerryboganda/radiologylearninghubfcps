# ADR 0003: Use RustFS for the local M0 S3-compatible runtime

Status: **Accepted for M0 local/CI runtime; staging storage remains deployment-configured**
Date: 2026-09-24
Decision owners: engineering and platform reviewers
Scope: disposable local/CI object storage only

## Context

The M0 Compose stack requires a private S3-compatible object-storage service for
API/worker configuration and startup verification. The previously pinned MinIO image
was no longer anonymously pullable from its publisher registry in GitHub Actions, so
CI could not reproduce the required runtime evidence. The product contract remains
`S3_ENDPOINT`, `S3_BUCKET`, `S3_ACCESS_KEY`, and `S3_SECRET_KEY`; the application must
not depend on MinIO-specific APIs.

## Decision

Use the project-owned `rustfs/rustfs:1.0.0` image for the local/CI `storage` service.
Configure it with RustFS's documented single-node S3-compatible variables and retain
private named-volume storage. The production override requires an immutable
`RADBRAIN_STORAGE_IMAGE`; production may use RustFS, S3, or another reviewed
S3-compatible service without changing application code.

This decision does not approve a hosted storage provider, retention policy, region,
or production storage commitment.

## Consequences

- CI can pull a pinned, project-owned S3-compatible image and run the full M0 Compose
  verification without an unavailable MinIO tag.
- The local credentials and volume are disposable development configuration only.
- RustFS's single-node disk-check bypass is enabled solely for this disposable local
  topology and must not be copied to staging/production.
- The application contract remains generic S3; switching storage implementations does
  not alter tenant-prefixed object-key or bucket policy requirements.
- Backups, versioning, retention, access logging, and restore drills remain staging
  or later-milestone obligations.

## Rejected alternatives

- **Unavailable MinIO tag:** keeps the scaffold unbootable and makes CI evidence
  depend on an unavailable publisher artifact.
- **Unverified third-party image:** introduces an unreviewed supply-chain dependency
  for a security-sensitive runtime.
- **Application-specific RustFS SDK:** couples the API/worker to a dev-only storage
  implementation and violates the provider-neutral S3 contract.

## Evidence

GitHub Actions run `36057363650` and the final run for revision `ecffb13` verify the
full runtime Compose startup, API/web health, worker ping, migrations, and live RLS
proof using the pinned RustFS image. This evidence is local/CI runtime evidence, not
staging OIDC or production storage approval.
