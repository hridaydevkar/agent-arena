import pytest

from arena_server.data_tools import analyze_records


@pytest.fixture
def invoice_fixtures():
    return {
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
    }


def test_structured_analysis_reconciles_billed_total(invoice_fixtures):
    result = analyze_records(
        {
            "table": "invoices",
            "filters": [
                {"column": "invoices.status", "op": "eq", "value": "open"}
            ],
            "aggregates": [
                {"op": "sum", "column": "invoices.amount", "as": "billed_total"}
            ],
        },
        invoice_fixtures,
    )
    assert result["rows"] == [{"billed_total": 2600}]


def test_structured_analysis_joins_and_deduplicates_payments(invoice_fixtures):
    result = analyze_records(
        {
            "table": "payments",
            "deduplicate": [{"table": "payments", "by": ["payment_id"]}],
            "join": {
                "table": "invoices",
                "left_on": "payments.invoice_id",
                "right_on": "invoices.id",
                "how": "inner",
            },
            "filters": [
                {"column": "invoices.status", "op": "eq", "value": "open"}
            ],
            "aggregates": [
                {"op": "sum", "column": "payments.amount", "as": "paid_total"}
            ],
        },
        invoice_fixtures,
    )
    assert result["rows"] == [{"paid_total": 1500}]


def test_structured_analysis_finds_unpaid_invoices(invoice_fixtures):
    result = analyze_records(
        {
            "table": "invoices",
            "deduplicate": [{"table": "payments", "by": ["payment_id"]}],
            "filters": [
                {"column": "invoices.status", "op": "eq", "value": "open"}
            ],
            "join": {
                "table": "payments",
                "left_on": "invoices.id",
                "right_on": "payments.invoice_id",
                "how": "left",
            },
            "group_by": [
                {"column": "invoices.id", "as": "invoice_id"},
                {"column": "invoices.amount", "as": "invoice_amount"},
            ],
            "aggregates": [
                {"op": "sum", "column": "payments.amount", "as": "paid_amount"}
            ],
            "computed_fields": [
                {
                    "as": "balance",
                    "op": "subtract",
                    "left": "invoice_amount",
                    "right": "paid_amount",
                }
            ],
            "post_filters": [
                {"column": "balance", "op": "gt", "value": 0}
            ],
            "sort_by": [{"column": "invoice_id", "direction": "asc"}],
        },
        invoice_fixtures,
    )
    assert result["rows"] == [
        {"invoice_id": "INV-102", "invoice_amount": 800, "paid_amount": 300, "balance": 500},
        {"invoice_id": "INV-104", "invoice_amount": 600, "paid_amount": 0, "balance": 600},
    ]


def test_structured_analysis_rejects_unknown_table(invoice_fixtures):
    with pytest.raises(ValueError, match="supplied fixtures"):
        analyze_records({"table": "not_a_fixture"}, invoice_fixtures)


def test_structured_analysis_rejects_ambiguous_column(invoice_fixtures):
    with pytest.raises(ValueError, match="table-qualified"):
        analyze_records(
            {
                "table": "payments",
                "join": {
                    "table": "invoices",
                    "left_on": "payments.invoice_id",
                    "right_on": "invoices.id",
                    "how": "inner",
                },
                "filters": [{"column": "amount", "op": "gt", "value": 0}],
            },
            invoice_fixtures,
        )
