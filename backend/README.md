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
future invitation acceptance must use the same company lock and recheck
ownership and email availability. Creation does not reserve the email globally.

This endpoint does not create an owner account or send email. Invitation
acceptance is not implemented yet.

## Tests

Run `python -m pytest` from `backend/`. PostgreSQL invitation tests are skipped
unless `TEST_DATABASE_URL` points to a migrated PostgreSQL test database with
CRUD permissions on companies, users, and invitations. These tests wrap their
data in an outer transaction and roll it back, including on failure.
