# Telemetry Event Contract — v1

|                |                                                      |
| -------------- | ---------------------------------------------------- |
| Status         | Draft, to be agreed by backend and data owners       |
| Direction      | Device (or simulator) → telemetry ingestion endpoint |
| Owners         | Backend (endpoint), Data (simulator, pipeline)       |
| Schema version | `1`                                                  |

This document is the only thing the simulator, the backend and the data pipeline share.
None of them may import each other's code to learn the event format.

---

## 1. Transport

| Item            | Value                                                |
| --------------- | ---------------------------------------------------- |
| Method and path | `POST /api/v1/telemetry` (proposed, backend decides) |
| Content type    | `application/json`                                   |
| Body            | One telemetry event per request                      |
| Max body size   | 4 KB                                                 |
| Authentication  | Header `X-Device-Key: <device api key>`              |

The API key identifies the device. The `device_id` in the body must belong to that key.

---

## 2. Event fields

| Field            | Type           | Required | Unit / format                | Valid range                     |
| ---------------- | -------------- | -------- | ---------------------------- | ------------------------------- |
| `schema_version` | integer        | yes      | —                            | exactly `1`                     |
| `event_id`       | string (UUID)  | yes      | lowercase UUID               | —                               |
| `device_id`      | string (UUID)  | yes      | lowercase UUID               | must match the API key's device |
| `event_time`     | string         | yes      | RFC 3339, UTC, ends with `Z` | see section 4                   |
| `temperature_c`  | number or null | no       | degrees Celsius              | -50 to 100                      |
| `humidity_pct`   | number or null | no       | percent relative humidity    | 0 to 100                        |
| `battery_pct`    | number or null | no       | percent                      | 0 to 100                        |
| `latitude`       | number or null | no       | decimal degrees, WGS84       | -90 to 90                       |
| `longitude`      | number or null | no       | decimal degrees, WGS84       | -180 to 180                     |

No other fields are allowed in v1. Unknown fields are rejected.

---

## 3. Field rules

### `event_id`

- Generated **by the device** when the measurement is taken.
- A device that resends an event (retry, reconnect, buffered upload) **must reuse the same `event_id`**.
- `event_id` is how the platform recognizes duplicates. A new ID on resend makes a duplicate look like a new measurement.

### Measurements

- Missing field and `null` mean the same thing in v1: "no value for this metric".
- `null` never means `0`. A device without a humidity sensor sends `null` or omits the field.
- At least one of `temperature_c`, `humidity_pct`, `battery_pct`, `latitude`/`longitude` must be non-null.
- `latitude` and `longitude` are sent together: both set or both null.
- The valid ranges in section 2 are **physical plausibility checks**, not business rules.
  `9.4` °C is a valid event even if a company's rule says 2–8 °C. Business thresholds live in alert rules, never in this contract.

### Fields the device must not send

- `company_id`, `location_id`, `device_type`: the platform looks these up from the authenticated device.
  A client must never be trusted to declare its own tenant.
- `ingestion_time`: set by the platform on receipt.

---

## 4. Time

- All timestamps are UTC with the `Z` suffix, for example `2026-09-29T10:30:00Z` or `2026-09-29T10:30:00.250Z`.
- Timestamps with other offsets (`+02:00`) are rejected in v1.
- `event_time` is **when the device measured the value**, not when it was sent.
- Events may arrive late, duplicated or out of order. Receivers must not assume arrival order equals `event_time` order.
- Two events from the same device may have the same `event_time`. They are different events if their `event_id` differs.

Proposed acceptance window (backend decides the final values):

| Condition                                      | Result                        |
| ---------------------------------------------- | ----------------------------- |
| `event_time` more than 5 minutes in the future | rejected (clock error)        |
| `event_time` older than 7 days                 | rejected (too late to accept) |
| anything in between, including late events     | accepted                      |

---

## 5. Responses

| Status                     | Meaning                                                        | Device should                       |
| -------------------------- | -------------------------------------------------------------- | ----------------------------------- |
| `202 Accepted`             | Event accepted, **or** already received with identical payload | stop, event is delivered            |
| `400 Bad Request`          | Malformed JSON or body too large                               | not retry, log it                   |
| `401 Unauthorized`         | Missing or unknown API key                                     | not retry                           |
| `403 Forbidden`            | Device deactivated, or `device_id` does not match the key      | not retry                           |
| `409 Conflict`             | Same `event_id` already received with a **different** payload  | not retry, log it                   |
| `422 Unprocessable Entity` | Valid JSON but a field breaks the rules above                  | not retry, log it                   |
| `429 Too Many Requests`    | Rate limit reached                                             | retry after `Retry-After`           |
| `5xx` or timeout           | Temporary server failure                                       | retry with backoff, same `event_id` |

A duplicate returns `202`, not an error: the device's goal, "the platform has this event", is achieved.

Error responses use one shape:

```json
{
  "error": {
    "code": "invalid_field",
    "message": "humidity_pct must be between 0 and 100",
    "field": "humidity_pct"
  }
}
```

### Device retry policy

- Retry only on `429`, `5xx` and timeouts.
- Exponential backoff with jitter, starting at 1 second, capped at 60 seconds.
- Every retry resends the **identical** body, including `event_id`.

---

## 6. Examples

### Cold storage sensor (no GPS)

```json
{
  "schema_version": 1,
  "event_id": "3f1c9a52-7b4e-4d2a-9c61-0e8f5a2b7d14",
  "device_id": "a7d2e4f1-5c3b-4e89-8f02-6b1d9c3e7a50",
  "event_time": "2026-09-29T10:30:00Z",
  "temperature_c": 4.2,
  "humidity_pct": 61.0,
  "battery_pct": 78.0,
  "latitude": null,
  "longitude": null
}
```

### Vehicle tracker

```json
{
  "schema_version": 1,
  "event_id": "9b0e7c3d-2a4f-4b1e-8d6c-5f3a1e9b2c70",
  "device_id": "c1f8b3a2-9d4e-4f7a-b6c5-2e0d8a1f3b94",
  "event_time": "2026-09-29T10:30:30.500Z",
  "temperature_c": 5.1,
  "battery_pct": 64.5,
  "latitude": 45.2671,
  "longitude": 19.8335
}
```

### Rejected examples

| Body problem                                | Status                        |
| ------------------------------------------- | ----------------------------- |
| `"event_time": "2026-09-29T12:30:00+02:00"` | `422`, not UTC `Z`            |
| `"humidity_pct": 140`                       | `422`, out of range           |
| only `latitude` set, `longitude` missing    | `422`, coordinates incomplete |
| all measurement fields null                 | `422`, no measurement         |
| extra field `"company_id": "..."`           | `422`, unknown field          |

---

## 7. Versioning

- Any change to a field's meaning, unit or type requires `schema_version: 2`.
- Adding a new **optional** field is allowed in a new version; old devices keep sending v1.
- The platform accepts every version it has not officially retired.
- A field is never reused with a different meaning.

---

## 8. Open questions

1. Batch endpoint for devices uploading buffered events after reconnect (for example `POST /api/v1/telemetry/batch`, max 100 events)?
2. Final acceptance window for late and future events (section 4).
3. Rate limit per device.
4. How device API keys are issued and rotated.
