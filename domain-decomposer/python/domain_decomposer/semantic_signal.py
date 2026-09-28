from __future__ import annotations

from .schemas import Facts
from .normalization import normalize_embedding


def extract(facts: Facts) -> dict[str, list[float]]:
    return {node_id: normalize_embedding(facts.embeddings.get(node_id, [])) for node_id in facts.nodes}
