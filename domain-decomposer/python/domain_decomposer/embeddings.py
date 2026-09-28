from __future__ import annotations

import hashlib
import json
from importlib.metadata import PackageNotFoundError, version
from typing import Any

from .schemas import Facts


DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def _description(facts: Facts, node_id: str) -> str:
    node = facts.nodes[node_id]
    attributes = node.attributes
    fields = attributes.get("fields", [])
    methods = attributes.get("method_signatures") or attributes.get("methods", [])
    annotations = attributes.get("annotations", [])
    related = sorted(
        {
            facts.nodes[target].fqcn
            for reference in facts.references
            for source, target in [(reference.get("source"), reference.get("target"))]
            if source == node_id and target in facts.nodes
        }
    )
    lines = [
        f"Class: {node.fqcn}",
        f"Package: {node.package}",
        f"Role: {node.role or 'unknown'}",
    ]
    if annotations:
        lines.append("Annotations: " + ", ".join(sorted(set(annotations))))
    if fields:
        lines.append("Fields: " + ", ".join(f"{field['name']}: {field['type']}" for field in fields))
    if methods:
        lines.append("Methods: " + ", ".join(methods))
    if related:
        lines.append("Related classes: " + ", ".join(related))
    documentation = attributes.get("documentation", "").strip()
    if documentation:
        lines.append("Documentation: " + documentation)
    return "\n".join(lines)


def generate(facts: Facts, model_name: str = DEFAULT_EMBEDDING_MODEL) -> tuple[dict[str, list[float]], dict[str, Any]]:
    """Generate deterministic class vectors and provenance using Sentence Transformers."""
    node_ids = sorted(facts.nodes)
    has_complete_input = bool(node_ids) and all(facts.embeddings.get(node_id) for node_id in node_ids)
    if has_complete_input:
        embeddings = {
            node_id: [float(value) for value in facts.embeddings[node_id]]
            for node_id in node_ids
        }
        dimensions = {len(vector) for vector in embeddings.values()}
        if len(dimensions) != 1:
            raise ValueError("Precomputed embeddings must all have the same dimension")
        metadata = {
            "model": "provided-input-embeddings",
            "library": None,
            "library_version": None,
            "dimensions": next(iter(dimensions), 0),
            "normalized": False,
            "generated_class_count": 0,
            "provided_class_count": len(embeddings),
            "input_sha256": None,
            "class_input_sha256": {},
        }
        return embeddings, metadata

    descriptions = {node_id: _description(facts, node_id) for node_id in node_ids}
    if descriptions:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as error:
            raise RuntimeError(
                "Semantic embeddings require the optional dependency. Install with "
                "`python -m pip install -e '.[semantic]'`."
            ) from error
        model = SentenceTransformer(model_name)
        vectors = model.encode(
            list(descriptions.values()),
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
    else:
        vectors = []

    embeddings = {
        node_id: [float(value) for value in vector]
        for node_id, vector in zip(descriptions, vectors)
    }

    input_hashes = {node_id: hashlib.sha256(text.encode("utf-8")).hexdigest() for node_id, text in descriptions.items()}
    combined_hash = hashlib.sha256(
        json.dumps(input_hashes, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    try:
        library_version = version("sentence-transformers") if descriptions else None
    except PackageNotFoundError:
        library_version = "unknown"
    dimensions = len(next(iter(embeddings.values()))) if embeddings else 0
    metadata = {
        "model": model_name,
        "library": "sentence-transformers",
        "library_version": library_version,
        "dimensions": dimensions,
        "normalized": bool(descriptions),
        "generated_class_count": len(descriptions),
        "provided_class_count": 0,
        "input_sha256": combined_hash,
        "class_input_sha256": input_hashes,
    }
    return embeddings, metadata