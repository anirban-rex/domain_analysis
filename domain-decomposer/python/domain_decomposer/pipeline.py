from __future__ import annotations

from pathlib import Path
from .schemas import Facts
from .foreign_key_signal import extract as extract_foreign_keys
from .transaction_signal import extract as extract_transactions
from .data_coaccess_signal import extract as extract_coaccess
from .git_cocommit_signal import extract as extract_cocommits
from .semantic_signal import extract as extract_semantic
from .feature_matrix import BASE_SIGNALS, build
from .cosine_graph import build_graph
from .louvain_domains import detect
from .html_report import render
from .io_utils import load_json, write_json
from .java_source_parser import parse as parse_java_source
from .service_boundaries import extract as extract_services
from .embeddings import DEFAULT_EMBEDDING_MODEL, generate as generate_embeddings


def run(source: str, output_dir: str, repository: str | None = None, resolution: float = 1.0, seed: int = 42, nearest_neighbors: int = 8, min_cosine: float = 0.05, embedding_model: str = DEFAULT_EMBEDDING_MODEL) -> Path:
    source_path = Path(source)
    payload = load_json(source) if source_path.suffix.lower() == ".json" else parse_java_source(source)
    facts = Facts.from_json(payload)
    signal_maps = {
        "foreign_key": extract_foreign_keys(facts),
        "transaction": extract_transactions(facts),
        "data_coaccess": extract_coaccess(facts),
    }
    repository_path = Path(repository).expanduser() if repository else None
    git_available = bool(repository_path and (repository_path / ".git").exists())
    if git_available:
        signal_maps["git_cocommit"] = extract_cocommits(facts, str(repository_path))
    active_signals = tuple(BASE_SIGNALS) + (("git_cocommit",) if git_available else ())
    facts.embeddings, embedding_metadata = generate_embeddings(facts, embedding_model)
    semantic = extract_semantic(facts)
    services = extract_services(facts, facts.embeddings)
    matrix = build(facts, signal_maps, semantic, active_signals)
    graph = build_graph(facts, matrix, nearest_neighbors, min_cosine)
    labels, score = detect(graph, resolution, seed)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "results.json", {"modularity": score, "communities": labels, "services": services, "semantic_metadata": embedding_metadata, "feature_names": matrix.feature_names, "vectors": {node_id: vector.tolist() for node_id, vector in matrix.vectors.items()}, "masks": matrix.masks, "edges": [{"source": left, "target": right, "weight": data["weight"]} for left, right, data in graph.edges(data=True)]})
    coverage = {name: sum(1 for record in values.values() if record.get("available", False)) for name, values in signal_maps.items()}
    coverage["semantic"] = sum(bool(value) for value in semantic.values())
    report = output / "domain_report.html"
    render(report, graph, labels, score, matrix.feature_names, coverage, services)
    return report
