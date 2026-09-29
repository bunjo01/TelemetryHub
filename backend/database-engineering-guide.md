# Database Engineering Guide

## Scope
Applies to PostgreSQL, Redis, MongoDB, and ScyllaDB.
Engineers and AI contributors should follow these rules.

Goal: use each database for the workload it solves best.
Preferences allow justified exceptions; mandatory safeguards use “must”.

## General Rules
- Choose storage based on access patterns.
- Define important reads/writes before designing schema.
- Avoid multiple databases for the same responsibility.
- Keep ownership clear.
- Measure before optimizing.
- Treat schema evolution as application development.
- Start with PostgreSQL; add other stores only for a clear workload or project requirement.
- Prefer native database features and straightforward queries over generic storage abstractions.
- Use consistent, descriptive `snake_case` schema names and document units, timestamp meaning, and retention.
- Company isolation must hold across queries, relationships, cache keys, and exports; do not trust a client-supplied company ID as authorization.

## PostgreSQL

### Use For
Relational and transactional business data:

```text
companies
users
devices
locations
alert rules
alerts
```

### Rules
- Normalize first; denormalize only for a measured reason.
- Use primary keys, foreign keys, and useful constraints.
- Use transactions for atomic business operations.
- Keep transaction ownership explicit and transactions short; avoid external calls while holding locks.
- Prevent lost updates with atomic updates, appropriate locking, or version checks; choose isolation for the invariant being protected.
- Index actual filters, joins, and sort patterns; account for write and storage cost. Foreign keys do not automatically index referencing columns.
- Check query plans for slow queries.
- Use deterministic ordering and bounded pagination; prefer keyset pagination for large sequential listings.
- Avoid N+1 queries.
- Use appropriate types: `timestamptz` for instants and exact numeric types when rounding would violate business rules.
- Keep autovacuum enabled and monitor lock waits, long transactions, and table/index growth.

## Redis

### Use For

```text
latest device state
cache
rate limiting
temporary counters
short-lived processing state
```

Redis is not the primary historical store.

### Rules
- Define the source of truth, acceptable staleness, and invalidation or refresh policy for cached values.
- Set TTLs for temporary data and explicit size limits for growing collections.
- Configure `maxmemory` and eviction policy; leave memory headroom for replication, persistence, and client buffers.
- Use namespaced keys containing company and resource identity.

Example:

```text
company:<company_id>:device:<device_id>:latest
```

- Assume cached data can disappear.
- Define bounded fallback or rejection behavior on outages; prevent simultaneous cache misses from overwhelming the primary store.
- Use atomic commands or short scripts for counters and conditional updates; prevent late telemetry from replacing newer device state.
- Avoid `KEYS` and large blocking operations in request paths; use incremental `SCAN` for maintenance and tolerate duplicate results.
- Keep values and pipelines bounded; pipelining reduces round trips but does not make operations atomic.

## MongoDB

### Use For
Flexible device configuration or metadata that differs greatly between device types.
Consider PostgreSQL JSONB first when it meets the same access and ownership needs.

### Rules
- Flexible schema does not mean no schema.
- Enforce document validation for required fields and types; flexibility does not remove invariants.
- Design around common queries.
- Embed data that belongs and is read together.
- Reference independently changing/high-cardinality data.
- Bound embedded arrays and document growth; do not append telemetry history indefinitely to a device document.
- Design compound indexes around actual filters and sorting; inspect query plans and fetch only needed fields.
- Prefer atomic single-document updates; use version conditions to detect conflicting edits and transactions when multi-document invariants require them.
- Choose read/write concern for required durability and consistency; do not assume replica reads are current.
- Version documents if schema evolves significantly.

## ScyllaDB

### Use For
High-volume telemetry history.

Typical query:

```text
Get telemetry for device X
between time A and time B.
```

### Rules
- Model tables around queries.
- Do not model it like PostgreSQL.
- Size time buckets from expected event rate and row size; validate partition size and hot-device load with representative data.
- Use clustering keys for ordered reads.
- Bound time ranges, pages, and partition fan-out; avoid full scans and `ALLOW FILTERING` in request paths.
- Duplicate data across tables only for needed queries, with a plan to repair partial writes.
- Choose replication and consistency levels together for the required failure tolerance; use conditional writes only when their extra cost is justified.
- Align TTL, compaction, and repair policy with retention; monitor tombstones and compaction backlog, including during late writes and backfills.

