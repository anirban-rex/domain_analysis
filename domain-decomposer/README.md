# Domain Decomposer

Evidence-driven Java monolith analysis using a Python source parser, pairwise signal-weighted cohesion graph, Louvain candidate domains, and an interactive HTML review report. The generated domains are provisional architecture candidates, not approved microservices.

The files under `../old` are historical prototypes and are not imported.

## Run

```bash
python3 -m pip install -e ".[semantic]"
python3 scripts/run_pipeline.py --source /path/to/ecommerce-backend-main.zip --output outputs
```

The Python parser reads the Java ZIP or source directory directly. It extracts class names, packages, roles (including common Spring stereotypes), annotations, fields, method signatures, documentation comments, and references to construct concise class descriptions. By default, the pipeline embeds these descriptions with `sentence-transformers/all-MiniLM-L6-v2` and stores model/input provenance in `results.json`. The model is downloaded on first use. Override it with `--embedding-model` if needed.

A precomputed `facts.json` is also accepted. A complete set of supplied embeddings is reused; if the set is incomplete, vectors are generated for all classes with the selected model to ensure a consistent embedding space. An optional Git checkout can provide pairwise co-change evidence.

The weighted class graph combines typed references, transaction/data-access relationships, foreign-key/entity relationships, semantic nearest neighbors, package proximity, and optional Git co-change evidence. Louvain assigns all classes to communities; the HTML report presents these as candidate domains with their anchors, member classes, cohesion indicators, ambiguous ownership flags, and direct dependencies crossing candidate boundaries. Review the results before treating a candidate as a bounded context or microservice.

Signal contributions are recorded per edge and in `results.json`. The CLI loads `config/default.yaml` by default; use `--config` to select another YAML file. Override settings with CLI options such as `--min-edge-weight` or repeated `--signal-weight SIGNAL=WEIGHT` options (`reference`, `workflow`, `foreign_key`, `semantic`, `package`, and `git_cocommit`).

Git co-commit features are included only when `--repository` points to a checkout containing `.git`. Without `.git`, the Git feature dimension is omitted from the node vectors and cosine calculations.

```bash
/Users/anirbansarkar/code/.venv/bin/python scripts/run_pipeline.py \
	--source /path/to/ecommerce-backend-main.zip \
	--repository /path/to/git/checkout \
	--output outputs
```
