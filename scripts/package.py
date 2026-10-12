"""Build a source + precompiled UI release ZIP without data, keys, or dependencies."""

import argparse
import os
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".arena",
    "test-results",
    "playwright-report",
    "build",
    ".cache",
}
EXCLUDED_FILES = {".env", "arena-run.json", "tsconfig.tsbuildinfo", "results.json"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(ROOT.parent / "AgentArena.zip"))
    args = parser.parse_args()
    if not (ROOT / "frontend/dist/index.html").exists():
        parser.error("Build the UI first: cd frontend && npm ci && npm run build")
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for folder, dirs, names in os.walk(ROOT):
            dirs[:] = sorted(d for d in dirs if d not in EXCLUDED_DIRS and not d.endswith(".egg-info"))
            for name in sorted(names):
                path = Path(folder) / name
                if (
                    path.is_symlink()
                    or name.startswith(".arena-env-")
                    or name in EXCLUDED_FILES
                    or name.endswith((".zip", ".db", ".db-wal", ".db-shm", ".pyc", ".pem"))
                ):
                    continue
                if name.startswith(".env") and name != ".env.example":
                    continue
                archive.write(path, Path("agent-arena") / path.relative_to(ROOT))
                count += 1
    print(f"Packaged {count} files: {output} ({output.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
