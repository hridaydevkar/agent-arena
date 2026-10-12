"""Launcher child process: load local .env, then start a single app server."""

import argparse
import os
from pathlib import Path

from dotenv import load_dotenv
import uvicorn

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--reload",
        action="store_true",
        default=os.getenv("ARENA_RELOAD", "").lower() in ("1", "true"),
        help="Enable auto-reload on code changes (dev mode)",
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    env = root / ".env"
    if env.is_file():
        load_dotenv(env, override=True)
        print(
            "Loaded local .env; these settings override inherited shell variables. Secrets are not printed.", flush=True
        )
    reload_dirs = [str(root / "backend"), str(root / "sdk")] if args.reload else None
    uvicorn.run("arena_server.main:app", host=args.host, port=args.port, reload=args.reload, reload_dirs=reload_dirs)
