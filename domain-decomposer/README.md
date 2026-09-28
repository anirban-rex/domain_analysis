# Domain Decomposer

Evidence-driven Java monolith decomposition using a Python-only source parser, normalized node feature vectors, cosine-only edge weights, weighted Louvain clustering, and an HTML report.

The files under `../old` are historical prototypes and are not imported.

## Run

```bash
python3 -m pip install -e ".[semantic]"
python3 scripts/run_pipeline.py --source /path/to/ecommerce-backend-main.zip --output outputs
```

The Python parser reads the Java ZIP or source directory directly. It extracts class names, packages, roles, annotations, fields, method signatures, documentation comments, and references to construct concise class descriptions. By default, the pipeline embeds these descriptions with `sentence-transformers/all-MiniLM-L6-v2` and stores model/input provenance in `results.json`. The model is downloaded on first use. Override it with `--embedding-model` if needed.

A precomputed `facts.json` is also accepted. A complete set of supplied embeddings is reused; if the set is incomplete, vectors are generated for all classes with the selected model to ensure a consistent embedding space. An optional Git checkout can provide co-commit evidence.

Git co-commit features are included only when `--repository` points to a checkout containing `.git`. Without `.git`, the Git feature dimension is omitted from the node vectors and cosine calculations.

```bash
/Users/anirbansarkar/code/.venv/bin/python scripts/run_pipeline.py \
	--source /path/to/ecommerce-backend-main.zip \
	--repository /path/to/git/checkout \
	--output outputs
```
