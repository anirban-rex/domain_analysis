from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from domain_decomposer.pipeline import run
from domain_decomposer.embeddings import DEFAULT_EMBEDDING_MODEL


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a cosine-weighted Louvain domain graph.")
    parser.add_argument("--source", required=True, help="Java source directory, ZIP archive, or precomputed facts JSON")
    parser.add_argument("--repository", help="Optional Git checkout for co-commit data")
    parser.add_argument("--output", default="outputs")
    parser.add_argument("--resolution", type=float, default=1.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--nearest-neighbors", type=int, default=8)
    parser.add_argument("--min-cosine", type=float, default=0.05)
    parser.add_argument("--embedding-model", default=DEFAULT_EMBEDDING_MODEL, help="Sentence Transformers model used to embed class descriptions")
    args = parser.parse_args()
    report = run(args.source, args.output, args.repository, args.resolution, args.seed, args.nearest_neighbors, args.min_cosine, args.embedding_model)
    print(f"Report written to {report}")


if __name__ == "__main__":
    main()
