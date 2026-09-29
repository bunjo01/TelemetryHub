# Microservices Architecture Guide

## Scope
Applies after modules are extracted from the modular monolith.
Engineers and AI contributors should follow these rules.

Goal: keep the distributed system understandable, reliable, and loosely coupled.
Preferences allow justified exceptions; mandatory safeguards use “must”.

## Core Principle
Do not create a microservice without a clear reason.

Good reasons:
- different scaling needs,
- clear domain ownership,
- separate lifecycle,
- independent deployment value,
- high-volume workload.

Do not create one service per entity or table.
Keep the modular monolith until extraction has a concrete benefit that justifies
additional deployments, network calls, monitoring, and operational cost.

## Service Boundaries
Each service should own a business capability.

Good examples:
- Device Service
- Telemetry Ingestion
- Telemetry Processing
- Alert Service
- Analytics Pipeline

Avoid:
- Temperature Service
- Battery Service
- Status Service

Aim for high cohesion and low coupling.
Share small, stable infrastructure utilities or generated contracts when useful.
Avoid shared business-model libraries that force services to upgrade together.

## Communication

```text
REST  -> Frontend <-> API Gateway
gRPC  -> synchronous internal calls
Kafka -> asynchronous events
```

Prefer async communication when an immediate response is not needed.

Avoid long chains such as:

```text
A -> B -> C -> D -> E
```

## Data Ownership
Each service should own its persistence.

A service should not directly query another service's private database.

Use:
- gRPC,
- Kafka events.

Services may share a database server, but must retain separate data ownership
and access permissions. Do not share private tables or write another service's data.

## Events
Events describe something that already happened.

Good:
- `TelemetryReceived`
- `DeviceRegistered`
- `AlertCreated`
- `DeviceOffline`

Avoid command-like event names.

Events should contain at least:

```text
event_id
event_type
occurred_at
version
source
payload
```

Include company and resource identity where relevant; define timestamp meaning
and schema compatibility without exposing unnecessary sensitive data.

## Idempotency
Assume messages and some requests can be delivered more than once.

Reuse stable `event_id` or `idempotency_key` values across retries.
A tracing `request_id` is not automatically an idempotency key.

Repeated processing must not create incorrect duplicate side effects.
Coordinate duplicate detection and the business change atomically where possible;
otherwise define a recoverable workflow. An ID or an in-memory check alone is insufficient.
Scope keys to the company and operation, reject conflicting payload reuse, and
keep deduplication records for the supported retry/replay window.

## Retries
Retry only transient failures.

Use:
- bounded attempts,
- timeout,
- exponential backoff,
- jitter.

Do not retry permanent validation errors.
Retry side effects only when safe to repeat, within the operation's overall deadline.
Give retries a clear owner so retrying at several layers does not multiply load.

## Kafka Processing
- Choose partition keys for the ordering needed by the business; there is no global order across partitions.
- Commit offsets only after durable processing or safe handoff. Concurrent processing must not commit past unfinished messages in the same partition.
- Handle replay after crashes and rebalances; Kafka transactions alone do not make external database effects exactly-once.
- Preserve required ordering during retries and replay; document when skipping a failed event is acceptable.

## Dead Letter Queue
Quarantine invalid or repeatedly failing messages according to a defined policy.
For dependency outages, prefer bounded retries and pausing intake over flooding the DLQ.

Preserve:
- original event,
- error,
- retry count,
- timestamps.

The DLQ must be observable and reviewable.
Assign an owner, retention policy, alerts, and a controlled replay procedure.
Confirm durable DLQ handoff before committing the original message's offset;
replay must preserve event identity and remain safe to repeat.

## Transactional Outbox
Use when a service must:

```text
change DB state
+
publish an event
```

Do not assume:

```text
commit DB
then publish Kafka
```

is safe without handling failure between both operations.
Persist the business change and outbox record in the same database transaction.
The publisher may deliver more than once; keep consumers idempotent and monitor
outbox age, failures, and cleanup.

## Eventual Consistency
Different services may temporarily hold different views of data.

