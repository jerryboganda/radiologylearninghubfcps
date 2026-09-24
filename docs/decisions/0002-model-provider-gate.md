# ADR 0002: Model and embedding provider decision gate

Status: **Open — no provider approved**
Date: 2026-09-24
Decision owners: product, security/privacy, engineering, finance, and content quality
Scope: hosted LLM/VLM, local LLM/VLM, text/image embeddings, and reranking

## Context

radbrain needs provider-agnostic model routes so deployment can change models without
rewriting agents. Route names are a stable interface; provider and concrete model
names are configuration. Candidate-owned source text and figures may be private or
copyrighted, so a provider decision changes privacy, legal, residency, quality,
availability, and cost commitments.

The supplied implementation spec contains example models and fallback chains. They
are hypotheses, not an approval, procurement decision, or permission to transmit
tenant data. This ADR defines the evidence gate. It does not select a provider.

## Decision

**No hosted or external model/embedding provider may receive application or tenant
content until a successor ADR records approval against every mandatory gate below.**
Until then:

- routes remain `reason`, `extract`, `classify`, `vision`, and `local`;
- checked-in route configuration is mock-only and has no real provider credential;
- tests use synthetic data; local CI makes no paid external model call;
- `ALLOW_UNGROUNDED_DEFAULT=false` remains enabled;
- private-material tests do not leave the authorized local/private environment;
- concrete model names, endpoints, and keys are not copied into this ADR.

A local model still needs quality, security, licensing, capacity, and retention
review. “Open source” is not automatically private, safe, or accurate.

## Non-negotiable technical interface

1. Application agents call named routes only. Provider/model changes are config and
   do not alter prompts, schemas, or citation guards.
2. Every call records route, concrete model/version, prompt/schema version, tenant,
   token counts, cost, latency, cache status, and trace ID in protected telemetry.
3. Every response is validated against a versioned Pydantic schema. Provider
   structured output is helpful but is not trusted without application validation.
4. User source text is data, not instruction. Tools/links derived from source content
   are not executed. Tutor output still requires the grounding guard.
5. Cache keys include tenant and scope. Provider caching and eval caching must not
   cross tenants except for reviewed immutable Core prompts/assets.
6. Model names, base URLs, and provider keys are deployment configuration. Browser
   bundles and source-controlled `.env` files never contain provider secrets.
7. Timeouts, retry bounds, circuit breaking, spend/rate caps, and an explicit local or
   degraded response are required. A silent provider fallback cannot weaken gates.
8. An embedding or reranker change is a schema/pipeline decision: dimensions,
   normalization, migration/backfill, cache invalidation, retrieval evals, and rollback
   must be specified before rollout.

## Mandatory approval gates

### A. Privacy, legal, and residency

The evidence packet must identify and obtain sign-off on:

- controller/processor roles, DPA/terms, subprocessors, and breach notification;
- exact data sent for each route (text, images, metadata, prompts, retained context);
- zero/few retention for prompts and outputs, training opt-out, human review, and
  deletion behavior across backups and support systems;
- processing regions, cross-border transfer mechanism, and institution/customer region
  requirements;
- whether the provider's terms permit candidate-owned copyrighted educational
  material and derived outputs;
- contractual deletion SLA and ability to honor user export/delete within 30 days;
- incident response, audit access, and subprocessor change notification.

Identifiers/patient data are prohibited regardless of contract or region. A provider
commitment cannot override the no-patient-data rule.

### B. Security and supply chain

- HTTPS-only endpoints, current transport security, documented provider auth, and
  least-privilege project/service credentials.
- Credential rotation, secret storage, incident revocation, and log redaction plan.
- Security review of the provider, subprocessors, SDKs, and model artifacts.
- Malware/model-artifact provenance where local models are downloaded.
- Evidence that prompts, source text, embeddings, and response bodies are absent
  from application, proxy, and provider logs except within approved bounded tracing.
- Data-use settings that prohibit provider training on application content.


### C. Quality and safety evidence

Use radiologist/editor-reviewed, licensed or fully synthetic golden sets; never use
private study folders as default evals. Run the same versioned prompts and fixtures
against each candidate. Report model/version, region, date, sample count, failures,
cost/latency percentiles, and variance—not only an average.

