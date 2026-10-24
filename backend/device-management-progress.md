# Device Management

Build company-scoped device management in the existing backend, following
`backend-engineering-guide.md` and `database-engineering-guide.md`.
This document tracks the agreed scope, not a step-by-step implementation guide.
Unchecked items represent work still to complete and verify.

## Agreed Behavior

- Owners can add, edit, activate, deactivate, list, and view their company's devices.
- Members can only list and view their company's devices.
- System admins have no access to these operations.
- Users of inactive companies cannot access device operations.
- New devices start active. Inactive devices remain viewable and editable.
- Activation/deactivation preserves device identity; repeating the same action succeeds without further changes.
- Listing supports active, inactive, or all devices, defaults to active, and includes name search and bounded pagination.
- Administrative active/inactive status is separate from telemetry-derived online/offline status.
- Devices are not deleted in this milestone.

## Device Fields

| Field | Rules |
| --- | --- |
| `id` | Server-generated UUID; immutable |
| `company_id` | Derived from the authenticated user; immutable |
| `name` | Required, trimmed, 1–100 characters; duplicates allowed; editable |
| `description` | Optional, up to 1,000 characters; editable and clearable |
| `device_type` | Required at creation; immutable |
| `status` | `active` or `inactive`; changed through activation/deactivation |
| `created_at` | Server-managed UTC timestamp |
| `updated_at` | Server-managed UTC timestamp reflecting stored changes |

Supported types are `temperature_sensor`, `environment_sensor`, and `gps_tracker`.
Use a backend string enum and a PostgreSQL text column with a check constraint.
The frontend will use matching fixed values and user-friendly labels; no
`GET /device-types` endpoint is needed. Keep stored values stable and coordinate
future additions across the backend, database constraint, and frontend.

## Completion Checklist

- [ ] Finalize API requests, responses, errors, pagination limits, and concurrent-update behavior for all device operations.
- [x] Add the device model and database migration with initial constraints and company index.
- [x] Implement device registration (`POST /devices`); initial integration tests and manual request passed.
- [x] Implement device details (`GET /devices/{device_id}`); PostgreSQL integration tests passed.
- [ ] Implement listing with status filtering, name search, and pagination.
- [ ] Implement editing of name and description.
- [ ] Implement activation/deactivation, including repeated requests.
- [ ] Enforce role permissions, company isolation, and inactive-company restrictions for every operation.
- [ ] Verify API behavior, validation, permissions, and relevant persistence/concurrency behavior with tests, including PostgreSQL integration tests.
- [ ] Complete applicable engineering-guide checks and update API documentation; record any skipped checks.

## Registration Progress

- Owner-only registration derives company ownership from the authenticated user,
  rejects inactive companies, and returns an active device with generated ID and timestamps.
- Migration `a85252429830` was applied; Alembic reported no remaining schema changes.
- The initial 13 PostgreSQL integration tests passed, and a manual request returned `201 Created`.
- The development application role required `SELECT`, `INSERT`, and `UPDATE` on
  `public.devices`; this grant was applied to `iotmonitor` before the successful manual request.
- Four failure/rollback cases and two concurrency cases passed alongside the
  initial 13 registration tests in the user's PostgreSQL test run.
- [x] Confirm all 19 registration tests pass against the migrated test database.

## Device Details Progress

- Active company owners and members can view their company's active and inactive
  devices; system admins and users of inactive companies are denied access.
- The repository scopes lookups by device ID and the authenticated user's company ID.
  Missing devices and other-company devices return the same `404` response.
- The application owns authorization and the transaction, holding a shared company
  lock during the lookup to coordinate with company deactivation.
- The API returns the existing device response schema with `Cache-Control: no-store`.
  Invalid UUIDs return `422`, unavailable credentials (including inactive users)
  return `401`, permission failures return `403`, and database connection/timeout
  failures return a generic `503` response.
- All 15 details test cases passed, covering response fields and timestamps,
  active/inactive devices, owner/member access, company isolation, denied access,
  invalid IDs, sanitized database failures, and recovery after injected failures.
- On 2026-10-24, the user confirmed all 34 device tests passed against the test
  database: 19 registration cases and 15 details cases. Lint and formatting passed.
  This supersedes the assistant's earlier runs that skipped database tests because
  `TEST_DATABASE_URL` was unset.

## Deferred

Device configuration, location assignment, device credentials, telemetry ingestion,
`last_seen_at`, and online/offline detection are outside this milestone. When
ingestion is implemented, inactive devices should be prevented from submitting
new telemetry. Frontend screens are a separate implementation task.