Design workflows so temporary inconsistency is expected and recoverable.
Define acceptable delay and how incomplete workflows are detected and reconciled.
Use compensating actions when needed; do not assume completed remote changes can simply be rolled back.

Avoid global distributed transactions unless truly necessary.

## Timeouts and Circuit Breakers
All synchronous calls need timeouts.
Set an overall deadline, pass the remaining budget to downstream calls, and stop
unnecessary work after cancellation. A timeout does not prove a remote write failed.

Use circuit breakers only where repeated dependency failures can create cascading failures.

## Resource Efficiency
- Bound concurrent requests, workers, queues, message sizes, and batches; reuse clients and connection pools.
- Define overload behavior: slow or pause intake, or reject work explicitly, instead of accumulating work in memory.
- Measure CPU, memory, latency, and throughput under representative load; budget downstream connections and capacity across all replicas.

## Security
- Authenticate service calls and enforce authorization and company isolation within each service; internal traffic is not automatically trusted.
- Restrict topic and database access to each service's needs and protect credentials and traffic.
- Validate incoming requests and events at boundaries; avoid secrets and unnecessary sensitive fields in messages or logs.

## Observability
Every service should provide:
- structured logs,
- metrics,
- health/readiness checks,
- traces.

Propagate:
- request ID,
- trace ID,
- event ID.

Monitor errors, latency, queue age, consumer lag, and resource saturation.
Keep metric labels bounded; put device/event IDs in logs or traces rather than metric labels.
Separate liveness from readiness: dependency outages should not cause restart loops,
and readiness should reflect whether the service can accept its intended work.

## Graceful Shutdown
A service should:
1. stop accepting new work,
2. stop consuming new messages,
3. finish or safely release active work,
4. commit/rollback correctly,
5. close resources,
6. exit.

Withdraw readiness before draining and enforce a shutdown deadline.
Leave unfinished messages replayable; never mark incomplete processing as successful.

## Versioning
Consider compatibility for:
- REST APIs,
- gRPC contracts,
- Kafka event schemas.

Prefer backward-compatible changes.
Test old and new producers/consumers together during rollout; remove fields only
after consumers migrate, and never reuse removed Protobuf field numbers.

## Testing
Each service should have:
- unit tests,
- integration tests,
- contract tests where useful.

Test important distributed flows.

Also test failures:
- duplicate events,
- delayed events,
- out-of-order events,
- service crash,
- unavailable DB,
- unavailable Kafka,
- slow dependency.

Cover crashes between side effects and offset commits, rebalances, overload,
company isolation, DLQ replay, and partial workflow recovery where relevant.

## Scaling
Scale measured bottlenecks only.

Examples:
- Ingestion -> multiple instances
- Telemetry Processor -> Kafka consumer group

Understand partitioning before scaling Kafka consumers.
For partition-based consumer groups, active consumers are limited by assigned
partitions; more replicas do not fix a hot partition or a saturated database.

## Migration from Monolith
Use a Strangler-style approach:

```text
modular monolith
-> choose clear boundary
-> extract one service
-> route traffic
-> observe
-> stabilize
-> extract next service
```

Do not rewrite everything at once.
Before extraction, define data ownership transfer, synchronization, traffic cutover,
and rollback. Keep one authoritative writer during migration or explicitly coordinate changes.

## Avoid
- distributed monolith,
- shared private tables or cross-service writes,
- synchronous chains everywhere,
- one service per table,
- Kafka for every operation,
- hidden coupling,
- duplicated business logic,
- unnecessary distributed transactions.

## Review Checklist
- Does this need to be a separate service?
- Is ownership clear?
- Does it own its data?
- Is gRPC actually required?
- Could this be asynchronous?
- Are duplicate events safe?
- Are failures handled?
- Is observability present?
- Are contracts backward-compatible?
- Are resource use, retries, and shutdown bounded?
- Are company isolation and service permissions enforced?
- Can interrupted processing and deployment be recovered safely?

## References
- [Kafka delivery semantics](https://kafka.apache.org/41/design/design/)
- [gRPC deadlines and cancellation](https://grpc.io/docs/guides/deadlines/)
