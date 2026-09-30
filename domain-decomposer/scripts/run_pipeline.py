from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from domain_decomposer.pipeline import run
from domain_decomposer.embeddings import DEFAULT_EMBEDDING_MODEL
from domain_decomposer.cohesion_graph import DEFAULT_SIGNAL_WEIGHTS


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a signal-weighted Louvain candidate-domain graph.")
    parser.add_argument("--config", default=str(ROOT / "config" / "default.yaml"), help="YAML configuration file")
    parser.add_argument("--source", required=True, help="Java source directory, ZIP archive, or precomputed facts JSON")
    parser.add_argument("--repository", help="Optional Git checkout for co-commit data")
    parser.add_argument("--output", default="outputs")
    parser.add_argument("--resolution", type=float)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--nearest-neighbors", type=int)
    parser.add_argument("--min-edge-weight", type=float, help="Minimum pairwise cohesion score required for a graph edge")
    parser.add_argument("--minimum-semantic-similarity", type=float, help="Minimum cosine used to propose semantic-neighbor edges")
    parser.add_argument("--signal-weight", action="append", default=[], metavar="SIGNAL=WEIGHT", help="Override a cohesion signal weight; repeat as needed (signals: " + ", ".join(DEFAULT_SIGNAL_WEIGHTS) + ")")
    parser.add_argument("--embedding-model", help="Sentence Transformers model used to embed class descriptions")
    parser.add_argument("--include-git-merges", action="store_true", default=None, help="Include merge commits in the Git co-change signal")
    args = parser.parse_args()
    try:
        config = yaml.safe_load(Path(args.config).read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as error:
        parser.error(f"Cannot load configuration {args.config}: {error}")
    signal_weights = {}
    for item in args.signal_weight:
        try:
            name, value = item.split("=", 1)
            signal_weights[name] = float(value)
        except ValueError as error:
            parser.error(f"Invalid --signal-weight {item!r}; expected SIGNAL=WEIGHT")
    configured_weights = dict(config.get("signal_weights", DEFAULT_SIGNAL_WEIGHTS))
    configured_weights.update(signal_weights)
    report = run(
        source=args.source,
        output_dir=args.output,
        repository=args.repository,
        resolution=args.resolution if args.resolution is not None else config.get("resolution", 1.0),
        seed=args.seed if args.seed is not None else config.get("seed", 42),
        nearest_neighbors=args.nearest_neighbors if args.nearest_neighbors is not None else config.get("nearest_neighbors", 8),
        min_edge_weight=args.min_edge_weight if args.min_edge_weight is not None else config.get("minimum_edge_weight", 0.08),
        embedding_model=args.embedding_model or DEFAULT_EMBEDDING_MODEL,
        signal_weights=configured_weights,
        minimum_semantic_similarity=args.minimum_semantic_similarity if args.minimum_semantic_similarity is not None else config.get("minimum_semantic_similarity", 0.45),
        include_git_merges=args.include_git_merges if args.include_git_merges is not None else config.get("git_include_merges", False),
    )
    print(f"Report written to {report}")


if __name__ == "__main__":
    main()
