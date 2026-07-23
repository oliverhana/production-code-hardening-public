---
name: production-code-hardening
description: Deeply audit and harden an existing service for production, then prove the result with tests and release evidence. Use for enterprise-readiness reviews, production refactors, or investigations involving state machines, async races, deadlocks, resource leaks, exception paths, database migrations, webhooks and idempotency, PII protection, LLM schema/tool boundaries, external-service retries, test gaps, coverage, or go-live gates. Apply to requests such as “深度代码审查并生产化重构”, “排查竞态/死锁/内存泄漏”, “补齐测试和发布门禁”, and “检查 Webhook、PII、LLM Agent 是否可上线”.
---

# Production Code Hardening

Turn a prototype or internal service into a defensible production candidate. Treat implementation, tests, migration safety, runtime configuration, and release evidence as one deliverable.

## Set the operating mode

Infer the authorized mode from the request before changing anything:

- For review, diagnosis, or status requests, inspect and report without editing.
- For hardening, refactoring, fixing, or “直接完成修改”, implement and verify the changes.
- Never let “make it production-ready” authorize deployment, credential rotation, external messaging, data deletion, or history rewriting.
- Preserve unrelated work in a dirty tree. Read repository instructions and inspect `git status` before editing.
- Separate code-complete findings from operator-owned blockers such as DNS, TLS, SSO, KMS, real credentials, and third-party console settings.

## Follow the hardening workflow

### 1. Establish the baseline

1. Read repository instructions, manifests, entry points, deployment files, migrations, tests, and environment templates.
2. Record the working-tree state and avoid overwriting user changes.
3. Run the narrowest existing test, lint, type, build, and dependency checks that reveal the starting condition.
4. Identify the real production entry point. Mark generated, compatibility, demo, and all-in-one files as non-authoritative or make them import the production modules.
5. Build an evidence ledger with: risk, invariant, affected path, proposed control, verification, and external dependency.

Do not begin with cosmetic restructuring. First identify which behaviors and failure modes must remain stable.

### 2. Model the system before patching

Map these dimensions explicitly:

- Process boundaries: UI, API, workers, schedulers, callbacks, CLIs.
- State machines: states, transitions, retries, leases, terminal states, and recovery paths.
- External side effects: messages, uploads, payments, writes, callbacks, and model calls.
- Trust boundaries: user files, webhook payloads, model output, tool output, database text, environment variables, and third-party responses.
- Concurrency domains: threads, async tasks, processes, hosts, database transactions, and file locks.
- Resource ownership: files, sockets, clients, cursors, executors, caches, timers, and temporary data.
- Sensitive data: collection, normalization, storage, lookup, export, retention, and deletion.

Read [state-machine-review.md](references/state-machine-review.md) whenever the service has retries, callbacks, queues, uploads, or multi-step side effects. Do not patch a race until its state transition and recovery invariant are written down.

### 3. Convert risks into enforceable invariants

Prefer program constraints over prompt wording, comments, and operator memory.

#### Validation and LLM boundaries

- Validate model and untrusted API output with strict schemas: reject missing required fields, unexpected fields, invalid types, invalid ranges, and empty values where absence is unsafe.
- Pass only validated objects to persistence, synchronization, notifications, exports, and decisions. Search for raw `.get(...)` or equivalent accesses at every output boundary.
- Execute mandatory business operations in code. Do not rely on `tool_choice="auto"` or a prompt saying the model “must” query, verify, authorize, or persist.
- Treat resume text, filenames, database text, tool output, retrieved documents, and model output as untrusted data, not instructions.
- Pin model/provider configuration explicitly, require HTTPS endpoints, set timeouts, classify retries, and record model/prompt/schema versions when decisions must be audited.
- Position high-impact model results as evidence or recommendations. Require a human decision state and bind approval to the exact content/version reviewed.

#### Identity and PII

- Match identities with strong, normalized identifiers. Never silently fall back to names or other weak identifiers.
- Define normalization as domain policy. Avoid transformations such as stripping email aliases or dots unless the organization has proven they are valid for its population.
- Use keyed HMAC for equality lookup and randomized authenticated encryption for recoverable values. Keep lookup and encryption keys separate.
- Add key/version metadata, rotation semantics, migration checkpoints, and full decryptability audits before dropping legacy data.
- Protect all copies: primary tables, logs, exports, caches, temporary files, WAL/SHM files, backups, and dead-letter payloads.
- Implement retention and deletion capabilities; filesystem permissions alone are not a PII control.

#### Webhooks and external side effects

- Separate transport authenticity, replay protection, and business idempotency; none substitutes for another.
- Authenticate before processing. Validate payload shape, tenant/application identity, actor, record ownership, timestamp window, and encrypted-envelope handling as applicable.
- Derive idempotency keys from the business operation, not timestamp plus nonce.
- Claim the operation transactionally before the side effect. Track at least `processing`, `succeeded`, `retryable_failed`, and `terminal_failed`, with lease ownership and expiry for abandoned work.
- Reuse a stable external idempotency token across retries. Bind retries to the original recipient, actor, and immutable action input.
- Design partial failure explicitly: “external success, local failure” and “local success, response lost” must not create duplicates or permanent loss. Use a durable outbox/worker when request deadlines cannot safely contain the workflow.

#### Concurrency, storage, and resources

