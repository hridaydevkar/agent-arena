"""Run a benchmark through the API. Requires the local server to be running."""

import os
import time

import httpx

base = os.getenv("ARENA_URL", "http://localhost:8000")
headers = {"Authorization": f"Bearer {os.environ['ARENA_API_TOKEN']}"} if os.getenv("ARENA_API_TOKEN") else {}
with httpx.Client(base_url=base, headers=headers, timeout=30) as client:
    response = client.post(
        "/api/benchmarks",
        json={
            "agent_ids": ["atlas", "relay"],
            "task_ids": ["invoice-reconciliation", "shipping-planner"],
        },
    )
    response.raise_for_status()
    job_id = response.json()["id"]
    while True:
        response = client.get(f"/api/jobs/{job_id}")
        response.raise_for_status()
        job = response.json()
        print(f"{job['status']}: {job['completed']}/{job['total']}")
        if job["status"] not in ("queued", "running"):
            for run_id in job["run_ids"]:
                print(f"Replay: {base}/runs/{run_id}")
            break
        time.sleep(1)
