"""Launcher child process: load local .env, then start a single app server."""

import argparse
from pathlib import Path

from dotenv import load_dotenv
import uvicorn

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    env = Path(__file__).resolve().parents[1] / ".env"
    if env.is_file():
        load_dotenv(env, override=True)
        print(
            "Loaded local .env; these settings override inherited shell variables. Secrets are not printed.", flush=True
        )
    uvicorn.run("arena_server.main:app", host=args.host, port=args.port)
