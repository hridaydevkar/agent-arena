"""Server-side provider configuration. No credentials leave this module in responses."""

import math
import os
import threading
import time
from urllib.parse import urlparse

import httpx

_REQUEST_LOCK = threading.Lock()
_LAST_REQUEST = 0.0


def read_only():
    return os.getenv("ARENA_READ_ONLY", "0").lower() in ("1", "true", "yes")


def base_url():
    return os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")


def provider_name():
    host = urlparse(base_url()).hostname or ""
    if host == "openrouter.ai":
        return "OpenRouter"
    if host == "generativelanguage.googleapis.com":
        return "Gemini (OpenAI compatibility)"
    if host in ("localhost", "127.0.0.1", "host.docker.internal"):
        return "Local OpenAI-compatible server"
    return "OpenAI-compatible provider"


def configured():
    return bool(os.getenv("OPENAI_API_KEY")) and not read_only()


def pace_requests():
    """Process-wide pacing. Counts against wall time; not a guarantee of account quota."""
    global _LAST_REQUEST
    seconds = float(os.getenv("ARENA_CALL_INTERVAL_SECONDS", "0"))
    seconds = max(0.0, min(seconds, 60.0)) if math.isfinite(seconds) else 0.0
    if not seconds:
        return
    with _REQUEST_LOCK:
        delay = seconds - (time.monotonic() - _LAST_REQUEST)
        if delay > 0:
            time.sleep(delay)
        _LAST_REQUEST = time.monotonic()


def error_message(status):
    messages = {
        400: "Provider rejected this request. Check the model ID and its tool-calling support.",
        401: "Provider key was rejected. Rerun scripts/setup_openrouter.py and restart the app.",
        402: "Provider credit/spending limit reached. Check your account limits; no automatic retry was made.",
        403: "Provider denied access. Check account permissions, model availability and privacy settings.",
        404: "Model or endpoint not found. Choose a current model ID from the provider catalogue.",
        408: "Provider request timed out. Try a smaller model or rerun later.",
        429: "Provider rate limit or daily quota reached. Wait and check your account limits before retrying.",
        502: "Provider is temporarily unavailable. Try again later or select another model.",
        503: "No model capacity is currently available. Free routes may be temporarily unavailable.",
    }
    return f"HTTP {status}: " + messages.get(
        status, "Provider request failed. Inspect account status or try again later."
    )


def openrouter_catalog():
    """Public metadata request only. Never starts inference or sends a key."""
    response = httpx.get("https://openrouter.ai/api/v1/models", timeout=15)
    if response.status_code != 200:
        raise RuntimeError(error_message(response.status_code))
    rows = []
    for model in response.json().get("data", []):
        modalities = model.get("architecture", {}).get("output_modalities", ["text"])
        if "text" not in modalities:
            continue
        prices = model.get("pricing") or {}
        try:
            inp, out = float(prices["prompt"]), float(prices["completion"])
            if not all(math.isfinite(p) and p >= 0 for p in (inp, out)):
                continue
        except (KeyError, TypeError, ValueError):
            continue
        rows.append(
            {
                "id": model["id"],
                "name": model.get("name", model["id"]),
                "supports_tools": "tools" in model.get("supported_parameters", []),
                "input_per_million": inp * 1_000_000,
                "output_per_million": out * 1_000_000,
                "free": inp == 0 and out == 0,
            }
        )
    return sorted(rows, key=lambda r: (not r["free"], not r["supports_tools"], r["input_per_million"], r["id"]))


def check_provider():
    if not configured():
        raise ValueError("No provider is configured, or this is a read-only site.")
    if provider_name() != "OpenRouter":
        return {
            "status": "configured",
            "message": "Configuration found. No inference or authenticated connection test was performed for this provider.",
        }
    response = httpx.get(
        "https://openrouter.ai/api/v1/key",
        headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
        timeout=15,
    )
    if response.status_code != 200:
        raise RuntimeError(error_message(response.status_code))
    data = response.json().get("data", {})
    return {
        "status": "authenticated",
        "message": "OpenRouter accepted your key. No model generation was requested. This does not guarantee model capacity or successful tool calls.",
        "key_limit_remaining": data.get("limit_remaining"),
        "free_model_daily_requests": data.get("free_model_daily_requests"),
    }