Possible idea:

```text
partition: (company_id, device_id, day)
clustering: (event_time, event_id)
```

This is an example, not a fixed schema. A stable event ID distinguishes readings
with the same timestamp; retries must reuse the same full primary key.
Choose bucket duration from the workload, not the example.

## Data Ownership
In the distributed version, services should own their data.

Other services should use APIs or events rather than querying private tables.

## Migrations
- Keep schema, index, and data migrations versioned and reviewed; record emergency changes in the same history.
- Prefer additive changes: deploy compatible readers/writers, backfill in bounded resumable batches, then remove old fields after consumers migrate.
- Assess locks, execution time, disk headroom, and recovery before large changes; use online/concurrent mechanisms where supported and appropriate.
- Version document and cache formats when needed and define compatibility during mixed-version deployments.

## Consistency
Use strong consistency where the business requires it.

Use eventual consistency where asynchronous processing is acceptable.

Do not force one consistency model everywhere.
Handle unknown write outcomes after timeouts: retry only when the operation is safe to repeat.
Writes across stores need recoverable coordination, such as an outbox; sequential writes are not one atomic transaction.

## Backups and Recovery
- Define acceptable data loss and recovery time; test restores, not just backup creation.
- Back up authoritative PostgreSQL, MongoDB, and ScyllaDB data according to retention requirements.
- Treat Redis state as reconstructable only when a tested source and rebuild path exist; otherwise define its durability and recovery requirements.
- Replication is not a backup. A rebuild from retained events works only while the necessary history is still available.

## Security
- Use least-privilege DB users.
- Do not expose DBs publicly.
- Never hard-code credentials.
- Keep secrets out of Git.
- Use parameterized SQL/CQL and structured driver queries; allowlist dynamic identifiers and operators rather than accepting raw query fragments.
- Protect database traffic and backups with appropriate encryption and access controls.
- Do not log secrets.

## Testing
Test the stores used by the feature:
- repository behavior,
- constraints,
- transactions,
- migrations,
- critical query performance,
- company isolation and concurrent/duplicate writes,
- Redis expiry, eviction, and outage fallback,
- MongoDB document compatibility and atomic updates,
- ScyllaDB bucket boundaries, identical timestamps, and late events.

Prefer real database instances for integration tests.

## Resource Efficiency
- Bound connection pools, concurrent queries, result sizes, and batch sizes; budget connections across all application instances.
- Set query and connection timeouts; bound lock waits where supported and keep retries within an overall deadline.
- Filter and project in the database; stream or page large results instead of materializing entire datasets in application memory.
- Measure latency, CPU, memory, disk I/O, and storage growth with realistic volumes before and after changes.
- Account for index maintenance, replication, backups, and compaction when sizing capacity; throttle backfills to protect normal traffic.

## Avoid
- MongoDB just because relational modeling feels difficult,
- relying on Redis durability without an explicit persistence and recovery design,
- Scylla modeled like SQL,
- shared tables across services,
- indexing everything,
- long transactions,
- huge Mongo documents,
- unbounded Scylla partitions.

## Review Checklist
- Is this the right database?
- What are the main reads?
- What are the main writes?
- Are indexes justified?
- Are partitions bounded?
- Are transactions clear?
- Who owns the data?
- What happens if the DB is unavailable?
- Are schema changes safely deployable?
- Are company isolation and concurrent writes safe?
- Are resource limits, retention, and recovery defined?

## References
- [PostgreSQL constraints](https://www.postgresql.org/docs/current/ddl-constraints.html)
- [Redis eviction and memory limits](https://redis.io/docs/latest/develop/reference/eviction/)
- [MongoDB data modeling](https://www.mongodb.com/docs/manual/data-modeling/) and [atomicity](https://www.mongodb.com/docs/v8.0/core/write-operations-atomicity/)
- [ScyllaDB keys and table definitions](https://docs.scylladb.com/manual/stable/cql/ddl.html) and [compaction](https://docs.scylladb.com/manual/stable/kb/compaction.html)
