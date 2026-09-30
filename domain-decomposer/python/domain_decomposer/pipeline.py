from __future__ import annotations

from pathlib import Path
from .schemas import Facts
from .foreign_key_signal import extract as extract_foreign_keys
from .transaction_signal import extract as extract_transactions
from .data_coaccess_signal import extract as extract_coaccess
from .git_cocommit_signal import extract as extract_cocommits, extract_pairwise as extract_git_pairs
from .semantic_signal import extract as extract_semantic
from .feature_matrix import BASE_SIGNALS, build
from .cohesion_graph import DEFAULT_SIGNAL_WEIGHTS, build_graph
from .louvain_domains import detect
from .candidate_domains import build_candidate_domains
from .html_report import render
from .io_utils import load_json, write_json
from .java_source_parser import parse as parse_java_source
from .service_boundaries import extract as extract_services
from .embeddings import DEFAULT_EMBEDDING_MODEL, generate as generate_embeddings


def run(source: str, output_dir: str, repository: str | None = None, resolution: float = 1.0, seed: int = 42, nearest_neighbors: int = 8, min_edge_weight: float = 0.08, embedding_model: str = DEFAULT_EMBEDDING_MODEL, signal_weights: dict[str, float] | None = None, minimum_semantic_similarity: float = 0.45, include_git_merges: bool = False) -> Path:
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
        signal_maps["git_cocommit"] = extract_cocommits(facts, str(repository_path), include_git_merges)
    pairwise_signals = {}
    if git_available:
        pairwise_signals["git_cocommit"] = extract_git_pairs(facts, str(repository_path), include_git_merges)
    elif facts.commits:
        pairwise_signals["git_cocommit"] = extract_git_pairs(facts)
    active_signals = tuple(BASE_SIGNALS) + (("git_cocommit",) if git_available else ())
    facts.embeddings, embedding_metadata = generate_embeddings(facts, embedding_model)
    semantic = extract_semantic(facts)
    services = extract_services(facts, facts.embeddings)
    matrix = build(facts, signal_maps, semantic, active_signals)
    graph = build_graph(facts, facts.embeddings, nearest_neighbors, min_edge_weight, minimum_semantic_similarity, signal_weights, pairwise_signals)
    labels, score = detect(graph, resolution, seed)
    candidate_domains = build_candidate_domains(facts, graph, labels)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "results.json", {"modularity": score, "communities": labels, "candidate_domains": candidate_domains, "services": services, "semantic_metadata": embedding_metadata, "signal_weights": graph.graph.get("active_signal_weights", DEFAULT_SIGNAL_WEIGHTS), "configured_signal_weights": graph.graph.get("signal_weights", DEFAULT_SIGNAL_WEIGHTS), "minimum_edge_weight": min_edge_weight, "feature_names": matrix.feature_names, "vectors": {node_id: vector.tolist() for node_id, vector in matrix.vectors.items()}, "masks": matrix.masks, "edges": [{"source": left, "target": right, "weight": data["weight"], "signal_scores": data.get("signal_scores", {}), "contributions": data.get("contributions", {}), "evidence": data.get("evidence", [])} for left, right, data in graph.edges(data=True)]})
    coverage = {name: sum(1 for record in values.values() if record.get("available", False)) for name, values in signal_maps.items()}
    coverage["semantic"] = sum(bool(value) for value in semantic.values())
    for signal_name in graph.graph.get("active_signal_weights", {}):
        coverage[f"pairwise_{signal_name}_edges"] = sum(
            1 for _, _, data in graph.edges(data=True)
            if data.get("signal_scores", {}).get(signal_name, 0.0) > 0.0
        )
    report = output / "domain_report.html"
    render(report, graph, labels, score, matrix.feature_names, coverage, services, candidate_domains)
    return report
