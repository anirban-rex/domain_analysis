from __future__ import annotations

import subprocess
from collections import Counter
from itertools import combinations
import math
from pathlib import Path
from .schemas import Facts
from .normalization import normalize_records


def extract(facts: Facts, repository: str | None = None, include_merges: bool = False) -> dict[str, dict]:
    counts = Counter()
    if repository:
        repository_path = Path(repository)
        if not (repository_path / ".git").exists():
            raise ValueError(f"Git repository has no .git directory: {repository}")
        command = ["git", "-C", repository, "log", "--name-only", "--pretty=format:%H %P", "--", "*.java"]
        output = subprocess.run(command, check=True, capture_output=True, text=True).stdout
        path_to_node = {node.source_path: node_id for node_id, node in facts.nodes.items()}
        current = []
        for line in output.splitlines() + [""]:
            if not line.strip():
                nodes = sorted(set(path_to_node[path] for path in current if path in path_to_node))
                for left, right in combinations(nodes, 2):
                    counts[left] += 1
                    counts[right] += 1
                current = []
            elif " " in line and not line.endswith(".java"):
                if include_merges or len(line.split()) <= 2:
                    continue
            elif line.endswith(".java"):
                current.append(line.strip())
    records = [{"node_id": node_id, "value": counts[node_id], "available": repository is not None, "metadata": {"signal": "git_cocommit"}} for node_id in facts.nodes]
    return normalize_records(records)


def extract_pairwise(facts: Facts, repository: str | None = None, include_merges: bool = False) -> dict[tuple[str, str], float]:
    """Return normalized class-pair co-change scores for cohesion edges."""
    pair_counts: Counter[tuple[str, str]] = Counter()
    if repository:
        repository_path = Path(repository)
        if not (repository_path / ".git").exists():
            raise ValueError(f"Git repository has no .git directory: {repository}")
        command = [
            "git", "-C", repository, "log", "--name-only",
            "--pretty=format:__COMMIT__%H %P", "--", "*.java",
        ]
        output = subprocess.run(command, check=True, capture_output=True, text=True).stdout
        path_to_nodes: dict[str, set[str]] = {}
        for node_id, node in facts.nodes.items():
            path_to_nodes.setdefault(Path(node.source_path).as_posix(), set()).add(node_id)
        current_paths: list[str] = []
        include_current = True

        def flush() -> None:
            if not include_current:
                return
            nodes = sorted({node_id for path in current_paths for node_id in path_to_nodes.get(path, set())})
            pair_counts.update(combinations(nodes, 2))

        for line in output.splitlines() + ["__COMMIT__"]:
            if line.startswith("__COMMIT__"):
                flush()
                parents = line[len("__COMMIT__"):].strip().split()[1:]
                include_current = include_merges or len(parents) <= 1
                current_paths = []
            elif line.strip().endswith(".java"):
                current_paths.append(line.strip())
    else:
        for commit in facts.commits:
            participants = sorted(set(commit.get("participants", [])) & set(facts.nodes))
            pair_counts.update(combinations(participants, 2))

    maximum = max(pair_counts.values(), default=0)
    if maximum == 0:
        return {}
    return {
        pair: min(1.0, math.log1p(count) / math.log1p(maximum))
        for pair, count in pair_counts.items()
    }
