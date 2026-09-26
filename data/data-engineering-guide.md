# Data Engineering Guide

## Scope
Applies to telemetry analytics, batch processing, streaming, transformations, and analytical datasets.

Goal: reliable, understandable, reproducible data pipelines.

## Core Principle
Separate:

```text
raw data
processed data
analytics-ready data
```

Do not overwrite raw data without a clear retention policy.

## Suggested Flow

```text
Kafka
  ↓
Raw Layer
  ↓
Validation / Cleaning
  ↓
Transformations
  ↓
Aggregations
  ↓
Analytics Storage
  ↓
Dashboard / Reports
```

## Raw Data
Preserve the original event as much as possible.

Store metadata such as:
- `event_id`
- `device_id`
- `event_time`
- `ingestion_time`
- `schema_version`
- `source`

Raw data should be replayable.

## Event Time vs Processing Time

```text
event_time      -> when device created the measurement
processing_time -> when pipeline processed it
```

IoT data may arrive late or out of order.

Do not assume arrival order equals event order.

## Data Quality
Validate:
- missing values,
- invalid ranges,
- duplicate events,
- malformed records,
- impossible timestamps,
- unknown devices,
- incorrect units.

Do not silently drop bad records.

Track rejected records and reasons.

## Transformations
Transformations should be:
- deterministic where possible,
- testable,
- documented,
- reproducible.

Examples:
- Fahrenheit -> Celsius
- normalize timestamp
- derive `temperature_violation`
- add `company_id`
- add `location_id`

Avoid giant jobs containing unrelated transformations.

## Idempotency and Deduplication
Pipelines may process the same event more than once.

Use stable IDs such as `event_id`.

Repeated execution must not corrupt results.

## Batch Processing
Use batch processing for:
- daily statistics,
- historical recalculation,
- large backfills,
- report preparation.

Batch jobs must be safely rerunnable.

## Streaming
Use streaming for:
- near-real-time telemetry,
- live aggregates,
- fresh dashboards,
- real-time anomaly signals.

Do not introduce distributed stream processing if normal consumers are sufficient.

## Aggregations
Create analytical datasets around real business questions.

Examples:
- `device_hourly_stats`
- `company_daily_stats`
- `alert_daily_stats`
- `device_uptime_stats`

Possible metrics:
- average temperature,
- min/max temperature,
- event count,
- violation count,
- uptime,
- downtime.

## Storage
Prefer Parquet for larger analytical datasets.

Use S3/MinIO-style object storage for file-based raw/processed layers.

Partition files by useful dimensions, for example:

```text
year/month/day/company
```

Avoid millions of tiny files.

## Pandas vs PySpark
Use Pandas when data fits comfortably on one machine.

Use PySpark when:
- data size justifies distributed processing,
- the workload requires it,
- or distributed processing is an explicit learning goal.

Do not use Spark for tiny datasets.

## Airflow
Use Airflow for orchestration, not heavy processing itself.

It should coordinate steps such as:

```text
extract
transform
validate
load
```

Jobs should be:
- idempotent,
- retryable,
- observable,
- independently testable.

## Data Contracts
Producers and consumers should agree on event structure.

Include a `schema_version` when useful.

Prefer backward-compatible changes.

Do not silently change field meaning.

## Monitoring
Track:
- records processed,
- records rejected,
- processing duration,
- consumer lag,
- job success/failure,
- data freshness,
- late events,
- duplicate rate.

A job can succeed technically while producing bad data.

## Testing
### Unit Tests
Test:
- transformations,
- aggregations,
- validation rules.

### Pipeline Tests
Test known input against expected output.

### Data Quality Tests
Check:
- null rates,
- uniqueness,
- valid ranges,
- row counts,
- freshness.

### Integration Tests
Test:
- Kafka ingestion,
- object storage,
- analytical storage,
- scheduled jobs where useful.

## Reprocessing and Backfills
Design pipelines so historical periods can be recomputed.

Example:

```text
reprocess 2026-09-01 through 2026-09-07
```

Do not build pipelines that only work for "today".

## Failure Handling
Bad records should not stop the whole pipeline unless necessary.

Possible pattern:

```text
valid data   -> normal pipeline
invalid data -> quarantine/rejected dataset
```

Keep the failure reason.

## Naming
Prefer descriptive names.

Good:

```text
raw_telemetry
processed_telemetry
device_hourly_stats
calculate_device_uptime
```

Avoid:

```text
data2
final_table
temp_final_v3
```

## Documentation
Each important dataset should document:
- purpose,
- source,
- owner,
- grain,
- key fields,
- update frequency,
- known limitations.

Example grain:

```text
one row per device per hour
```

## Avoid
- silent data loss,
- hidden transformations,
- Spark for small data,
- giant untestable pipelines,
- assuming events arrive in order,
- non-idempotent jobs,
- unclear dataset grain,
- meaningless names like `final`.

## Review Checklist
- What is the dataset grain?
- What is raw vs processed?
- Can this job be safely rerun?
- How are duplicates handled?
- How are late events handled?
- Are bad records observable?
- Are transformations tested?
- Is freshness measurable?
- Is Spark actually necessary?
- Can historical data be reprocessed?
