#!/usr/bin/env python3
"""Interactive local setup. Standard library only; no model inference or paid request."""

import getpass
import json
import math
import os
import re
import sys
import ssl
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def get_json(url, key=None):
    headers = {"Accept": "application/json", "User-Agent": "AgentArena-Setup/0.2"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    # Prefer the installed certificate bundle in the project virtual environment. Never disable verification.
    try:
        import certifi

        context = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        context = ssl.create_default_context()
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=25, context=context) as response:
        return json.load(response)


def write_env(path, values):
    old = (
        path.read_text(encoding="utf-8") if path.exists() else "# AgentArena local settings. Never commit this file.\n"
    )
    lines = [line for line in old.splitlines() if line.split("=", 1)[0].strip() not in values]
    text = "\n".join(lines).rstrip() + "\n\n" + "\n".join(f"{k}={json.dumps(str(v))}" for k, v in values.items()) + "\n"
    fd, temporary = tempfile.mkstemp(prefix=".arena-env-", dir=path.parent)
    try:
        os.fchmod(fd, 0o600) if os.name != "nt" else None
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(text)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main():
    if not sys.stdin.isatty():
        raise SystemExit(
            "Run this setup in your own interactive terminal. Never send your key to a chat or pipe it into a command."
        )
    print(
        "\nAgentArena · OpenRouter setup\nYour computer runs the app; OpenRouter runs the model.\nThis setup only checks key/model metadata. It does not generate model output.\n"
    )
    key = getpass.getpass("Paste your OpenRouter API key (typing is hidden): ").strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]{12,}", key):
        raise SystemExit("That does not look like an API key. Nothing was saved.")
    try:
        info = get_json("https://openrouter.ai/api/v1/key", key).get("data", {})
    except urllib.error.HTTPError as exc:
        raise SystemExit(
            f"OpenRouter rejected the metadata check (HTTP {exc.code}). Check the key and account access. Nothing was saved."
        ) from None
    except Exception:
        raise SystemExit(
            "Could not reach OpenRouter securely. Check your network; TLS verification has not been disabled. Nothing was saved."
        ) from None
    print("Key accepted. No inference requested.")
    if isinstance(info.get("free_model_daily_requests"), dict):
        daily = info["free_model_daily_requests"]
        print(f"Free-route requests remaining today (reported by provider): {daily.get('remaining', 'unknown')}")
    print("Set a low per-key spending cap in your OpenRouter dashboard. App request caps are NOT dollar caps.\n")
    models = []
    try:
        for row in get_json("https://openrouter.ai/api/v1/models").get("data", []):
            if "tools" not in row.get("supported_parameters", []) or row["id"] in (
                "openrouter/free",
                "openrouter/auto",
            ):
                continue
            inp, out = float(row["pricing"]["prompt"]), float(row["pricing"]["completion"])
            if all(math.isfinite(p) and p >= 0 for p in (inp, out)):
                models.append({"id": row["id"], "input": inp * 1e6, "output": out * 1e6, "free": inp == out == 0})
        models.sort(key=lambda m: (not m["free"], m["input"] + m["output"], m["id"]))
    except Exception:
        print("Model catalogue unavailable. You may enter a current model ID manually from openrouter.ai/models.\n")
    choices = models[:10]
    if choices:
        print("Current catalogue entries advertising tool support (availability is NOT guaranteed):")
        for i, m in enumerate(choices, 1):
            price = (
                "free token pricing; quota-limited"
                if m["free"]
                else f"USD {m['input']:g} input / {m['output']:g} output per million tokens"
            )
            print(f"  {i:2}. {m['id']} — {price}")
    answer = input("\nChoose a number, or paste a specific model ID (not an automatic router): ").strip()
    selected = None
    if answer.isdigit() and 1 <= int(answer) <= len(choices):
        selected = choices[int(answer) - 1]
        model = selected["id"]
    else:
        model = answer
        selected = next((m for m in models if m["id"] == model), None)
    if not re.fullmatch(r"[A-Za-z0-9._:/+\-]{1,160}", model) or model in ("openrouter/free", "openrouter/auto"):
        raise SystemExit("Choose a specific model ID for reproducible comparisons. Nothing was saved.")
    if selected and not selected["free"]:
        if input("This model has paid token pricing. Type YES to configure it (no generation yet): ").strip() != "YES":
            raise SystemExit("Cancelled. Nothing saved.")
    if not selected:
        print("Manual model ID: price and tool capability are unverified. Check its model page before running.")
    path = ROOT / ".env"
    print(
        f"\nThe key will be saved as plaintext in {path}. It is git-ignored and owner-readable on macOS/Linux. Do not share this file."
    )
    if input("Save local configuration? [y/N]: ").strip().lower() != "y":
        raise SystemExit("Cancelled. Nothing saved.")
    values = {
        "OPENAI_API_KEY": key,
        "OPENAI_BASE_URL": "https://openrouter.ai/api/v1",
        "OPENAI_MODEL": model,
        "ARENA_WORKERS": "1",
        "ARENA_CALL_INTERVAL_SECONDS": "3.2",
        "ARENA_READ_ONLY": "0",
        "ARENA_INPUT_PRICE": selected["input"] if selected else "",
        "ARENA_OUTPUT_PRICE": selected["output"] if selected else "",
    }
    write_env(path, values)
    print(
        "\nSaved. Your key was not printed and no model generation was requested.\nNext:\n  python3 scripts/start.py --port 8002\nOpen http://localhost:8002 → Experiments → select ONE task → run the three-agent comparison.\nFree models can be unavailable or rate-limited. Do not promise results before checking them."
    )


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        raise SystemExit("\nCancelled. No new configuration was saved.") from None
