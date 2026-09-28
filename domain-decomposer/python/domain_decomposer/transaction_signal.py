from __future__ import annotations

from collections import Counter
from .schemas import Facts
from .normalization import normalize_records


def extract(facts: Facts) -> dict[str, dict]:
    counts = Counter()
    for transaction in facts.transactions:
        participants = transaction.get("participants", [])
        for node_id in participants:
            if node_id in facts.nodes:
                counts[node_id] += 1
    return normalize_records([{"node_id": node_id, "value": counts[node_id], "metadata": {"signal": "transaction", "boundary_count": counts[node_id]}} for node_id in facts.nodes])
