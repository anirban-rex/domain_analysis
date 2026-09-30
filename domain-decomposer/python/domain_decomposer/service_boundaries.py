from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

import numpy as np

from .schemas import Facts


ROLE_ANCHORS = {"service", "handler", "use_case", "manager"}
TECHNICAL_ROLES = {"controller", "repository", "dto", "config", "mapper", "exception"}


def _tokens(value: str) -> set[str]:
    words = re.findall(r"[A-Z]+(?=[A-Z][a-z]|\d|$)|[A-Z]?[a-z]+|\d+", value)
    return {word.lower() for word in words if len(word) > 1}


def _is_service_anchor(node: Any) -> bool:
    name = node.fqcn.rsplit(".", 1)[-1]
    role = str(node.role or "").lower()
    lowered = name.lower()
    annotations = {str(annotation).rsplit(".", 1)[-1].lower() for annotation in (node.attributes or {}).get("annotations", []) or []}
    if lowered.endswith(("successhandler", "accessdeniedhandler", "exceptionhandler", "failurehandler")):
        return False
    if ".security." in node.package or ".common." in node.package:
        return role == "service" or "service" in annotations
    return (
        role in ROLE_ANCHORS
        or bool(annotations & {"service", "usecase"})
        or lowered.endswith(("service", "serviceimpl", "usecase", "manager"))
    )


def _service_key(node: Any) -> str:
    return node.fqcn


def _cosine(left: list[float], right: list[float]) -> float:
    if not left or not right:
        return 0.0
    size = min(len(left), len(right))
    left_array, right_array = np.asarray(left[:size]), np.asarray(right[:size])
    denominator = float(np.linalg.norm(left_array) * np.linalg.norm(right_array))
    return float(np.dot(left_array, right_array) / denominator) if denominator else 0.0


def extract(facts: Facts, embeddings: dict[str, list[float]] | None = None, minimum_affinity: float = 0.15) -> dict[str, Any]:
    embeddings = embeddings or facts.embeddings
    anchor_nodes = {node_id: node for node_id, node in facts.nodes.items() if _is_service_anchor(node)}
    anchors: dict[str, list[str]] = defaultdict(list)
    for node_id, node in anchor_nodes.items():
        anchors[_service_key(node)].append(node_id)
    if not anchor_nodes:
        return {"anchors": {}, "assignments": {}, "groups": {}, "shared": [], "cross_boundary": []}

    outgoing: dict[str, set[str]] = defaultdict(set)
    incoming: dict[str, set[str]] = defaultdict(set)
    for reference in facts.references:
        source, target = reference.get("source"), reference.get("target")
        if source in facts.nodes and target in facts.nodes:
            outgoing[source].add(target)
            incoming[target].add(source)

    assignments: dict[str, str] = {}
    affinities: dict[str, dict[str, float]] = {}
    shared: list[str] = []
    cross_boundary: list[dict[str, Any]] = []
    for node_id, node in facts.nodes.items():
        if node_id in anchor_nodes:
            assignments[node_id] = _service_key(anchor_nodes[node_id])
            affinities[node_id] = {assignments[node_id]: 1.0}
            continue
        node_tokens = _tokens(node.fqcn + " " + node.package)
        scores: dict[str, float] = {}
        for service_key, anchor_ids in anchors.items():
            anchor = anchor_nodes[anchor_ids[0]]
            anchor_tokens = _tokens(service_key + " " + anchor.package)
            score = 0.0
            for anchor_id in anchor_ids:
                if anchor_id in outgoing[node_id] or anchor_id in incoming[node_id]:
                    score += 0.60
                if node_id in outgoing[anchor_id] or node_id in incoming[anchor_id]:
                    score += 0.25
            if node.package and anchor.package and (node.package == anchor.package or node.package.startswith(anchor.package + ".") or anchor.package.startswith(node.package + ".")):
                score += 0.20
            overlap = node_tokens & anchor_tokens
            if overlap:
                score += min(0.30, 0.10 * len(overlap))
            score += 0.40 * max(0.0, max((_cosine(embeddings.get(node_id, []), embeddings.get(anchor_id, [])) for anchor_id in anchor_ids), default=0.0))
            scores[service_key] = score
        ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        best_anchor, best_score = ordered[0]
        second_score = ordered[1][1] if len(ordered) > 1 else 0.0
        affinities[node_id] = scores
        if best_score < minimum_affinity:
            shared.append(node_id)
        else:
            assignments[node_id] = best_anchor
        if len(ordered) > 1 and best_score > minimum_affinity and best_score - second_score < 0.10:
            cross_boundary.append({"node_id": node_id, "primary": best_anchor, "secondary": ordered[1][0], "primary_score": round(best_score, 4), "secondary_score": round(second_score, 4)})

    groups: dict[str, list[str]] = {anchor_id: [] for anchor_id in anchors}
    for node_id, anchor_id in assignments.items():
        groups.setdefault(anchor_id, []).append(node_id)
    names = {service_key: _service_name(service_key) for service_key in anchors}
    return {"anchors": names, "assignments": assignments, "groups": groups, "shared": shared, "cross_boundary": cross_boundary, "affinities": affinities}


def _service_name(fqcn: str) -> str:
    name = fqcn.rsplit(".", 1)[-1]
    name = re.sub(r"(ServiceImpl|Service|Handler|UseCase|Manager)$", "", name)
    return " ".join(part.capitalize() for part in _tokens(name)) or name
