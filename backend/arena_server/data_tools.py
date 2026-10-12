"""Validated, read-only relational operations over task fixture data.

This module deliberately accepts a small declarative query specification instead
of arbitrary SQL so local models can filter, join, deduplicate, group, and derive
values without inventing SQL syntax or column names.
"""
from __future__ import annotations

import math
from collections import defaultdict
from typing import Any

MAX_RESULT_ROWS = 100
MAX_INPUT_ROWS_PER_TABLE = 50_000


def _to_rows(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if isinstance(value, dict):
        return [dict(value)]
    if not isinstance(value, list):
        return [{"value": value}]
    rows = []
    for item in value:
        rows.append(dict(item) if isinstance(item, dict) else {"value": item})
    return rows


def _qualified(table: str, row: dict[str, Any]) -> dict[str, Any]:
    return {f"{table}.{key}": value for key, value in row.items()}


def _field(row: dict[str, Any], name: str) -> Any:
    if not isinstance(name, str) or not name:
        raise ValueError("Column names must be non-empty strings.")
    if name in row:
        return row[name]
    matches = [key for key in row if key.endswith("." + name)]
    if len(matches) == 1:
        return row[matches[0]]
    if len(matches) > 1:
        raise ValueError(f"Ambiguous column '{name}'; use a table-qualified name.")
    raise ValueError(f"Unknown column '{name}'. Use the supplied fixture schema.")


def _resolve_value(row: dict[str, Any], value: Any) -> Any:
    if isinstance(value, dict) and set(value) == {"column"}:
        return _field(row, value["column"])
    return value


def _matches(row: dict[str, Any], condition: dict[str, Any]) -> bool:
    if not isinstance(condition, dict):
        raise ValueError("Each filter must be an object.")
    column = condition.get("column")
    op = condition.get("op")
    if op not in {
        "eq", "ne", "gt", "gte", "lt", "lte", "in", "not_in",
        "contains", "starts_with", "is_null", "is_not_null",
    }:
        raise ValueError(f"Unsupported filter operator: {op!r}.")
    left = _field(row, column)
    if op == "is_null":
        return left is None
    if op == "is_not_null":
        return left is not None
    right = _resolve_value(row, condition.get("value"))
    if op == "eq":
        return left == right
    if op == "ne":
        return left != right
    if op == "in":
        if not isinstance(right, (list, tuple, set)):
            raise ValueError("The value for 'in' must be an array.")
        return left in right
    if op == "not_in":
        if not isinstance(right, (list, tuple, set)):
            raise ValueError("The value for 'not_in' must be an array.")
        return left not in right
    if left is None or right is None:
        return False
    if op == "gt":
        return left > right
    if op == "gte":
        return left >= right
    if op == "lt":
        return left < right
    if op == "lte":
        return left <= right
    if op == "contains":
        return isinstance(left, (str, list, tuple)) and right in left
    if op == "starts_with":
        return isinstance(left, str) and isinstance(right, str) and left.startswith(right)
    return False


def _dedupe_table(rows: list[dict[str, Any]], table: str, by: list[str]) -> list[dict[str, Any]]:
    if not by or not all(isinstance(column, str) and column for column in by):
        raise ValueError("Each deduplicate rule needs a non-empty 'by' column list.")
    seen = set()
    result = []
    for row in rows:
        qualified_row = _qualified(table, row)
        key_values = tuple(_field(qualified_row, col if "." in col else f"{table}.{col}") for col in by)
        # JSON encoding handles list/object keys without relying on hashability.
        import json
        key = json.dumps(key_values, sort_keys=True, ensure_ascii=False, default=str)
        if key not in seen:
            seen.add(key)
            result.append(row)
    return result


def _number(value: Any, label: str) -> float | int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} requires numeric values.")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"{label} requires finite numeric values.")
    return value


