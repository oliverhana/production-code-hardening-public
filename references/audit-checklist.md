# Production Hardening Audit Checklist

Use this checklist selectively after mapping the system. Record evidence for every relevant item; mark irrelevant items as not applicable with a reason rather than silently skipping them.

## Architecture and ownership

- Identify production entry points, worker topology, process count, schedulers, callbacks, and compatibility/demo entry points.
- Locate repository instructions, generated files, dirty-tree changes, runtime manifests, migrations, and data stores.
- Trace each critical request from input through validation, state transition, external side effects, persistence, response, and retry.
- Assign ownership for code, infrastructure, credentials, policy, and external consoles.

## Validation and trust boundaries

- Enumerate all untrusted inputs: HTTP, webhooks, files, filenames, database free text, model/tool output, queues, environment values, and third-party responses.
- Enforce strict schemas at ingress and after probabilistic transformations.
- Reject unknown fields where they could hide version drift or injection.
- Verify downstream persistence, sync, export, and notification paths consume validated objects only.
- Bound strings, collections, nesting, numeric ranges, and expanded/decompressed sizes.
- Escape or sanitize output for its sink: SQL, Markdown/cards, CSV formulas, HTML, logs, and filenames.

## LLM and agent controls

- Separate deterministic business operations from model judgment.
- Remove model-selected tools for mandatory history, authorization, identity, verification, or persistence actions.
- Treat retrieved/tool/database content as untrusted data in the system policy.
- Require explicit provider endpoint, HTTPS, timeout, model identifier, retry policy, and token/input limits.
- Validate model output; classify transport, rate-limit, authentication, context-length, and schema failures separately.
- Store model, prompt, schema, and policy versions for auditable decisions.
- Require human review for high-impact decisions and bind review to an immutable content/version digest.

## Identity, authorization, and PII

- Define authoritative identifiers and normalization rules; document collision behavior.
- Prohibit fallback from strong identifiers to names unless a human-mediated reconciliation flow exists.
- Authorize tenant, actor, record, recipient, action, and resource—not just the request signature.
- Use separate keyed HMAC and authenticated-encryption keys.
- Store encryption key version and support rotation without losing decryptability.
- Encrypt sensitive derived fields as well as obvious phone/email fields.
- Inspect logs, exports, temp files, WAL/SHM, backups, caches, and error payloads for plaintext.
- Implement retention, deletion, audit access, and least-privilege runtime directories.
- Test migration on a protected realistic copy; prove all expected ciphertext decrypts and no plaintext remains.

## Webhook and side-effect semantics

- Verify signature/MAC, timestamp window, nonce replay defense, verification token, encrypted envelope, tenant/app identity, and request size.
- Parse all supported event envelope versions without weakening validation.
- Choose a business idempotency key from immutable operation identity.
- Claim before side effect using a database uniqueness constraint or atomic compare-and-set.
- Record lease owner/expiry, attempts, stable external token, immutable recipient/action, error class, and timestamps.
- Distinguish retryable from terminal failures and allow safe recovery of abandoned claims.
- Test successful side effect with failed local update, lost HTTP response, duplicate callback, and concurrent workers.
- Use durable outbox/inbox processing when request SLA is shorter than reliable completion time.

## Concurrency and lifecycle

- List every lock and establish one acquisition order.
- Check all shared mutable caches and singleton clients under threads and processes.
- Avoid network calls and unbounded work inside database transactions or locks.
- Set bounded lock waits and expose timeout/recovery behavior.
- Bound thread pools, async task groups, queues, caches, retries, and result retention.
- Close files, responses, cursors, sessions, executors, and temporary resources on success, failure, and cancellation.
- Verify background threads have stop/join semantics and do not multiply on framework reruns or worker forks.
- Find fire-and-forget tasks, callbacks, futures, and thread targets whose exceptions are never observed; route failures to structured telemetry and recovery.
- Review broad `except`, swallowed exceptions, retry wrappers, and framework error hooks; preserve actionable error classes without leaking sensitive payloads.
- Measure or stress long-lived caches, queues, task registries, response bodies, and object retention rather than inferring “no leak” from a short unit test.
- Use monotonic time for durations/leases where appropriate and UTC-aware timestamps for persisted events.

## Database and migrations

- Enable and test foreign keys, uniqueness, transaction isolation, busy timeouts, and indexes for lookup/idempotency paths.
- Serialize migrations across processes and make each migration restartable or transactionally atomic.
- Back up before irreversible conversion and verify restore behavior.
- Coordinate SQLite schema changes, WAL checkpoints, backup, VACUUM, and sidecar-file permissions.
- Avoid using a process-local lock as the only database concurrency control.
- Preserve schema/application compatibility during rolling deployment or explicitly prohibit mixed versions.
- Record row counts, null counts, collisions, orphan counts, decrypt failures, and schema version after migration.

## Files, parsers, and uploads

- Enforce upload byte limits before copying or parsing.
- Enforce page/item/expanded-text limits during early iteration.
- Use private random temporary paths and clean them in `finally` without cross-request deletion races.
- Validate content and parser behavior rather than trusting file extensions.
- Treat empty/scanned files distinctly and return actionable errors; add OCR only with explicit resource limits.
- Prevent archive bombs, path traversal, unsafe symlinks, and parser subprocess hangs when relevant.
- Order remote upload and local evaluation to avoid orphan side effects, or implement compensation/reconciliation.

## External clients and runtime configuration

- Centralize authentication, token refresh, HTTP/business-code validation, timeout, retry, and telemetry.
- Refresh expired credentials consistently and at most within a bounded retry policy.
- Do not retry authentication, authorization, validation, or deterministic business failures.
- Fail closed in production for missing/weak secrets, insecure URLs, debug mode, and insecure webhook bypasses.
- Keep secrets out of source, logs, process arguments, generated reports, and example files.
- Use a production server, multiple-worker smoke test, TLS termination, request limits, and health/readiness probes.

## Tests and release evidence

- Add characterization tests before risky refactors.
- Cover malformed inputs, concurrent operations, partial failures, retry boundaries, cleanup, migrations, and production startup.
- Run tests in the same dependency set and interpreter intended for deployment.
- Run compilation/build, tests, coverage, dependency consistency, static/type checks where configured, and diff whitespace checks.
- Test the real WSGI/ASGI/worker entry point with at least two workers when supported.
- Verify sensitive runtime files are ignored and untracked; inspect history separately before claiming secret removal.
- Report exact commands and outcomes, skipped gates, dataset/migration counts, and remaining external blockers.

## Release evidence record

For each P0/P1 item, record:

| Field | Required evidence |
|---|---|
| Risk | Concrete failure and impact |
| Invariant | Property that must always hold |
| Control | Code/configuration enforcing it |
| Test | Adversarial or failure-path proof |
| Runtime proof | Worker topology, migration copy, or integration smoke evidence |
| Residual risk | What remains and why |
| Owner | Code, infrastructure, security, legal, or business |

Finish with a release verdict and explicit blocking conditions. Do not collapse skipped, mocked, and externally blocked checks into “passed”.
