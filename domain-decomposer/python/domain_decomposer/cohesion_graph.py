from __future__ import annotations

from collections import defaultdict
from itertools import combinations
import math
from typing import Any

import networkx as nx
import numpy as np

from .schemas import Facts

DEFAULT_SIGNAL_WEIGHTS = {
    "reference": 0.23,
    "workflow": 0.23,
    "foreign_key": 0.18,
    "semantic": 0.23,
    "package": 0.05,
    "git_cocommit": 0.08,
}
REFERENCE_STRENGTH = {
    "method_call": 1.0,
    "type_reference": 0.8,
    "import": 0.65,
}


def _pair(left: str, right: str) -> tuple[str, str]:
    return tuple(sorted((left, right)))


def _resolve_node(value: Any, facts: Facts, simple_names: dict[str, list[str]]) -> str | None:
    if not isinstance(value, str):
        return None
    if value in facts.nodes:
        return value
    matches = simple_names.get(value.rsplit(".", 1)[-1], [])
    return matches[0] if len(matches) == 1 else None


def _cosine(left: list[float], right: list[float]) -> float:
    if not left or not right:
        return 0.0
    size = min(len(left), len(right))
    left_array = np.asarray(left[:size], dtype=float)
    right_array = np.asarray(right[:size], dtype=float)
    denominator = float(np.linalg.norm(left_array) * np.linalg.norm(right_array))
    if denominator == 0.0:
        return 0.0
    return max(0.0, min(1.0, float(np.dot(left_array, right_array) / denominator)))