def _aggregate(rows: list[dict[str, Any]], aggregate: dict[str, Any]) -> Any:
    if not isinstance(aggregate, dict):
        raise ValueError("Each aggregate must be an object.")
    op = aggregate.get("op")
    column = aggregate.get("column", "*")
    alias = aggregate.get("as")
    if not isinstance(alias, str) or not alias:
        raise ValueError("Each aggregate requires a non-empty 'as' alias.")
    values = [None if column == "*" else _field(row, column) for row in rows]
    present = [value for value in values if value is not None]
    if op == "count":
        return len(rows) if column == "*" else len(present)
    if op == "count_distinct":
        return len({repr(value) for value in present})
    if op == "sum":
        return sum(_number(value, "sum") for value in present)
    if op == "avg":
        return (sum(_number(value, "avg") for value in present) / len(present)) if present else None
    if op == "min":
        return min(present) if present else None
    if op == "max":
        return max(present) if present else None
    raise ValueError(f"Unsupported aggregate operator: {op!r}.")


def _sort_value(value: Any):
    if value is None:
        return (1, "", "")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return (0, "number", value)
    return (0, type(value).__name__, str(value))


def analyze_records(spec: dict[str, Any], fixtures: dict[str, Any]) -> dict[str, Any]:
    """Apply a validated relational operation spec to task-provided fixtures.

    Supported spec keys: table, deduplicate, join, filters, group_by, aggregates,
    computed_fields, post_filters, sort_by, and limit. This function never reads
    external resources, never mutates fixture data, and never executes code/SQL.
    """
    if not isinstance(spec, dict):
        raise ValueError("Analysis specification must be an object.")
    if not isinstance(fixtures, dict):
        raise ValueError("Fixtures must be supplied as an object.")
    table = spec.get("table")
    if not isinstance(table, str) or table not in fixtures:
        raise ValueError("'table' must name one of the supplied fixtures.")

    tables: dict[str, list[dict[str, Any]]] = {}
    for name, value in fixtures.items():
        rows = _to_rows(value)
        if len(rows) > MAX_INPUT_ROWS_PER_TABLE:
            raise ValueError(f"Fixture '{name}' exceeds the row limit.")
        tables[name] = rows

    deduplicate = spec.get("deduplicate", [])
    if not isinstance(deduplicate, list):
        raise ValueError("'deduplicate' must be an array.")
    for rule in deduplicate:
        if not isinstance(rule, dict):
            raise ValueError("Each deduplicate rule must be an object.")
        target = rule.get("table")
        if target not in tables:
            raise ValueError("Deduplicate rules must name a supplied fixture table.")
        tables[target] = _dedupe_table(tables[target], target, rule.get("by", []))

    base = [_qualified(table, row) for row in tables[table]]
    join = spec.get("join")
    if join is not None:
        if not isinstance(join, dict):
            raise ValueError("'join' must be an object.")
        join_table = join.get("table")
        how = join.get("how", "inner")
        left_on = join.get("left_on")
        right_on = join.get("right_on")
        if join_table not in tables:
            raise ValueError("Join table must name a supplied fixture table.")
        if how not in ("inner", "left"):
            raise ValueError("Join 'how' must be 'inner' or 'left'.")
        if not isinstance(left_on, str) or not isinstance(right_on, str):
            raise ValueError("Join requires 'left_on' and 'right_on' column names.")
        right_rows = [_qualified(join_table, row) for row in tables[join_table]]
        known_right_columns = sorted({key for row in right_rows for key in row})
        joined = []
        for left_row in base:
            left_value = _field(left_row, left_on)
            matches = [row for row in right_rows if _field(row, right_on) == left_value]
            if matches:
                for right_row in matches:
                    overlap = set(left_row).intersection(right_row)
                    if overlap:
                        raise ValueError("Joining the same fixture table twice is not supported.")
                    joined.append({**left_row, **right_row})
            elif how == "left":
                joined.append({**left_row, **{column: None for column in known_right_columns}})
        base = joined

    filters = spec.get("filters", [])
    if not isinstance(filters, list):
        raise ValueError("'filters' must be an array.")
    for condition in filters:
        base = [row for row in base if _matches(row, condition)]

    group_by = spec.get("group_by", [])
    aggregates = spec.get("aggregates", [])
    if not isinstance(group_by, list) or not isinstance(aggregates, list):
        raise ValueError("'group_by' and 'aggregates' must be arrays.")

    def normalize_group(item: Any) -> tuple[str, str]:
        if isinstance(item, str):
            return item, item.rsplit(".", 1)[-1]
        if isinstance(item, dict) and isinstance(item.get("column"), str):
            alias = item.get("as") or item["column"].rsplit(".", 1)[-1]
            if not isinstance(alias, str) or not alias:
                raise ValueError("Group-by aliases must be non-empty strings.")
            return item["column"], alias
        raise ValueError("Each group_by entry must be a column string or {column, as} object.")

    normalized_groups = [normalize_group(item) for item in group_by]
    if aggregates or normalized_groups:
        grouped: dict[str, tuple[dict[str, Any], list[dict[str, Any]]]] = {}
        for row in base:
            group_values = {alias: _field(row, column) for column, alias in normalized_groups}
            import json
            key = json.dumps(group_values, sort_keys=True, ensure_ascii=False, default=str)
            if key not in grouped:
                grouped[key] = (group_values, [])
            grouped[key][1].append(row)
        if not normalized_groups and aggregates:
            grouped = {"__all__": ({}, base)}
        results = []
        for group_values, members in grouped.values():
            result = dict(group_values)
            for aggregate in aggregates:
                result[aggregate["as"]] = _aggregate(members, aggregate)
            results.append(result)
        base = results

    computed_fields = spec.get("computed_fields", [])
    if not isinstance(computed_fields, list):
        raise ValueError("'computed_fields' must be an array.")
    for field in computed_fields:
        if not isinstance(field, dict) or not isinstance(field.get("as"), str):
            raise ValueError("Each computed field requires an 'as' alias.")
        op = field.get("op")
        left_name = field.get("left")
        right_name = field.get("right")
        for row in base:
            left = _number(_field(row, left_name), "computed field")
            right = _number(_field(row, right_name), "computed field")
            if op == "subtract":
                value = left - right
            elif op == "add":
                value = left + right
            elif op == "multiply":
                value = left * right
            elif op == "divide":
                if right == 0:
                    raise ValueError("Computed field cannot divide by zero.")
                value = left / right
            else:
                raise ValueError(f"Unsupported computed-field operator: {op!r}.")
            if isinstance(value, float) and not math.isfinite(value):
                raise ValueError("Computed field produced a non-finite number.")
            row[field["as"]] = value

    post_filters = spec.get("post_filters", [])
    if not isinstance(post_filters, list):
        raise ValueError("'post_filters' must be an array.")
    for condition in post_filters:
        base = [row for row in base if _matches(row, condition)]

    sort_by = spec.get("sort_by", [])
    if not isinstance(sort_by, list):
        raise ValueError("'sort_by' must be an array.")
    for sort in reversed(sort_by):
        if not isinstance(sort, dict) or not isinstance(sort.get("column"), str):
            raise ValueError("Each sort_by entry requires a column.")
        direction = sort.get("direction", "asc")
        if direction not in ("asc", "desc"):
            raise ValueError("Sort direction must be 'asc' or 'desc'.")
        base.sort(key=lambda row, col=sort["column"]: _sort_value(_field(row, col)), reverse=direction == "desc")

    limit = spec.get("limit", MAX_RESULT_ROWS)
    if type(limit) is not int or not 1 <= limit <= MAX_RESULT_ROWS:
        raise ValueError(f"'limit' must be an integer between 1 and {MAX_RESULT_ROWS}.")
    truncated = len(base) > limit
    result_rows = base[:limit]
    columns = list(result_rows[0].keys()) if result_rows else []
    return {"columns": columns, "rows": result_rows, "truncated": truncated}
