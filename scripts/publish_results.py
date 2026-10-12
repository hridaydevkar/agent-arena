"""Export one completed model job for publication. No inference, uploads or deployment."""

import argparse
import json
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://localhost:8002")
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument("--job")
    choice.add_argument("--latest", action="store_true")
    parser.add_argument(
        "--confirm-public", action="store_true", help="Confirm that names and result metrics can be made public"
    )
    args = parser.parse_args()
    if not args.confirm_public:
        parser.error("Review what is exported in public-data/README.md, then add --confirm-public")

    def get(path):
        with urllib.request.urlopen(args.url.rstrip("/") + path, timeout=30) as response:
            return json.load(response)

    job = args.job
    if args.latest:
        model_ids = {a["id"] for a in get("/api/agents") if a["strategy"] == "model"}
        job = next(
            (j["id"] for j in get("/api/jobs") if j["status"] == "completed" and set(j["agent_ids"]) <= model_ids), None
        )
        if not job:
            raise SystemExit("No completed model job found. Run an experiment first.")
    report = get(f"/api/jobs/{job}/report")
    path = ROOT / "public-data/results.json"
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        f"Saved summary-only report: {path}\nReview this file before committing. Nothing was deployed or uploaded.\nNext: follow docs/PUBLISH.md. Never commit .env or .arena."
    )


if __name__ == "__main__":
    try:
        main()
    except urllib.error.HTTPError as exc:
        raise SystemExit(
            f"Export refused (HTTP {exc.code}). Check that the job completed and contains actual model executions; inspect errors in Run history."
        ) from None
    except urllib.error.URLError:
        raise SystemExit(
            "Could not reach the app. Keep it running and check --url (your port is likely 8002)."
        ) from None
