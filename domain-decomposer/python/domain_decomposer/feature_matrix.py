from __future__ import annotations

from dataclasses import dataclass
import numpy as np
from .schemas import Facts


BASE_SIGNALS = ("foreign_key", "transaction", "data_coaccess")


@dataclass
class FeatureMatrix:
    node_ids: list[str]
    vectors: dict[str, np.ndarray]
    masks: dict[str, list[bool]]
    feature_names: list[str]


def build(facts: Facts, signal_maps: dict[str, dict], semantic: dict[str, list[float]], active_signals: tuple[str, ...] = BASE_SIGNALS) -> FeatureMatrix:
    node_ids = sorted(facts.nodes)
    semantic_size = max((len(value) for value in semantic.values()), default=0)
    feature_names = list(active_signals) + [f"semantic_{index}" for index in range(semantic_size)]
    vectors = {}
    masks = {}
    for node_id in node_ids:
        values, mask = [], []
        for signal in active_signals:
            record = signal_maps[signal].get(node_id, {"value": 0.0, "available": False})
            values.append(float(record.get("value", 0.0)))
            mask.append(bool(record.get("available", False)))
        embedding = semantic.get(node_id, [])
        values.extend(float(embedding[index]) if index < len(embedding) else 0.0 for index in range(semantic_size))
        mask.extend(index < len(embedding) for index in range(semantic_size))
        vectors[node_id] = np.asarray(values, dtype=float)
        masks[node_id] = mask
    return FeatureMatrix(node_ids=node_ids, vectors=vectors, masks=masks, feature_names=feature_names)
