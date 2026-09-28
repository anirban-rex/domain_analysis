from __future__ import annotations

from collections import Counter
from .schemas import Facts
from .normalization import normalize_records


def extract(facts: Facts) -> dict[str, dict]:
    counts = Counter()
    for relation in facts.foreign_keys:
        source = relation.get("source") or relation.get("from")
        target = relation.get("target") or relation.get("to")
        if source in facts.nodes:
            counts[source] += 1
        if target in facts.nodes:
            counts[target] += 1
    return normalize_records([{"node_id": node_id, "value": counts[node_id], "metadata": {"signal": "foreign_key", "relationship_count": counts[node_id]}} for node_id in facts.nodes])
