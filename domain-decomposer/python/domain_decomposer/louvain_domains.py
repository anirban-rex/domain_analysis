from __future__ import annotations

import networkx as nx
from networkx.algorithms.community import louvain_communities, modularity


def detect(graph: nx.Graph, resolution: float = 1.0, seed: int = 42) -> tuple[dict[str, int], float]:
    communities = louvain_communities(graph, weight="weight", resolution=resolution, seed=seed)
    labels = {node: index for index, community in enumerate(communities, start=1) for node in community}
    score = modularity(graph, communities, weight="weight") if graph.number_of_edges() else 0.0
    return labels, float(score)
