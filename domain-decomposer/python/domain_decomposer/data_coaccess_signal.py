from __future__ import annotations

from collections import Counter
from itertools import combinations
from .schemas import Facts
from .normalization import normalize_records


def extract(facts: Facts) -> dict[str, dict]:
    counts = Counter()
    for transaction in facts.transactions:
        participants = sorted(set(item for item in transaction.get("participants", []) if item in facts.nodes))
        for left, right in combinations(participants, 2):
            counts[left] += 1
            counts[right] += 1
    return normalize_records([{"node_id": node_id, "value": counts[node_id], "metadata": {"signal": "data_coaccess", "pair_count": counts[node_id]}} for node_id in facts.nodes])
