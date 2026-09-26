# Microservices Architecture Guide

## Scope
Applies after modules are extracted from the modular monolith.

Goal: keep the distributed system understandable, reliable, and loosely coupled.

## Core Principle
Do not create a microservice without a clear reason.

Good reasons:
- different scaling needs,
- clear domain ownership,
- separate lifecycle,
- independent deployment value,
- high-volume workload.

Do not create one service per entity or table.

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

Avoid shared databases between independent services.

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

## Idempotency
Assume messages and some requests can be delivered more than once.

Use stable identifiers:
- `event_id`
- `request_id`
- `idempotency_key`

Repeated processing must not create incorrect duplicate side effects.

## Retries
Retry only transient failures.

Use:
- bounded attempts,
- timeout,
- exponential backoff,
- jitter.

Do not retry permanent validation errors.

## Dead Letter Queue
Repeatedly failing messages should move to a DLQ.

Preserve:
- original event,
- error,
- retry count,
- timestamps.

The DLQ must be observable and reviewable.

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

## Eventual Consistency
Different services may temporarily hold different views of data.

Design workflows so temporary inconsistency is expected and recoverable.

Avoid global distributed transactions unless truly necessary.

## Timeouts and Circuit Breakers
All synchronous calls need timeouts.

Use circuit breakers only where repeated dependency failures can create cascading failures.

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

## Graceful Shutdown
A service should:
1. stop accepting new work,
2. stop consuming new messages,
3. finish or safely release active work,
4. commit/rollback correctly,
5. close resources,
6. exit.

## Versioning
Consider compatibility for:
- REST APIs,
- gRPC contracts,
- Kafka event schemas.

Prefer backward-compatible changes.

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

## Scaling
Scale measured bottlenecks only.

Examples:
- Ingestion -> multiple instances
- Telemetry Processor -> Kafka consumer group

Understand partitioning before scaling Kafka consumers.

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

## Avoid
- distributed monolith,
- shared databases,
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