def _package_score(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    if left == right:
        return 1.0
    if left.startswith(right + ".") or right.startswith(left + "."):
        return 0.6
    left_parts, right_parts = left.split("."), right.split(".")
    common = 0
    for left_part, right_part in zip(left_parts, right_parts):
        if left_part != right_part:
            break
        common += 1
    return common / max(len(left_parts), len(right_parts)) if common >= 2 else 0.0


def _resource_pairs(facts: Facts, simple_names: dict[str, list[str]]) -> dict[tuple[str, str], set[str]]:
    """Infer co-access pairs from explicit resource/table access records when present."""
    resource_users: dict[str, set[str]] = defaultdict(set)
    for record in facts.method_accesses:
        resource = next((record.get(key) for key in ("table", "entity", "resource", "target") if record.get(key)), None)
        node_id = _resolve_node(record.get("node_id") or record.get("source") or record.get("owner"), facts, simple_names)
        if resource and node_id:
            resource_users[str(resource)].add(node_id)
        participants = record.get("participants") or record.get("classes")
        if resource and isinstance(participants, list):
            resource_users[str(resource)].update(
                node for value in participants
                if (node := _resolve_node(value, facts, simple_names)) is not None
            )
    result: dict[tuple[str, str], set[str]] = defaultdict(set)
    for resource, users in resource_users.items():
        for left, right in combinations(sorted(users), 2):
            result[_pair(left, right)].add(resource)
    return result


def build_graph(
    facts: Facts,
    embeddings: dict[str, list[float]] | None = None,
    nearest_neighbors: int = 8,
    minimum_edge_weight: float = 0.10,
    minimum_semantic_similarity: float = 0.45,
    signal_weights: dict[str, float] | None = None,
    pairwise_signals: dict[str, dict[tuple[str, str], float]] | None = None,
) -> nx.Graph:
    """Build an undirected cohesion graph from pairwise evidence.

    Directed code dependencies are retained as edge metadata and should also be
    analyzed separately when reviewing cross-domain coupling.
    """
    embeddings = embeddings or facts.embeddings
    weights = dict(DEFAULT_SIGNAL_WEIGHTS)
    if signal_weights:
        unknown = set(signal_weights) - set(weights)
        if unknown:
            raise ValueError(f"Unknown cohesion signal weights: {', '.join(sorted(unknown))}")
        weights.update({name: float(value) for name, value in signal_weights.items()})
    if any(not math.isfinite(value) or value < 0.0 for value in weights.values()) or sum(weights.values()) <= 0.0:
        raise ValueError("Signal weights must be finite, non-negative, and have a positive total")
    if not math.isfinite(minimum_edge_weight) or minimum_edge_weight < 0.0:
        raise ValueError("Minimum edge weight must be finite and non-negative")
    if not 0.0 <= minimum_semantic_similarity <= 1.0:
        raise ValueError("Minimum semantic similarity must be between 0 and 1")
    pairwise_signals = pairwise_signals or {}
    availability = facts.signal_availability
    enabled = {
        "reference": availability.get("reference", bool(facts.references)),
        "workflow": availability.get("workflow", bool(facts.transactions or facts.method_accesses)),
        "foreign_key": availability.get("foreign_key", bool(facts.foreign_keys)),
        "semantic": bool(embeddings),
        "package": any(bool(node.package) for node in facts.nodes.values()),
        "git_cocommit": "git_cocommit" in pairwise_signals,
    }
    active_signals = [name for name in weights if enabled.get(name, False)]
    weight_total = sum(weights[name] for name in active_signals)

    graph = nx.Graph()
    graph.add_nodes_from(
        (node_id, {
            "fqcn": node.fqcn,
            "package": node.package,
            "source_path": node.source_path,
            "role": node.role,
        })
        for node_id, node in facts.nodes.items()
    )
    if weight_total <= 0.0:
        graph.graph["signal_weights"] = weights
        graph.graph["active_signal_weights"] = {}
        graph.graph["minimum_edge_weight"] = minimum_edge_weight
        graph.graph["minimum_semantic_similarity"] = minimum_semantic_similarity
        graph.graph["pair_evidence_count"] = 0
        return graph
    simple_names: dict[str, list[str]] = defaultdict(list)
    for node_id, node in facts.nodes.items():
        simple_names[node.fqcn.rsplit(".", 1)[-1]].append(node_id)

    pair_evidence: dict[tuple[str, str], dict[str, Any]] = {}

    def record(left: str | None, right: str | None, signal: str, score: float, detail: dict[str, Any]) -> None:
        if not left or not right or left == right or left not in facts.nodes or right not in facts.nodes:
            return
        key = _pair(left, right)
        entry = pair_evidence.setdefault(key, {"scores": {}, "evidence": []})
        entry["scores"][signal] = max(float(score), entry["scores"].get(signal, 0.0))
        if len(entry["evidence"]) < 12:
            entry["evidence"].append({"signal": signal, **detail})

    for reference in facts.references:
        source = _resolve_node(reference.get("source"), facts, simple_names)
        target = _resolve_node(reference.get("target"), facts, simple_names)
        reference_type = str(reference.get("type", "reference")).lower()
        strength = REFERENCE_STRENGTH.get(reference_type, 0.5)
        record(source, target, "reference", strength, {
            "type": reference_type,
            "source": source,
            "target": target,
            "method": reference.get("method"),
        })

    for relation in facts.foreign_keys:
        source = _resolve_node(relation.get("source") or relation.get("from"), facts, simple_names)
        target = _resolve_node(relation.get("target") or relation.get("to"), facts, simple_names)
        record(source, target, "foreign_key", 1.0, {
            "type": relation.get("type", "foreign_key"),
            "source": source,
            "target": target,
            "field": relation.get("field"),
        })

    transaction_pair_counts: dict[tuple[str, str], int] = defaultdict(int)
    coaccess_pair_counts: dict[tuple[str, str], int] = defaultdict(int)
    for index, transaction in enumerate(facts.transactions):
        participants = sorted({
            node for value in transaction.get("participants", [])
            if (node := _resolve_node(value, facts, simple_names)) is not None
        })
        for left, right in combinations(participants, 2):
            key = _pair(left, right)
            transaction_pair_counts[key] += 1
            coaccess_pair_counts[key] += 1
            record(left, right, "workflow", 1.0, {
                "type": "transaction_co_participation",
                "transaction": transaction.get("id", transaction.get("name", index)),
            })

    explicit_coaccess = _resource_pairs(facts, simple_names)
    for key, resources in explicit_coaccess.items():
        record(key[0], key[1], "workflow", min(1.0, 0.6 + 0.1 * (len(resources) - 1)), {
            "type": "shared_data_access",
            "resources": sorted(resources),
        })

    # Select a bounded semantic-neighbor candidate set. Semantic similarity is
    # supporting evidence, not a dense all-pairs graph that overwhelms structure.
    semantic_candidates: set[tuple[str, str]] = set()
    node_ids = sorted(facts.nodes)
    neighbor_limit = max(0, nearest_neighbors)
    for node_id in node_ids:
        scored = [
            (_cosine(embeddings.get(node_id, []), embeddings.get(other, [])), other)
            for other in node_ids if other != node_id
        ]
        for similarity, other in sorted(scored, reverse=True)[:neighbor_limit]:
            if similarity >= minimum_semantic_similarity:
                semantic_candidates.add(_pair(node_id, other))

    candidate_pairs = set(pair_evidence) | semantic_candidates
    for signal_name, pair_scores in pairwise_signals.items():
        if signal_name not in weights:
            raise ValueError(f"Unknown pairwise signal: {signal_name}")
        for pair, score in pair_scores.items():
            left, right = _pair(pair[0], pair[1])
            if left not in facts.nodes or right not in facts.nodes or left == right:
                continue
            normalized_score = float(score)
            if not math.isfinite(normalized_score):
                continue
            record(left, right, signal_name, min(1.0, max(0.0, normalized_score)), {"type": signal_name})
            candidate_pairs.add((left, right))
    for left, right in sorted(candidate_pairs):
        entry = pair_evidence.setdefault((left, right), {"scores": {}, "evidence": []})
        scores = entry["scores"]
        semantic_score = _cosine(embeddings.get(left, []), embeddings.get(right, []))
        if (left, right) in semantic_candidates:
            scores["semantic"] = semantic_score
            entry["evidence"].append({"signal": "semantic", "cosine": round(semantic_score, 5)})
        package_score = _package_score(facts.nodes[left].package, facts.nodes[right].package)
        if package_score:
            scores["package"] = package_score
            entry["evidence"].append({"signal": "package", "similarity": round(package_score, 5)})

        contributions = {name: weights[name] * scores.get(name, 0.0) for name in active_signals}
        edge_weight = sum(contributions.values()) / weight_total
        if edge_weight < minimum_edge_weight:
            continue
        graph.add_edge(
            left,
            right,
            weight=edge_weight,
            signal_scores={name: round(scores.get(name, 0.0), 5) for name in active_signals if scores.get(name, 0.0) > 0.0},
            contributions={name: round(value, 5) for name, value in contributions.items() if value > 0.0},
            evidence=entry["evidence"],
            reference_types=sorted({
                item.get("type", "reference") for item in entry["evidence"]
                if item.get("signal") == "reference"
            }),
        )
    graph.graph["signal_weights"] = weights
    graph.graph["active_signal_weights"] = {name: weights[name] for name in active_signals}
    graph.graph["minimum_edge_weight"] = minimum_edge_weight
    graph.graph["minimum_semantic_similarity"] = minimum_semantic_similarity
    graph.graph["pair_evidence_count"] = len(pair_evidence)
    return graph
