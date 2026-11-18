# Local pre-commit checks

Install backend development dependencies into `backend/.venv` (Python 3.13+),
including Ruff, pytest, and python-dotenv. Install frontend dependencies with
`npm ci` in `frontend/`, then install its browser with
`npx playwright install chromium`. See each application's README for setup.

Backend commits require a running, migrated PostgreSQL test database and a
nonempty `TEST_DATABASE_URL` in the environment or `backend/.env`. An explicitly
set environment variable takes precedence, including an empty value, which fails.
The hook never creates or migrates databases.

## Enable once per clone

From the repository root, inspect existing hook configuration:

```sh
git config --get core.hooksPath
```

No output means no custom hook path is configured. If another path is configured,
resolve that existing setup before replacing it. Otherwise enable this hook:

```sh
git config --local core.hooksPath .githooks
```

The hook uses `backend/.venv/bin/python`; activating the environment is unnecessary.
This environment is required even for frontend commits. Setup targets Linux/macOS.
Hook configuration is local and must be repeated by each developer.

## Behavior

- Any staged backend path triggers Ruff lint/format checks on staged Python paths,
  then the entire pytest suite.
- Any staged frontend path triggers Biome checks on supported staged paths, then
  the entire Vitest and Playwright suites. Existing Biome exclusions still apply.
- All affected lint and formatting checks must pass before any tests run.
  Changes in both folders run backend checks, frontend checks, backend tests,
  then frontend tests.
- Documentation and deletions also trigger their folder's tests. Deleted files
  are not linted; renames trigger both affected folders and lint the destination.
- Paths outside those folders do not trigger checks. Standalone SCSS is not
  covered by the existing formatter configuration.
- Lint warnings also block the commit. The first failure stops the hook before
  tests run. Nothing is automatically fixed or staged.

Checks select paths from the index but read working-directory contents. Tests also
run against the working directory. Unstaged edits, including partial staging, can
therefore affect the results; this is not isolated validation of the staged snapshot.

## Fix a failed check

From the relevant application folder, run the appropriate command with the actual
file paths, inspect its changes, and stage the intended fixes before retrying:

```sh
npx biome check --write src/path/to/file.vue
```

```sh
.venv/bin/python -m ruff check --fix app/path/to/file.py
.venv/bin/python -m ruff format app/path/to/file.py
```

To run the hook without creating a commit, stage the intended files and run
`.githooks/pre-commit` from the repository root. This runs the real affected suites.
Missing test tools or browser binaries must be installed before retrying.

To disable this local setup, use `git config --local --unset core.hooksPath`.
Local hooks are developer checks, not a substitute for future CI enforcement.