| Capability | Required evidence | Release gate |
| --- | --- | --- |
| Extraction | 300 labelled chunks; claim precision/recall; exact span check | P >= 0.90, R >= 0.80, span pass 100% |
| Grounding | 200 labelled tutor answers and hallucination review | Judge agreement >= 0.90, hallucination <= 2% |
| Retrieval | 300 questions with gold chunks | recall@8 >= 0.90, MRR >= 0.75 |
| Question quality | 100 items, two-editor review | Acceptable >= 85%; no regression vs current |
| Grader | 100 labelled SEQ answers | Within one editor point >= 90% |
| Vision | Licensed/synthetic figure set with modality/region/findings review | No unsupported diagnosis; route threshold approved before M1 |
| Reranking | Same retrieval set and index build | Improves or preserves gates; p95 within target |

Additional requirements:

- Capability/JSON-schema success, truncation, timeout, and retry rates.
- Deterministic/planner tests remain code-only and provider-independent.
- Failure slices by content type, language, image quality, and protected attributes.
- Human comparison for safety-critical radiology claims; no pass-probability claim.
- Shadow results before traffic; canary and rollback criteria in the successor ADR.

The provider with the highest benchmark average does not override privacy, grounding,
failure, or cost gates.

### D. Reliability and operations

- Published availability, regional service boundaries, rate limits, and quotas.
- Tested timeout/retry/circuit-breaker behavior and idempotency.
- Capacity for target concurrent chat/ingest; queue/backpressure plan.
- Status/incident subscription and notification path.
- Fallback route and degradation UX (queue, local model, or clear pause).
- Local fallback hardware, cold-start, throughput, and maintenance plan for solo mode.
- Target p95 latency by route and monthly spend projection at launch load.

### E. Cost and commercial gate

Provide a bottom-up estimate using token/image units, expected retries/cache misses,
embedding volume, storage, evaluation, and projected cohort/concurrency. State:

- monthly and per-active-user cost at low/median/high load;
- free-tier assumptions and quota exhaustion behavior;
- spend alerts at 80% and a hard tenant cap at 100% (110% interactive rule if adopted);
- billing owner, approved launch cap, currency, taxes, and overage response;
- local compute/energy cost and migration cost;
- price sensitivity and effect on SaaS margin.

The launch cohort size/date and approved monthly cap are human/product decisions.
A benchmark token price alone is not a cost model.

## Evidence packet and approval record

The proposer attaches, without tenant/private content:

1. candidate routes, exact model/version, provider, region, and hosting mode;
2. data-flow diagram and field-level payload inventory for every route;
3. legal/privacy/security questionnaires, DPA/terms summary, retention and deletion
   evidence, subprocessors, and transfer mechanism;
4. reproducible eval report and failure analysis against the gates above;
5. load/latency/reliability test and incident/fallback plan;
6. bottom-up cost model, launch assumptions, cap, and alerts;
7. SDK/container hashes, configuration diff, secret plan, and rollback plan;
8. signed approvals from product, security/privacy, engineering, finance, and the
   clinical/content-quality owner.

The successor ADR template is:

```markdown
# ADR NNNN: Select <capability> provider and models
Status: Accepted | Rejected | Superseded
Date: YYYY-MM-DD
Decision: <provider/model/region per route>
Approved by: <roles and names/links, no personal contact data>
Evidence: <eval, contract, security, load, and cost links>
Consequences: <quality, cost, fallback, residency, migration>
Rejected alternatives: <specific candidates and reasons>
Re-review triggers: <material version/price/terms/region change>
```

## Rollout after approval

1. Add provider credentials only to the environment/secret manager.
2. Configure explicit routes/fallbacks and safe mock default; verify config schema.
3. Run synthetic smoke, contract, cost-cap, and failure tests in non-production.
4. Run shadow traffic with output/log redaction, then a small tenant canary.
5. Monitor quality, latency, errors, cap consumption, and incidents.
6. Expand only after the canary window meets the successor ADR thresholds.

Rollback disables the route/config revision, returns affected work to the approved
fallback or queues it, and revokes compromised credentials. It must not silently
switch to an unapproved provider or bypass grounding.

## Re-review triggers

A new ADR or explicit amendment is required after a concrete model/provider change,
region or subprocessors change, material price/terms/retention change, new data
category or modality, embedding dimension change, incident, grounding regression
over two points, or fallback architecture change.

## Current decision

**Deferred.** There is no approved hosted provider, embedding provider, reranker, or
launch spend cap in this repository. Mock/local-only development may continue under
the data-handling runbook. This gate is a release blocker, not a recommendation to
adopt the examples in the product specification.
