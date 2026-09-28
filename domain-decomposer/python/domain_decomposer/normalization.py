from __future__ import annotations

import math
from typing import Any


def log_scale(value: float, maximum: float) -> float:
    if maximum <= 0:
        return 0.0
    return min(1.0, math.log1p(max(0.0, value)) / math.log1p(maximum))


def normalize_records(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    available = [float(item["value"]) for item in records if item.get("available", True)]
    maximum = max(available, default=0.0)
    result = {}
    for item in records:
        raw = float(item.get("value", 0.0))
        result[item["node_id"]] = {"raw": raw, "value": log_scale(raw, maximum), "available": bool(item.get("available", True)), "metadata": item.get("metadata", {})}
    return result


def normalize_embedding(values: list[float]) -> list[float]:
    if not values:
        return []
    norm = math.sqrt(sum(value * value for value in values))
    if norm == 0.0:
        return [0.0 for _ in values]
    return [value / norm for value in values]
