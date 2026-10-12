#!/usr/bin/env python3
"""Cross-platform, single-process launcher. Uses only Python's standard library."""

import argparse
import hashlib
import os
import shutil
import socket
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(command, cwd=ROOT):
    print("\n> " + " ".join(str(p) for p in command), flush=True)
    subprocess.run([str(p) for p in command], cwd=cwd, check=True)


def main():
    parser = argparse.ArgumentParser(description="Install and run your local AgentArena workspace")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--host", default="127.0.0.1", help="Keep loopback for local use; do not expose untrusted traces publicly"
    )
    parser.add_argument("--rebuild", action="store_true", help="Rebuild UI from source; requires Node 20.19+ and npm")
    parser.add_argument(
        "--reload", action="store_true", help="Enable auto-reload on code changes (dev mode)"
    )
    parser.add_argument(
        "--check", action="store_true", help="Install/check dependencies and UI, then exit without starting a server"
    )
    args = parser.parse_args()
    if sys.version_info < (3, 11):
        parser.error("Python 3.11+ is required. Install Python 3.12 or 3.13 and try again.")
    if not 1 <= args.port <= 65535:
        parser.error("Port must be between 1 and 65535")
    os.chdir(ROOT)
    print("\n  AgentArena / Intelligence, measured.\n  Local workspace setup\n", flush=True)
    env = ROOT / ".venv"
    python = env / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not python.exists():
        print("Creating a private Python environment…", flush=True)
        run([sys.executable, "-m", "venv", env])
    digest = hashlib.sha256((ROOT / "pyproject.toml").read_bytes()).hexdigest()
    marker = env / "arena-installed"
    if not marker.exists() or marker.read_text().strip() != digest:
        print("Installing the SDK and backend. Internet is needed for this first install.", flush=True)
        run([python, "-m", "pip", "install", "-e", "."])
        marker.write_text(digest)
    else:
        print("Python environment is ready.", flush=True)
    frontend = ROOT / "frontend"
    if args.rebuild or not (frontend / "dist/index.html").exists():
        npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
        node = shutil.which("node")
        if not npm or not node:
            parser.error(
                "The prebuilt UI is missing. Install Node.js 20.19+ (22 LTS recommended), then rerun; or extract the full release ZIP."
            )
        version = subprocess.check_output([node, "--version"], text=True).strip().lstrip("v")
        parts = tuple(int(p) for p in version.split(".")[:2])
        if parts < (20, 19):
            parser.error(f"Node {version} is too old for the supported setup. Install Node 22 LTS.")
        run([npm, "ci"], cwd=frontend)
        run([npm, "run", "build"], cwd=frontend)
    else:
        print("Bundled frontend is ready; Node.js is not needed.", flush=True)
    run(
        [
            python,
            "-c",
            "from arena_server.main import app; from agent_arena import Agent; print('SDK and API imports OK')",
        ]
    )
    if args.check:
        print("\nSetup verified. Run this command again without --check to start.")
        return
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as check:
            check.bind((args.host, args.port))
    except OSError:
        parser.error(f"Cannot bind {args.host}:{args.port}. Stop the other process or add --port 8002.")
    print(
        f"\nOpen http://localhost:{args.port}\nKeep this terminal open. Ctrl+C stops the app.\nData stays in {os.environ.get('ARENA_DATA_DIR', str(ROOT / '.arena'))}\n",
        flush=True,
    )
    # One worker only: the executor is intentionally in-process.
    serve_cmd = [python, ROOT / "scripts/serve.py", "--host", args.host, "--port", str(args.port)]
    if args.reload:
        serve_cmd.append("--reload")
    run(serve_cmd)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped. Your workspace data is preserved.")
    except subprocess.CalledProcessError as error:
        print(
            f"\nSetup/startup failed (exit {error.returncode}). See the command and error above.\nTroubleshooting: README.md",
            file=sys.stderr,
        )
        sys.exit(error.returncode or 1)
