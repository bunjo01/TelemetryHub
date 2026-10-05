# IoTMonitor backend

Requires Python 3.13 or newer. Run these commands from `backend/`.

## Install

On Debian/Ubuntu, if virtual environment creation reports that `ensurepip` is
missing, install the matching Python package first:

```sh
sudo apt install python3.13-venv
```

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

## Run locally

```sh
fastapi dev
```

Interactive API documentation: http://127.0.0.1:8000/docs

Health endpoint: http://127.0.0.1:8000/health

## Lint and format

```sh
ruff check .
ruff check . --fix
ruff format .
```

For checks that do not modify files:

```sh
ruff check .
ruff format --check .
```

Dependencies and tool settings live in `pyproject.toml`. The application starts
in `app/main.py`.

## Owner invitations

An active system administrator can call
`POST /companies/{company_id}/owner-invitations` with a bearer access token and
a JSON body containing only `email`. The email is trimmed and lowercased.

The response is `201` with the invitation ID, company ID, email, role,
expiration time, and a random `token`. For local development, manually share
this token with the intended recipient. It is returned only at creation;
only its SHA-256 hash is persisted. Do not log or commit the token.
The response uses `Cache-Control: no-store`.

`INVITATION_EXPIRE_HOURS` defaults to 24 (allowed range: 1–168).
A missing company returns `404`. An inactive company, an existing owner
(including an inactive owner), an email already registered, or an unexpired
pending owner invitation returns `409`. After expiry, a new invitation can
be issued. Creation locks the company row to serialize competing requests;
invitation acceptance uses the same company lock and rechecks
ownership and email availability. Creation does not reserve the email globally.

Creation does not create an owner account or send email.

## Member invitations

An active company owner can call
`POST /companies/{company_id}/member-invitations` with their bearer token and
a JSON body containing only `email`. The requested company must match the
owner's company. Members, system administrators, and owners of other companies
receive `403`; the endpoint does not grant owner or administrator roles.

The response is `201` with the same invitation fields as owner creation, but
`role` is always `member`. Only the token hash is persisted. The same expiration
configuration and one-time token response apply.

The company must be active and the email must not already have an account.
Only one unexpired pending member invitation per company/email is allowed;
different emails can be invited independently. Company locking serializes
duplicate creation attempts. Conflicts return `409`. Invitations to the same
email from different companies may coexist, but only one can create an account
because account emails are globally unique.

## Accepting invitations

Call `POST /invitations/accept` without an access token. Send a JSON body with
`token` (the 43-character invitation token) and `password` (15–128 characters).
Passwords are preserved exactly, including whitespace. Email, role, and company
are taken from the invitation; additional input fields are rejected.

Success returns `201` with the public user fields and `Cache-Control: no-store`.
The new owner or member can then log in through `/auth/login`. No access token is issued
by acceptance itself.

Unknown, expired, used, or unsupported invitations return a generic `400`.
An inactive company, an existing owner (for owner invitations), or an email that has since registered
returns `409`. Invalid input returns `422`; overload or database availability
failures return `503`. Overload responses include `Retry-After: 1`.

Account insertion and marking the invitation accepted share one transaction.
Password hashing runs outside that transaction, followed by locked revalidation.
Login and acceptance share the per-process `LOGIN_MAX_CONCURRENT` capacity
budget to bound simultaneous password work. This is a concurrency limit, not
a per-client rate limiter. Acceptance uses the stored invitation role, never a
client-supplied role. Email delivery is not included yet.

## Tests

Run `python -m pytest` from `backend/`. PostgreSQL invitation tests are skipped
unless `TEST_DATABASE_URL` points to a migrated PostgreSQL test database with
CRUD permissions on companies, users, and invitations. These tests wrap their
data in an outer transaction and roll it back, including on failure. The
concurrency test needs independent connections, so it commits uniquely
identified fixtures and deletes those test rows in a `finally` block. Use a
disposable test database for these integration tests.
