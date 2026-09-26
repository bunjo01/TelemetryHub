# Backend Engineering Guide

## Scope
Applies to Python + FastAPI backend code.

Goal: maintainable, testable, production-oriented backend code.

## General Rules
- Keep business logic independent from FastAPI where possible.
- Keep functions/classes focused on one responsibility.
- Prefer explicit code over hidden magic.
- Keep dependencies flowing toward domain/application logic.
- Do not mix HTTP, business logic, and persistence in one function.
- Do not create abstractions before they are useful.

## Suggested Layers

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
- Use `async` only for real asynchronous I/O.
- Do not mix sync and async carelessly.

## Naming
Use:
- `snake_case` for variables/functions/modules,
- `PascalCase` for classes,
- `UPPER_SNAKE_CASE` for constants.

Prefer descriptive names:

```python
get_active_alerts()
```

Avoid:

```python
process_data()
handle_thing()
```

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

## Error Handling
Distinguish:
- validation errors,
- not found,
- authorization errors,
- business-rule violations,
- infrastructure failures,
- unexpected errors.

Map internal errors to HTTP/gRPC responses at the boundary.

Do not use exceptions for normal control flow.

## Persistence
- Use repositories where they improve separation.
- Keep transactions explicit.
- Avoid hidden database calls.
- Avoid N+1 queries.
- Keep transactions short.
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

## Configuration
Configuration must not be hard-coded.

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

Retries must be bounded.

## Testing
### Unit
Test:
- domain rules,
- use cases,
- validation,
- transformations.

### Integration
Test:
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
- validation,
- error responses,
- important endpoints.

General:
- test behavior, not implementation,
- avoid mocking everything,
- keep tests deterministic,
- add regression tests for fixed bugs.

## Tooling
Use:
- Ruff,
- Pyright,
- pytest.

Before merge:
- lint passes,
- format passes,
- type checks pass,
- tests pass,
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