- Define one lock order and use it everywhere. Never hold a process-local lock while waiting indefinitely on I/O or another lock.
- Distinguish thread safety, process safety, and host-level coordination. An in-memory lock never proves multi-worker correctness.
- Keep database transactions short and exclude network calls. Use uniqueness constraints or compare-and-set transitions as the final concurrency authority.
- Serialize schema migration and destructive maintenance across processes. Treat SQLite WAL, SHM, backup, and VACUUM operations as part of one storage state machine.
- Bound queues, caches, retries, recursion, request bodies, decompression, page counts, text length, and executor sizes.
- Set explicit timeouts on network, model, subprocess, and lock waits. Retry only transient classes with bounded exponential backoff and jitter.
- Acquire resources with context managers or `try/finally`; test cleanup on cancellation and exceptions.
- Reject oversized or unsupported inputs before expensive parsing where possible, and enforce an early limit during streaming/iteration when preflight cannot know the expanded size.

Use [audit-checklist.md](references/audit-checklist.md) for the complete review surface and evidence expectations.

### 4. Implement in dependency order

Apply controls in this order unless the system demands otherwise:

1. Freeze behavior with characterization tests for critical paths.
2. Introduce strict schemas and typed boundaries.
3. Make identity, authorization, and deterministic business rules explicit.
4. Add durable idempotency and state transitions before changing HTTP retry behavior.
5. Add PII cryptography and verified, restartable migrations.
6. Fix lock ordering, timeouts, resource ownership, and file limits.
7. Unify external-service clients, retries, and error classification.
8. Repair UI/session-state behavior and bind human review to immutable versions.
9. Remove duplicate implementations or convert them into thin compatibility entry points.
10. Update deployment configuration and operator documentation only after runtime behavior is proven.

Keep patches small enough to test after each invariant. Do not combine a schema migration, concurrency rewrite, and unrelated formatting into one opaque change.

### 5. Verify adversarially

Test more than the happy path:

- Schema: wrong types, extra fields, missing fields, empty values, malformed model JSON, and raw-object leakage to output boundaries.
- Identity: normalization, absent identifiers, collisions, no weak fallback, and legacy-data behavior.
- PII: round trip, wrong key, key rotation, partial migration, restart, rollback safety, full-row decrypt audit, and absence from logs/exports.
- Idempotency: concurrent claims, duplicate delivery, response loss, side-effect success plus local failure, lease expiry, recipient/action tampering, and retry reuse of external tokens.
- Database: migration from a realistic copy, concurrent startup, WAL checkpoints, backup/restore, foreign keys, uniqueness, and maintenance exclusion.
- Async/resources: timeout, cancellation, exception cleanup, bounded concurrency, and multi-process execution.
- Files: oversized input, too many pages/items, truncated content marker, empty/scanned input, parser error, and private temporary-file cleanup.
- UI/high-impact decisions: framework rerun semantics, review invalidation after content changes, human override, and formula-safe exports.
- Production startup: fail closed on missing/weak secrets, multiple workers, health checks, and no development server exposed publicly.

Use production-like data only through a protected copy. Never mutate the sole live database to prove a migration.

Coverage is supporting evidence, not the goal. Require assertions over failure semantics and invariants; a high percentage with no partial-failure tests is not a release gate.

### 6. Run deterministic quality gates

Use the repository's own commands first. Use `scripts/run_quality_gates.py` to execute a repeatable Python baseline and emit machine-readable evidence:

```bash
python3 scripts/run_quality_gates.py \
  --project /path/to/project \
  --python /path/to/project/.venv/bin/python \
  --coverage \
  --coverage-fail-under 85 \
  --report /tmp/quality-gates.json
```

The runner avoids a shell, uses bounded timeouts, checks `git diff --check`, compiles Python, auto-detects standard-library `unittest` versus configured `pytest`, runs tests, verifies dependencies, and returns nonzero if a required gate fails. Coverage honors the project's coverage configuration; use repeated `--coverage-target` only to override its source scope. Inspect the project before running tests because project test hooks can execute arbitrary repository code. Treat the JSON report as potentially sensitive because it captures command output; store it in a protected location or pass `--max-output-chars=0` to omit captured output.

For non-Python projects, use the same evidence contract with native build/test/type/dependency tools. Do not claim a gate passed when it was skipped or unavailable.

### 7. Make the release decision

Report these separately:

1. Implemented controls and the invariants they enforce.
2. Verification evidence with exact commands, counts, coverage, and smoke-test topology.
3. Remaining code risks with severity and owner.
4. External blockers requiring credentials, infrastructure, policy, or business decisions.
5. A release verdict: `not ready`, `controlled internal trial`, `controlled canary with human review`, or `production ready`.

Never equate “all tests pass” with “production ready”. Keep the verdict conservative when real multi-worker behavior, migrations, TLS, identity, retention, or external integrations remain unproven.

## Avoid false closure

- Do not call a certificate or fraud-rule lookup “verification” unless it validates the subject and credential against an authoritative source.
- Do not call a nonce cache business idempotency.
- Do not call chmod encryption or access control.
- Do not call an in-process mutex multi-worker safety.
- Do not return retryable HTTP errors after a successful side effect unless durable idempotency prevents duplication.
- Do not preserve two production implementations that can drift.
- Do not silently coerce invalid structured output into empty data.
- Do not backfill hashes from unavailable plaintext by guessing identity.
- Do not log decrypted PII or secrets while debugging a migration.
- Do not mark operator-owned controls complete based only on example configuration.
