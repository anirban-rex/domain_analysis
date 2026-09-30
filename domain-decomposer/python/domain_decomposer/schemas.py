from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Node:
    id: str
    fqcn: str
    package: str = ""
    source_path: str = ""
    role: str = ""
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class Facts:
    nodes: dict[str, Node]
    references: list[dict[str, Any]] = field(default_factory=list)
    foreign_keys: list[dict[str, Any]] = field(default_factory=list)
    transactions: list[dict[str, Any]] = field(default_factory=list)
    method_accesses: list[dict[str, Any]] = field(default_factory=list)
    commits: list[dict[str, Any]] = field(default_factory=list)
    embeddings: dict[str, list[float]] = field(default_factory=dict)
    signal_availability: dict[str, bool] = field(default_factory=dict)

    @classmethod
    def from_json(cls, payload: dict[str, Any]) -> "Facts":
        nodes = {}
        for item in payload.get("nodes", []):
            node = Node(**{key: item.get(key, "") for key in ("id", "fqcn", "package", "source_path", "role")}, attributes=item.get("attributes", {}))
            nodes[node.id] = node
        signal_availability = {
            "reference": "references" in payload,
            "foreign_key": "foreign_keys" in payload,
            "workflow": "transactions" in payload or "method_accesses" in payload,
            "git_cocommit": "commits" in payload,
            "semantic": bool(payload.get("embeddings")),
            "package": any(bool(node.package) for node in nodes.values()),
        }
        return cls(nodes=nodes, references=payload.get("references", []), foreign_keys=payload.get("foreign_keys", []), transactions=payload.get("transactions", []), method_accesses=payload.get("method_accesses", []), commits=payload.get("commits", []), embeddings=payload.get("embeddings", {}), signal_availability=signal_availability)


def signal_record(node_id: str, value: float, available: bool = True, **metadata: Any) -> dict[str, Any]:
    return {"node_id": node_id, "value": float(value), "available": available, "metadata": metadata}
