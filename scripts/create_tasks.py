"""Rebuild the versioned, fully synthetic benchmark fixtures. No external datasets."""

import json
from pathlib import Path

TASKS = []


def add(id, title, category, difficulty, description, operation, inputs, expected, tags):
    TASKS.append(
        dict(
            id=id,
            title=title,
            category=category,
            difficulty=difficulty,
            description=description,
            operation=operation,
            inputs=inputs,
            expected=expected,
            output_schema={k: type(v).__name__ for k, v in expected.items()},
            tags=tags,
            version="1.0.0",
            suite="workbench-v1",
            tools=["fixtures.read", "calculator.evaluate"],
            rubric="Equal weight for each required output field. Numeric tolerance: 0.01; lists must follow the specified order. All fields must pass for task success.",
        )
    )


add(
    "invoice-reconciliation",
    "Reconcile a messy invoice ledger",
    "Data analysis",
    "Medium",
    "Read invoices and payments. Ignore void invoices. Exclude duplicate payments with the same payment_id. Return billed_total, paid_total (payments against non-void invoices only), outstanding_total and unpaid_invoice_ids (positive balance, sorted).",
    "invoices",
    {
        "invoices": [
            {"id": "INV-101", "amount": 1200, "status": "open"},
            {"id": "INV-102", "amount": 800, "status": "open"},
            {"id": "INV-103", "amount": 500, "status": "void"},
            {"id": "INV-104", "amount": 600, "status": "open"},
        ],
        "payments": [
            {"payment_id": "P1", "invoice_id": "INV-101", "amount": 1200},
            {"payment_id": "P2", "invoice_id": "INV-102", "amount": 300},
            {"payment_id": "P2", "invoice_id": "INV-102", "amount": 300},
            {"payment_id": "P3", "invoice_id": "INV-103", "amount": 500},
        ],
    },
    {"billed_total": 2600, "paid_total": 1500, "outstanding_total": 1100, "unpaid_invoice_ids": ["INV-102", "INV-104"]},
    ["Deduplication", "Reconciliation"],
)
add(
    "revenue-by-region",
    "Find the highest-revenue region",
    "Data analysis",
    "Easy",
    "Read orders. Exclude cancelled orders. Net revenue is amount minus refund. Return total_net_revenue, top_region, and top_region_revenue. Break ties alphabetically.",
    "revenue",
    {
        "orders": [
            {"region": "APAC", "amount": 1200, "refund": 100, "status": "paid"},
            {"region": "EMEA", "amount": 900, "refund": 0, "status": "paid"},
            {"region": "APAC", "amount": 500, "refund": 0, "status": "cancelled"},
            {"region": "AMER", "amount": 1600, "refund": 200, "status": "paid"},
            {"region": "APAC", "amount": 600, "refund": 0, "status": "paid"},
        ]
    },
    {"total_net_revenue": 4000, "top_region": "APAC", "top_region_revenue": 1700},
    ["Aggregation", "Data cleaning"],
)
add(
    "latency-audit",
    "Investigate a latency regression",
    "Data analysis",
    "Medium",
    "Read requests. Exclude failed requests. Return successful_requests, mean_latency_ms rounded to 2 decimals, p95_latency_ms using nearest-rank percentile (ceil(0.95*n)), and slow_request_ids (latency strictly above 500 ms, sorted).",
    "latency",
    {
        "requests": [
            {"id": f"R{i + 1}", "latency_ms": n, "status": "failed" if i == 8 else "ok"}
            for i, n in enumerate([100, 120, 150, 200, 250, 300, 550, 900, 9000, 400])
        ]
    },
    {"successful_requests": 9, "mean_latency_ms": 330, "p95_latency_ms": 900, "slow_request_ids": ["R7", "R8"]},
    ["Statistics", "Observability"],
)
add(
    "subscription-metrics",
    "Calculate monthly recurring revenue",
    "Data analysis",
    "Hard",
    "Read subscriptions. Only active subscriptions count. Annual prices must be divided by 12. Return active_customers, mrr, arr, and enterprise_mrr. Each row is one customer; round currency to 2 decimals.",
    "subscriptions",
    {
        "subscriptions": [
            {"id": "A", "status": "active", "plan": "enterprise", "period": "annual", "price": 12000},
            {"id": "B", "status": "active", "plan": "starter", "period": "monthly", "price": 49},
            {"id": "C", "status": "cancelled", "plan": "enterprise", "period": "monthly", "price": 900},
            {"id": "D", "status": "active", "plan": "enterprise", "period": "monthly", "price": 500},
            {"id": "E", "status": "trial", "plan": "starter", "period": "monthly", "price": 49},
        ]
    },
    {"active_customers": 3, "mrr": 1549, "arr": 18588, "enterprise_mrr": 1500},
    ["Finance", "Normalization"],
)
add(
    "vendor-comparison",
    "Choose a compliant cloud vendor",
    "Research",
    "Medium",
    "Read vendor briefs and policy. Eligible vendors must have eu_hosting=true, soc2=true, and price <= budget. Choose lowest price, breaking ties by name. Return selected_vendor, monthly_cost, eligible_vendors (alphabetical), and citation_ids (selected vendor's source_id only). These are synthetic vendor briefs, not live market claims.",
    "vendors",
    {
        "policy": {"budget": 200},
        "vendors": [
            {"name": "Aster", "price": 150, "eu_hosting": True, "soc2": True, "source_id": "brief-01"},
            {"name": "Birch", "price": 90, "eu_hosting": False, "soc2": True, "source_id": "brief-02"},
            {"name": "Cedar", "price": 180, "eu_hosting": True, "soc2": True, "source_id": "brief-03"},
            {"name": "Dune", "price": 120, "eu_hosting": True, "soc2": False, "source_id": "brief-04"},
        ],
    },
    {
        "selected_vendor": "Aster",
        "monthly_cost": 150,
        "eligible_vendors": ["Aster", "Cedar"],
        "citation_ids": ["brief-01"],
    },
    ["Source grounding", "Constraints"],
)
add(
    "conflicting-sources",
    "Resolve a conflicting product claim",
    "Research",
    "Hard",
    "Read sources. Use only official sources, selecting the latest by ISO date for each topic. Return storage_gb, retention_days, and citation_ids of the selected sources sorted alphabetically. Community sources are not authoritative.",
    "sources",
    {
        "sources": [
            {"id": "src-01", "topic": "storage_gb", "value": 50, "official": True, "date": "2025-01-01"},
            {"id": "src-02", "topic": "storage_gb", "value": 100, "official": True, "date": "2025-06-01"},
            {"id": "src-03", "topic": "retention_days", "value": 30, "official": True, "date": "2025-02-01"},
            {"id": "src-04", "topic": "retention_days", "value": 90, "official": False, "date": "2025-07-01"},
        ]
    },
    {"storage_gb": 100, "retention_days": 30, "citation_ids": ["src-02", "src-03"]},
    ["Recency", "Citations"],
)
add(
    "evidence-review",
    "Separate evidence from speculation",
    "Research",
    "Medium",
    "Read studies. Include only randomized studies with sample_size >= 100. Return qualifying_ids sorted, total_participants, and weighted_effect (sum(effect*sample_size)/total_participants, rounded to 2 decimals). All studies are synthetic fixtures.",
    "studies",
    {
        "studies": [
            {"id": "S1", "design": "randomized", "sample_size": 200, "effect": 0.2},
            {"id": "S2", "design": "observational", "sample_size": 1000, "effect": 0.9},
            {"id": "S3", "design": "randomized", "sample_size": 50, "effect": 0.8},
            {"id": "S4", "design": "randomized", "sample_size": 300, "effect": 0.1},
        ]
    },
    {"qualifying_ids": ["S1", "S4"], "total_participants": 500, "weighted_effect": 0.14},
    ["Evidence quality", "Synthesis"],
)
add(
    "policy-audit",
    "Audit an access-control policy",
    "Research",
    "Easy",
    "Read policy and access_requests. Approve only if the user's role is allowed for that resource AND mfa=true. Return approved_ids and denied_ids, both sorted, and citation_ids containing the policy source_id.",
    "access",
    {
        "policy": {
            "source_id": "policy-v3",
            "roles": {"billing": ["admin", "finance"], "deploy": ["admin", "engineer"]},
        },
        "access_requests": [
            {"id": "A1", "resource": "billing", "role": "finance", "mfa": True},
            {"id": "A2", "resource": "deploy", "role": "engineer", "mfa": False},
            {"id": "A3", "resource": "billing", "role": "engineer", "mfa": True},
            {"id": "A4", "resource": "deploy", "role": "admin", "mfa": True},
        ],
    },
    {"approved_ids": ["A1", "A4"], "denied_ids": ["A2", "A3"], "citation_ids": ["policy-v3"]},
    ["Policy retrieval", "Verification"],
)
add(
    "ticket-triage",
    "Prioritize the support queue",
    "Operations",
    "Medium",
    "Read tickets. Exclude resolved tickets. Sort remaining tickets by severity (critical, high, medium, low), then created_at ascending, then id. Return ordered_ids, critical_count, and next_ticket_id.",
    "tickets",
    {
        "tickets": [
            {"id": "T1", "severity": "high", "created_at": "2025-06-01T09:00", "status": "open"},
            {"id": "T2", "severity": "critical", "created_at": "2025-06-01T10:00", "status": "open"},
            {"id": "T3", "severity": "critical", "created_at": "2025-06-01T08:00", "status": "resolved"},
            {"id": "T4", "severity": "low", "created_at": "2025-05-30T09:00", "status": "open"},
            {"id": "T5", "severity": "high", "created_at": "2025-06-01T08:00", "status": "open"},
        ]
    },
    {"ordered_ids": ["T2", "T5", "T1", "T4"], "critical_count": 1, "next_ticket_id": "T2"},
    ["Prioritization", "Tool use"],
)
add(
    "shipping-planner",
    "Find the cheapest eligible shipment",
    "Operations",
    "Easy",
    "Read shipment and carriers. A carrier qualifies when max_weight_kg >= weight_kg and days <= deadline_days. Cost is base_cost + per_kg * weight_kg. Return carrier, total_cost, and delivery_days. Break cost ties alphabetically by carrier name.",
    "shipping",
    {
        "shipment": {"weight_kg": 8, "deadline_days": 3},
        "carriers": [
            {"name": "Arrow", "base_cost": 10, "per_kg": 2, "days": 2, "max_weight_kg": 10},
            {"name": "Budget", "base_cost": 2, "per_kg": 1, "days": 7, "max_weight_kg": 50},
            {"name": "Cargo", "base_cost": 8, "per_kg": 1.5, "days": 3, "max_weight_kg": 30},
            {"name": "Dash", "base_cost": 5, "per_kg": 1, "days": 1, "max_weight_kg": 5},
        ],
    },
    {"carrier": "Cargo", "total_cost": 20, "delivery_days": 3},
    ["Optimization", "Constraints"],
)
add(
    "inventory-restock",
    "Plan an inventory replenishment",
    "Operations",
    "Hard",
    "Read inventory. Available = on_hand + incoming - reserved. When available < reorder_point, order target_stock - available units. Return order_quantities keyed by SKU (only SKUs needing orders), total_units, and estimated_cost using unit_cost.",
    "inventory",
    {
        "inventory": [
            {
                "sku": "K1",
                "on_hand": 10,
                "incoming": 5,
                "reserved": 8,
                "reorder_point": 10,
                "target_stock": 30,
                "unit_cost": 4,
            },
            {
                "sku": "K2",
                "on_hand": 30,
                "incoming": 0,
                "reserved": 5,
                "reorder_point": 10,
                "target_stock": 40,
                "unit_cost": 8,
            },
            {
                "sku": "K3",
                "on_hand": 3,
                "incoming": 0,
                "reserved": 2,
                "reorder_point": 5,
                "target_stock": 20,
                "unit_cost": 2,
            },
        ]
    },
    {"order_quantities": {"K1": 23, "K3": 19}, "total_units": 42, "estimated_cost": 130},
    ["Planning", "Inventory"],
)
add(
    "schedule-builder",
    "Build a dependency-aware schedule",
    "Operations",
    "Hard",
    "Read jobs. Unlimited parallel workers are available. Jobs start after all dependencies finish; jobs with no dependencies start at hour 0. Return completion_hours (job id to finish hour), makespan_hours, and critical_path. The critical path ends at the last finishing job; choose alphabetically for ties.",
    "schedule",
    {
        "jobs": [
            {"id": "A", "duration": 2, "depends_on": []},
            {"id": "B", "duration": 3, "depends_on": ["A"]},
            {"id": "C", "duration": 6, "depends_on": ["A"]},
            {"id": "D", "duration": 2, "depends_on": ["B", "C"]},
        ]
    },
    {"completion_hours": {"A": 2, "B": 5, "C": 8, "D": 10}, "makespan_hours": 10, "critical_path": ["A", "C", "D"]},
    ["Dependencies", "Scheduling"],
)

Path(__file__).resolve().parents[1].joinpath("backend/arena_server/task_library.json").write_text(
    json.dumps(TASKS, indent=2) + "\n"
)
print(f"Created {len(TASKS)} tasks")
