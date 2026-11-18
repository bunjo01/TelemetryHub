import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYTHON = ROOT / "backend/.venv/bin/python"


def staged_paths() -> tuple[set[str], set[str]]:
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-status", "-z", "--find-renames"],
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
    )
    fields = iter(os.fsdecode(result.stdout).split("\0")[:-1])
    affected = set()
    existing = set()
    for status in fields:
        path = next(fields)
        affected.add(path)
        if status.startswith(("R", "C")):
            path = next(fields)
            affected.add(path)
        if status != "D":
            existing.add(path)
    return affected, existing


def run(label: str, command: list[str], directory: Path) -> None:
    print(f"Pre-commit: {label}", flush=True)
    subprocess.run(command, cwd=directory, check=True)


def check_frontend(paths: set[str]) -> None:
    directory = ROOT / "frontend"
    biome = directory / "node_modules/.bin/biome"
    if not biome.is_file() or shutil.which("npm") is None:
        raise RuntimeError("Install Node.js and run npm ci inside frontend first.")
    files = sorted(
        path.removeprefix("frontend/")
        for path in paths
        if path.startswith("frontend/")
        and Path(path).suffix in {".js", ".vue", ".html", ".json"}
        and path != "frontend/package-lock.json"
    )
    if files:
        run(
            "frontend lint and formatting",
            [
                str(biome),
                "check",
                "--error-on-warnings",
                "--no-errors-on-unmatched",
                "--",
                *files,
            ],
            directory,
        )


def check_backend(paths: set[str]) -> None:
    directory = ROOT / "backend"
    files = sorted(
        path.removeprefix("backend/")
        for path in paths
        if path.startswith("backend/") and path.endswith(".py")
    )
    if files:
        run(
            "backend lint",
            [str(PYTHON), "-m", "ruff", "check", "--", *files],
            directory,
        )
        run(
            "backend formatting",
            [str(PYTHON), "-m", "ruff", "format", "--check", "--", *files],
            directory,
        )


def test_backend() -> None:
    from dotenv import dotenv_values

    directory = ROOT / "backend"
    url = os.environ.get("TEST_DATABASE_URL")
    if "TEST_DATABASE_URL" not in os.environ:
        url = dotenv_values(directory / ".env").get("TEST_DATABASE_URL")
    if not url or not url.strip():
        raise RuntimeError(
            "Set TEST_DATABASE_URL to a migrated PostgreSQL test database "
            "in the environment or backend/.env before committing backend changes."
        )
    os.environ["TEST_DATABASE_URL"] = url
    run("all backend tests", [str(PYTHON), "-m", "pytest"], directory)


def test_frontend() -> None:
    directory = ROOT / "frontend"
    run("all frontend unit tests", ["npm", "test"], directory)
    run("all frontend browser tests", ["npm", "run", "test:e2e"], directory)


def main() -> int:
    try:
        affected, existing = staged_paths()
        backend_changed = any(path.startswith("backend/") for path in affected)
        frontend_changed = any(path.startswith("frontend/") for path in affected)
        if backend_changed:
            check_backend(existing)
        if frontend_changed:
            check_frontend(existing)
        if backend_changed:
            test_backend()
        if frontend_changed:
            test_frontend()
    except subprocess.CalledProcessError:
        print("Pre-commit: checks failed; commit blocked.", file=sys.stderr)
        return 1
    except (OSError, RuntimeError, ImportError) as error:
        print(f"Pre-commit: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
