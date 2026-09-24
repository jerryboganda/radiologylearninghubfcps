# radbrain documentation

This directory is the documentation entry point for the M0 scaffold and the later
milestones defined by the implementation specification.

## Start here

| Need | Document |
| --- | --- |
| Product, architecture, and milestone source of truth | [`SPEC.md`](SPEC.md) |
| Current implementation snapshot | [`../CONTEXT.md`](../CONTEXT.md) |
| Agent and contributor rules | [`../AGENTS.md`](../AGENTS.md), [`../CLAUDE.md`](../CLAUDE.md) |
| Local and private data rules | [`runbooks/data-handling.md`](runbooks/data-handling.md) |
| M0 operation, verification, rollback, and demo | [`runbooks/m0-foundation.md`](runbooks/m0-foundation.md) |
| Tenant isolation and RLS decision | [`decisions/0001-tenant-isolation-rls.md`](decisions/0001-tenant-isolation-rls.md) |
| Model-provider approval gate | [`decisions/0002-model-provider-gate.md`](decisions/0002-model-provider-gate.md) |

## Documentation rules

- State whether a capability is implemented, targeted, or only a requirement.
- Never put source text, prompts containing source text, credentials, patient data,
  tenant data, or private study-file names in documentation.
- Use synthetic identifiers in commands and examples.
- Record material architectural or policy choices as an ADR under `decisions/`.
- Keep operational instructions under `runbooks/` and update them with behavior.
- Prefer links to the canonical implementation over copying large sections of it.

## Current status

The repository is an M0 foundation scaffold. Do not infer M0 completion from the
presence of this documentation. The authoritative exit test is in the M0 runbook,
and all four exit conditions must have fresh evidence on staging.
