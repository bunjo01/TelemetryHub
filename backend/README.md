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
