# Backend Engineering Guide

## Scope
Applies to Python + FastAPI backend code.
Engineers and AI contributors should follow these rules.

Goal: maintainable, testable, production-oriented backend code.
Preferences allow justified exceptions; mandatory safeguards use “must”.

## General Rules
- Keep business logic independent from FastAPI where possible.
- Keep functions/classes focused on one responsibility.
- Prefer explicit code over hidden magic.
- Keep dependencies flowing toward domain/application logic.
- Do not mix HTTP, business logic, and persistence in one function.
- Do not create abstractions before they are useful.
- Reuse stable business rules; accept small duplication when sharing would couple unrelated features.
- Solve current requirements with the fewest concepts needed; avoid speculative extension points.

## Suggested Layers

Use these boundaries as the application grows, not as mandatory folders for every feature.
Avoid interfaces or wrappers that only forward calls without a useful boundary.

```text
api/
application/
domain/
infrastructure/
tests/
```

Responsibilities:

```text
api            -> HTTP/gRPC boundaries
application    -> use cases and orchestration
domain         -> business rules and domain objects
infrastructure -> databases, Kafka, Redis, external systems
```

The domain should not depend directly on FastAPI or database drivers.

## Python Style
- Use type hints.
- Avoid `Any` unless justified.
- Prefer small, explicit functions.
- Prefer early returns over deep nesting.
- Avoid mutable default arguments.
- Avoid global mutable state.
- Follow idiomatic Python and existing project conventions; prefer standard-library solutions when sufficient.
- Use `async` to coordinate asynchronous I/O; it does not make CPU-heavy work faster.
- Keep blocking I/O and expensive CPU work off the event loop using an appropriate, bounded execution mechanism.
- Preserve cancellation and use context managers or `finally` to release resources on every exit path.

## Naming
Use:
- `snake_case` for variables/functions/modules,
- `PascalCase` for classes,
- `UPPER_SNAKE_CASE` for constants.

Choose names that explain the domain and action in context, such as `get_active_alerts()`.
Avoid vague names such as `handle_thing()` and unnecessary abbreviations.
Include units when ambiguous (`timeout_seconds`) and distinguish `event_time` from `ingestion_time`.

## API Design
- Use REST semantics correctly.
- Validate all external input.
- Return consistent responses.
- Use appropriate HTTP status codes.
- Keep endpoints thin.
- Do not leak stack traces/internal details.
- Prefer resource-oriented routes.

## Validation
Validate at boundaries:
- HTTP,
- Kafka,
- gRPC,
- external data.

Separate:
- format validation,
- business validation,
- authorization.

Bound request sizes, collection lengths, page sizes, and query time ranges.
Authorization must enforce company isolation for every resource access; valid input alone is not permission.

## Error Handling
Distinguish:
- validation errors,
- not found,
- authorization errors,
- business-rule violations,
- infrastructure failures,
- unexpected errors.

Map internal errors to HTTP/gRPC responses at the boundary.

Use exceptions idiomatically for failures; prefer simple branching for routine decisions.
Catch errors where they can be handled meaningfully, preserve their cause, and never silently swallow failures.

## Persistence
- Use repositories where they improve separation.
- Make transaction ownership, commit, and rollback explicit.
- Avoid hidden database calls.
- Avoid N+1 queries.
- Keep transactions short; avoid external network calls while holding them open.
- Enforce data invariants with database constraints where possible and handle concurrent updates deliberately.
- Do not return ORM models directly from API handlers.
- Use migrations for schema changes.

## Dependency Injection
Use dependency injection for:
- repositories,
- DB sessions,
- Kafka producers,
- Redis clients,
- external services.

Avoid hidden globals and service locators.
Use ordinary parameters or FastAPI dependencies; a custom injection framework is not required.

## Configuration
Keep environment-specific settings and secrets outside code; make operational limits configurable.
Stable domain constants and safe default values can live in code.

Examples:
- database URLs,
- Kafka brokers,
- secrets,
- timeouts,
- retry limits.

Secrets must never be committed.

## Logging
Use structured logs.

Include useful context:
- request ID,
- trace ID,
- service name,
- device ID,
- event ID.

Never log:
- passwords,
- tokens,
- secrets.

## Reliability
Use where appropriate:
- timeouts,
- retries,
- exponential backoff,
- idempotency,
- graceful shutdown,
- health checks,
- circuit breakers.

Every network call should have a timeout.

Retries must have bounded attempts and an overall time budget.
Retry only transient failures when repeating the operation is safe, using backoff and jitter.
Assign retries to a clear layer so nested retries do not multiply the load.

## Resource Efficiency
- Bound concurrent work, queues, batches, and caches; define how overload is rejected or delayed.
- Paginate or stream large results; fetch needed fields and avoid loading entire datasets to filter them.
- Reuse connection pools and long-lived clients with explicit startup/shutdown ownership; keep sessions scoped to a unit of work.
- Consider algorithmic cost, repeated queries, and unnecessary copies as data grows.
- Measure CPU, peak memory, latency, and throughput on representative workloads before adding complex optimizations.

## Testing
### Unit
Test:
- domain rules,
- use cases,
- validation,
- transformations.

### Integration
Test the dependencies actually used by the feature:
- PostgreSQL,
- Redis,
- Kafka,
- MongoDB,
- ScyllaDB,
- repositories.

### API
Test:
- status codes,
- authentication,
- authorization and company isolation,
- validation,
- error responses,
- important endpoints.

General:
- test behavior, not implementation,
- avoid mocking everything,
- keep tests deterministic,
- add regression tests for fixed bugs.
- cover relevant limits, concurrent updates, duplicate requests, and dependency failures.

## Tooling
Ruff is configured in `pyproject.toml`. Pyright and pytest are the intended tools
for type checking and testing, but are not yet declared in the development dependencies.
Configure them when introducing those checks; do not claim unavailable checks passed.

Before merge:
- lint passes,
- format passes,
- configured type checks and relevant tests pass,
- missing checks or untested behavior are reported,
- no debug/dead code.

## Avoid
- fat route handlers,
- business logic inside ORM models,
- global DB sessions,
- broad `Exception` catches without reason,
- unbounded retries,
- silent failures,
- unnecessary generic abstractions,
- magic strings,
- duplicate business rules.

## Review Checklist
- Is business logic testable without FastAPI?
- Is persistence separated?
- Are transactions clear?
- Are failures explicit?
- Are timeouts/retries safe?
- Are types clear?
- Are important paths tested?
- Is company isolation enforced?
- Are resource use and concurrency bounded, with cleanup on failure?
- Does each abstraction simplify a current requirement?
