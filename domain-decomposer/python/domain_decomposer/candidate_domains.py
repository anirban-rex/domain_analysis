from __future__ import annotations

import re
from collections import Counter, defaultdict
from typing import Any

import networkx as nx

from .schemas import Facts
from .service_boundaries import _is_service_anchor


_SUFFIX = re.compile(r"(?:ServiceImpl|Service|UseCase|Manager|Handler)$", re.IGNORECASE)


def _anchor_label(fqcn: str) -> str:
    simple_name = fqcn.rsplit(".", 1)[-1]
    stem = _SUFFIX.sub("", simple_name)
    words = re.findall(r"[A-Z]+(?=[A-Z][a-z]|\d|$)|[A-Z]?[a-z]+|\d+", stem)
    return " ".join(word.capitalize() for word in words) or stem or simple_name


def _domain_name(cluster_id: int, anchor_ids: list[str], facts: Facts) -> str:
    labels = sorted({_anchor_label(facts.nodes[node_id].fqcn) for node_id in anchor_ids})
    if len(labels) == 1:
        return labels[0]
    if labels:
        visible = labels[:3]
        suffix = f" +{len(labels) - len(visible)}" if len(labels) > len(visible) else ""
        return " + ".join(visible) + suffix
    return f"Candidate domain {cluster_id}"


def _edge_communities(graph: nx.Graph, labels: dict[str, int]) -> tuple[dict[int, float], dict[int, float], dict[str, dict[str, Any]]]:
    internal: dict[int, float] = defaultdict(float)
    external: dict[int, float] = defaultdict(float)
    node_external: dict[str, dict[str, Any]] = {}
    for left, right, data in graph.edges(data=True):
        left_cluster, right_cluster = labels.get(left, 0), labels.get(right, 0)
        weight = float(data.get("weight", 0.0))
        if left_cluster == right_cluster:
            internal[left_cluster] += weight
            continue
        external[left_cluster] += weight
        external[right_cluster] += weight
        for node_id, other_cluster in ((left, right_cluster), (right, left_cluster)):
            row = node_external.setdefault(node_id, {"weight": 0.0, "clusters": set()})
            row["weight"] += weight
            row["clusters"].add(other_cluster)
    return internal, external, node_external


def build_candidate_domains(facts: Facts, graph: nx.Graph, labels: dict[str, int]) -> dict[str, Any]:
    """Turn Louvain membership into reviewable, evidence-backed candidates."""
    cluster_members: dict[int, list[str]] = defaultdict(list)
    for node_id in facts.nodes:
        cluster_members[labels.get(node_id, 0)].append(node_id)
    internal_weight, external_weight, node_external = _edge_communities(graph, labels)

    anchors_by_cluster: dict[int, list[str]] = defaultdict(list)
    for node_id, node in facts.nodes.items():
        if _is_service_anchor(node):
            anchors_by_cluster[labels.get(node_id, 0)].append(node_id)

    ambiguous_by_cluster: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for node_id, relation in node_external.items():
        cluster_id = labels.get(node_id, 0)
        incident_weight = sum(float(data.get("weight", 0.0)) for _, _, data in graph.edges(node_id, data=True))
        own_weight = max(0.0, incident_weight - relation["weight"])
        if len(relation["clusters"]) >= 2 and relation["weight"] >= own_weight:
            ambiguous_by_cluster[cluster_id].append({
                "node_id": node_id,
                "fqcn": facts.nodes[node_id].fqcn,
                "external_weight": round(relation["weight"], 5),
                "internal_weight": round(own_weight, 5),
                "neighbor_clusters": sorted(relation["clusters"]),
            })

    domains: list[dict[str, Any]] = []
    for cluster_id in sorted(cluster_members):
        members = sorted(cluster_members[cluster_id])
        anchors = sorted(anchors_by_cluster.get(cluster_id, []))
        incident_weight = internal_weight.get(cluster_id, 0.0) + external_weight.get(cluster_id, 0.0)
        cohesion = internal_weight.get(cluster_id, 0.0) / incident_weight if incident_weight else 0.0
        role_counts = Counter((facts.nodes[node_id].role or "unknown") for node_id in members)
        boundary_edges = []
        for left, right, data in graph.edges(data=True):
            if labels.get(left, 0) == cluster_id and labels.get(right, 0) != cluster_id:
                boundary_edges.append({"source": left, "target": right, "weight": round(float(data.get("weight", 0.0)), 5), "signals": data.get("signal_scores", {})})
            elif labels.get(right, 0) == cluster_id and labels.get(left, 0) != cluster_id:
                boundary_edges.append({"source": right, "target": left, "weight": round(float(data.get("weight", 0.0)), 5), "signals": data.get("signal_scores", {})})
        reasons = []
        if not anchors:
            reasons.append("No recognized service/use-case anchor is present in this community.")
        if len(anchors) > 1:
            reasons.append("Multiple service anchors share this community; review whether they represent one capability.")
        if incident_weight and cohesion < 0.5:
            reasons.append("More weighted graph evidence crosses the community boundary than stays inside it.")
        if ambiguous_by_cluster.get(cluster_id):
            reasons.append("One or more classes have strong connections to multiple other communities.")
        domains.append({
            "id": cluster_id,
            "name": _domain_name(cluster_id, anchors, facts),
            "members": members,
            "anchors": anchors,
            "anchor_names": [facts.nodes[node_id].fqcn for node_id in anchors],
            "role_counts": dict(sorted(role_counts.items())),
            "internal_edge_weight": round(internal_weight.get(cluster_id, 0.0), 5),
            "external_edge_weight": round(external_weight.get(cluster_id, 0.0), 5),
            "cohesion": round(cohesion, 4),
            "boundary_edges": boundary_edges,
            "ambiguous_classes": ambiguous_by_cluster.get(cluster_id, []),
            "review_reasons": reasons,
            "review_required": bool(reasons),
        })

    cross_domain_dependencies = []
    for reference in facts.references:
        source, target = reference.get("source"), reference.get("target")
        if source in facts.nodes and target in facts.nodes and labels.get(source) != labels.get(target):
            cross_domain_dependencies.append({
                "source": source,
                "target": target,
                "type": reference.get("type", "reference"),
                "method": reference.get("method"),
                "source_domain": labels.get(source, 0),
                "target_domain": labels.get(target, 0),
            })

    return {
        "domains": domains,
        "assignments": {node_id: labels.get(node_id, 0) for node_id in facts.nodes},
        "cross_domain_dependencies": cross_domain_dependencies,
        "review_required_count": sum(domain["review_required"] for domain in domains),
        "anchor_count": sum(len(domain["anchors"]) for domain in domains),
    }
