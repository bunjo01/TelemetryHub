# Backend Engineering Guide

## Scope
Applies to Python + FastAPI backend code.
Engineers and AI contributors must follow this guide for backend work.

Goal: maintainable, testable, production-oriented backend code.
Direct instructions such as “use”, “keep”, and “do not” state project rules;
“prefer” and “should” indicate recommendations that allow justified alternatives.
“Must” emphasizes a requirement. Explicit exceptions are identified in the guide.

## How to Use This Guide

- Read this guide before implementing or refactoring backend code. Inspect affected use cases, their callers, persistence, and relevant tests before choosing an abstraction.
- Apply these rules to new and changed code. Existing code may predate them and is not a precedent to copy blindly.
- Keep changes within the requested scope. Following this guide does not authorize a whole-application rewrite.
- Preserve API contracts, business behavior, and stored data during structural refactoring unless the task explicitly changes them.
- Document why an exception is needed and how it preserves the rule's intent. Exceptions must not silently discard security or data-integrity safeguards. Routine implementation choices do not require user approval.
- Use the database engineering guide for storage-specific decisions. The microservices architecture guide applies when services are extracted.

## General Rules
- Keep application and domain logic independent from FastAPI.
- Keep functions/classes focused on one responsibility.
- Prefer explicit code over hidden magic.
- Follow the responsibility and dependency boundaries below.
- Do not mix HTTP, business logic, and persistence in one function.
- Do not create abstractions before they are useful.
- Reuse stable business rules; accept small duplication when sharing would couple unrelated features.
- Solve current requirements with the fewest concepts needed; avoid speculative extension points.

## Architecture and Responsibility Boundaries

Use pragmatic layered architecture within a modular monolith. Organize work around
business capabilities such as companies, invitations, and devices. These boundaries
do not require a folder, service class, or domain object for every operation.

```text
api/
application/
domain/
infrastructure/
tests/
```

| Boundary | Owns | Must not own |
| --- | --- | --- |
| API | Request parsing, input-shape validation, authenticated identity, response mapping, HTTP error translation | Database queries, business workflows, transaction coordination |
| Application | Use-case orchestration, resource authorization, business decisions, transaction boundaries | HTTP responses or transport-specific exceptions |
| Domain, when useful | Substantial business rules, calculations, and state transitions | FastAPI, database drivers, network calls |
| Repositories and other infrastructure | Concrete queries, persistence operations, external integrations | Independent commits within an application-owned transaction, HTTP responses |

Application functions may depend on SQLAlchemy sessions and concrete repositories.
This is a deliberate project choice; abstract repository interfaces and a custom
unit-of-work framework are not required. Keep extracted business-rule functions
independent of HTTP and persistence libraries.

- Routes call application functions; repositories do not call routes or orchestrate application use cases.
- Authentication may use an API dependency. Enforce resource permissions in the application use case and company scope in its data access; a valid token or a client-supplied company ID is not authorization.
- Give each business rule a clear owner. Simple rules can remain in the application function; extract domain functions or objects when they isolate meaningful complexity or stable reuse.
- Modules interact through deliberate public functions or application services. Do not reach into another module's private helpers or scatter knowledge of its persistence across unrelated features.
- Use ordinary in-process calls inside the monolith. Introduce distributed communication only when an actual service boundary requires it.

### Extraction and Reuse

- Inspect existing implementations before adding a shared helper or abstraction.
- Extract code when it isolates a coherent responsibility or shares the same stable concept. Similar syntax alone does not justify coupling unrelated features.
- A function used once can deserve extraction if it makes a substantial rule or workflow easier to understand and test. Line count alone is not a reason.
- Prefer concrete repository functions and queries over generic CRUD frameworks. A repository class or interface must provide a useful boundary beyond forwarding calls.
- Keep simple CRUD simple. Do not create empty domain layers, one class per action, or extension points for hypothetical requirements.

For example, a device-deactivation route parses the device ID and maps the result.
The application function checks the actor's permission and coordinates the state
change in a transaction. The repository performs the company-scoped read or update.
A separate domain function is useful only if the transition has rules substantial
enough to warrant it.

## Implementation Workflow

Develop one coherent use case at a time through its API, application logic,
persistence, and relevant tests. Keep changes small enough to review as a complete
behavior. Scale design notes and testing to the complexity and risk of the change.

1. **Define behavior.** Identify inputs, outputs, permissions, state changes, and invariants. Define outcomes for missing resources, invalid transitions, repeated requests, and relevant failures.
2. **Design data access and transactions.** Identify required reads and writes, company scope, atomic changes, and concurrency risks. Choose constraints, atomic updates, locking, or version checks to protect the actual invariant. Define pagination and other relevant limits.
3. **Implement the smallest complete behavior.** Follow the responsibility boundaries and reuse established concepts when they match. Avoid unrelated refactoring.
4. **Verify observable outcomes.** Test meaningful business rules, API behavior, permissions, company isolation, and relevant failures. Use real PostgreSQL tests for database-dependent behavior, including constraints, rollback, and concurrent writes where applicable.
5. **Review and simplify.** Remove unnecessary indirection, check resource bounds, document significant tradeoffs, and complete the applicable checks below.

Before implementing device deactivation, for example, establish who may deactivate,
what a repeated request does, whether history remains readable, and how ingestion
should treat an inactive device. Those decisions become acceptance criteria; this
example does not prescribe the product policy.

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
- Application use cases own transaction boundaries, commit, and rollback. Repositories participate in the caller's transaction and may flush, but must not independently commit or roll back it.
- Keep operations that must succeed together in one transaction. Do not compose application functions that independently commit when the overall workflow must be atomic.
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

Clear code boundaries support maintainability. Runtime scalability requires evidence
from query behavior and representative workloads; additional layers or services do
not establish capacity. Define workload and latency/throughput targets when doing
performance work, then measure before and after the change.

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
Ruff is configured and pytest is declared in the development dependencies in
`pyproject.toml`. Pyright is intended for type checking but is not yet declared or
configured there. Type annotations alone do not establish that type checking passes.
Configure the checker when introducing it; do not claim unavailable checks passed.

Before merge of application-code changes, run from `backend/`:
- `ruff check .` and `ruff format --check .`.
- `python -m pytest` for the relevant tests; run the full suite when changing shared authentication, dependencies, or persistence behavior.
- Configured type checks, once available.

PostgreSQL integration tests require `TEST_DATABASE_URL` pointing to a migrated,
disposable test database. Skipped database tests are not evidence that database
behavior passed. Report skipped checks, unavailable dependencies, and untested
behavior. Remove debug and dead code, and keep relevant API documentation and
migrations aligned with the implementation.

Automate important rules where practical through linting, type checks, behavioral
tests, and database constraints. Manual review still checks responsibility ownership,
appropriate abstractions, transaction design, and resource bounds.

For documentation-only changes, review consistency and examples and run
`git diff --check`. Application tests are not required unless executable code or
configuration also changes.

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
- Are acceptance criteria clear, including repeated requests and relevant state transitions?
- Does the application own the transaction, with repositories participating without independent commits?
- Are module interactions deliberate, without dependence on private implementation details?
- Are performance claims backed by measurements, and skipped or unavailable checks reported?
