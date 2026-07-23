# State Machine and Side-Effect Review

Use this worksheet for any workflow with retries, callbacks, leases, queues, uploads, notifications, payments, or model-assisted decisions.

## 1. Inventory operations

Create one row per business operation:

| Operation | Trigger | Business key | Mutable state | External effect | Deadline | Recovery owner |
|---|---|---|---|---|---|---|
| Example: recommend record | signed webhook | record + action + recipient | event row | send message, update record | webhook SLA | worker/reconciler |

Keep transport identifiers such as request IDs, timestamps, and nonces separate from business keys.

## 2. Define states and legal transitions

Prefer an explicit transition table:

| Current | Event/guard | Next | Atomic write | Side effect allowed? |
|---|---|---|---|---|
| absent | valid request + successful claim | processing | insert unique business key, lease, immutable inputs | yes, by lease owner |
| processing | duplicate while lease valid | processing | none | no |
| processing | transient failure | retryable_failed | attempts, error class, next attempt | no |
| processing | effect confirmed | succeeded | external receipt/result | no further effect |
| retryable_failed | retry due + successful claim | processing | new lease, same external token | yes |
| processing | invalid/permanent failure | terminal_failed | reason | no |
| processing | lease expired + reconciliation | processing | compare-and-set new owner | only after checking effect state |

For each transition, specify the database uniqueness constraint or compare-and-set condition that makes it atomic.

## 3. State invariants

Write invariants before code. Common examples:

- At most one valid lease owner may perform the effect for a business key.
- Immutable inputs—actor, recipient, action, resource, payload digest—cannot change across retries.
- The external idempotency token remains stable for all attempts of one operation.
- A succeeded operation never returns to a state that permits the effect again.
- A retryable operation eventually becomes claimable; a crashed worker cannot hold it forever.
- Terminal validation or authorization failures are never retried.
- A human approval applies only to the exact version/digest reviewed.

If the external system does not support idempotency or querying effect status, document that exactly-once behavior is impossible. Choose and explain the business preference between duplicate and missed effects.

## 4. Analyze every crash window

Walk through failure between every adjacent pair:

1. Authenticate and validate.
2. Claim business key.
3. Commit claim.
4. Call external system with stable token.
5. Receive external success.
6. Persist receipt/success.
7. Perform dependent local/remote update.
8. Return response or acknowledge queue item.

For each gap ask:

- What persists if the process dies here?
- What does a retry observe?
- Could the side effect repeat?
- Could the operation become permanently stuck?
- Can a reconciler prove the external outcome?
- Is the HTTP/queue response consistent with retry semantics?

Pay special attention to “effect succeeded, success record failed” and “success committed, response lost”.

## 5. Review lock and transaction order

Build a lock graph including process locks, file locks, database transactions, row/advisory locks, and external calls.

Rules:

1. Define one global acquisition order.
2. Add timeouts to waits.
3. Never hold a database transaction or exclusive maintenance lock over network I/O.
4. Use database constraints as the cross-process authority.
5. Treat migration, backup, WAL checkpoint, and VACUUM as exclusive storage transitions.
6. Re-check conditions after acquiring a lock; observations made before waiting may be stale.

A process-local mutex can optimize contention but cannot establish correctness across workers or hosts.

## 6. Build the adversarial test matrix

At minimum test:

- Two workers claim the same absent business key simultaneously.
- A duplicate arrives while the original lease is valid.
- A worker dies after claim and another resumes after expiry.
- External timeout occurs before and after the remote system commits.
- External success occurs but local success persistence fails.
- Local success commits but the response is lost.
- Retry attempts to change actor, recipient, action, or payload.
- A stale worker tries to commit after its lease was replaced.
- Transient failure reaches retry limits; permanent failure is not retried.
- Multiple processes start during schema migration or maintenance.

Assert externally observable effect count, final state, immutable bindings, attempt count, and recovery—not only HTTP status.

## 7. Decide when to use an outbox

Use a durable outbox/inbox plus worker when one or more apply:

- The request deadline is shorter than worst-case side-effect latency.
- Multiple remote side effects must be coordinated.
- The remote service can commit while the response is lost.
- Retries must survive process restarts.
- Operators need reconciliation, replay, or dead-letter handling.
- Rate limits require delayed scheduling.

Keep the synchronous endpoint responsible for authentication, validation, atomic enqueue/claim, and a truthful acceptance response. Let the worker own retries and reconciliation.

