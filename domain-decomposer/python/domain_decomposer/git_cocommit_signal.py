from __future__ import annotations

import subprocess
from collections import Counter
from itertools import combinations
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
