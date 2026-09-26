# Database Engineering Guide

## Scope
Applies to PostgreSQL, Redis, MongoDB, and ScyllaDB.

Goal: use each database for the workload it solves best.

## General Rules
- Choose storage based on access patterns.
- Define important reads/writes before designing schema.
- Avoid multiple databases for the same responsibility.
- Keep ownership clear.
- Measure before optimizing.
- Treat schema evolution as application development.

# PostgreSQL

## Use For
Relational and transactional business data:

```text
companies
users
devices
locations
alert rules
alerts
```

## Rules
- Normalize first; denormalize only for a measured reason.
- Use primary keys, foreign keys, and useful constraints.
- Use transactions for atomic business operations.
- Keep transactions short.
- Index based on real query patterns.
- Avoid indexing every column.
- Check query plans for slow queries.
- Use pagination for large result sets.
- Avoid N+1 queries.

# Redis

## Use For

```text
latest device state
cache
rate limiting
temporary counters
short-lived processing state
```

Redis is not the primary historical store.

## Rules
- Define why a value is cached.
- Use TTL where appropriate.
- Use clear key names.

Example:

```text
device:{device_id}:latest
```

- Avoid huge values.
- Assume cached data can disappear.
- Define fallback behavior if Redis is unavailable.

# MongoDB

## Use For
Flexible device configuration or metadata that differs greatly between device types.

## Rules
- Flexible schema does not mean no schema.
- Validate document structure.
- Design around common queries.
- Embed data that belongs and is read together.
- Reference independently changing/high-cardinality data.
- Avoid uncontrolled document growth.
- Index frequent query fields.
- Version documents if schema evolves significantly.

# ScyllaDB

## Use For
High-volume telemetry history.

Typical query:

```text
Get telemetry for device X
between time A and time B.
```

## Rules
- Model tables around queries.
- Do not model it like PostgreSQL.
- Avoid unbounded partitions.
- Use time bucketing where needed.
- Choose partition keys carefully.
- Use clustering keys for ordered reads.
- Avoid expensive cross-partition queries in hot paths.
- Duplicate data across tables when query patterns justify it.

Possible idea:

```text
partition: device_id + day
clustering: timestamp
```

The exact schema must follow actual query requirements.

# Data Ownership
In the distributed version, services should own their data.

Other services should use APIs or events rather than querying private tables.

# Migrations
For relational databases:
- use migrations,
- never patch production schema manually,
- review migrations,
- prefer backward-compatible rollouts.

For NoSQL:
- version documents/events where necessary,
- support old/new formats during migrations when needed.

# Consistency
Use strong consistency where the business requires it.

Use eventual consistency where asynchronous processing is acceptable.

Do not force one consistency model everywhere.

# Backups and Recovery
Know what is:
- permanent,
- reconstructable,
- worth backing up.

Example:

```text
PostgreSQL -> critical business data
Redis -> reconstructable cache/state
Kafka -> retention-based event history
Scylla -> historical telemetry
```

# Security
- Use least-privilege DB users.
- Do not expose DBs publicly.
- Never hard-code credentials.
- Keep secrets out of Git.
- Validate external input.
- Do not log secrets.

# Testing
Test:
- repository behavior,
- constraints,
- transactions,
- migrations,
- critical query performance,
- Redis fallback behavior,
- Mongo document compatibility,
- Scylla query patterns.

Prefer real database instances for integration tests.

# Performance
Before optimizing:
1. measure,
2. identify bottleneck,
3. inspect query,
4. inspect indexes/partitioning,
5. change,
6. measure again.

# Avoid
- MongoDB just because relational modeling feels difficult,
- Redis as permanent storage,
- Scylla modeled like SQL,
- shared tables across services,
- indexing everything,
- long transactions,
- huge Mongo documents,
- unbounded Scylla partitions.

# Review Checklist
- Is this the right database?
- What are the main reads?
- What are the main writes?
- Are indexes justified?
- Are partitions bounded?
- Are transactions clear?
- Who owns the data?
- What happens if the DB is unavailable?
- Are schema changes safely deployable?
