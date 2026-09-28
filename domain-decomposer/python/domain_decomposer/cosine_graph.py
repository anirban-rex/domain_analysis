from __future__ import annotations

from itertools import combinations
import networkx as nx
import numpy as np
from .feature_matrix import FeatureMatrix
from .schemas import Facts


def cosine(left: np.ndarray, right: np.ndarray, left_mask: list[bool] | None = None, right_mask: list[bool] | None = None) -> float:
    if left_mask is not None and right_mask is not None:
        mask = np.asarray(left_mask, dtype=bool) & np.asarray(right_mask, dtype=bool)
        left, right = left[mask], right[mask]
    denominator = float(np.linalg.norm(left) * np.linalg.norm(right))
    if denominator == 0.0:
        return 0.0
    return float(np.dot(left, right) / denominator)


def build_graph(facts: Facts, matrix: FeatureMatrix, nearest_neighbors: int = 8, min_cosine: float = 0.05) -> nx.Graph:
    graph = nx.Graph()
    graph.add_nodes_from((node_id, {"fqcn": facts.nodes[node_id].fqcn, "package": facts.nodes[node_id].package, "source_path": facts.nodes[node_id].source_path}) for node_id in matrix.node_ids)
    candidates = {tuple(sorted((item.get("source"), item.get("target")))) for item in facts.references if item.get("source") in facts.nodes and item.get("target") in facts.nodes}
    for node_id in matrix.node_ids:
        distances = []
        for other in matrix.node_ids:
            if other == node_id:
                continue
            score = cosine(matrix.vectors[node_id], matrix.vectors[other], matrix.masks[node_id], matrix.masks[other])
            distances.append((score, other))
        candidates.update(tuple(sorted((node_id, other))) for score, other in sorted(distances, reverse=True)[:nearest_neighbors])
    for left, right in candidates:
        score = cosine(matrix.vectors[left], matrix.vectors[right], matrix.masks[left], matrix.masks[right])
        if score >= min_cosine:
            graph.add_edge(left, right, weight=score, cosine=score)
    return graph
