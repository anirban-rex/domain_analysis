from __future__ import annotations

import re
import zipfile
from pathlib import Path
from typing import Iterable


JAVA_FILE = re.compile(r"(?:^|/)src/main/java/(.+\.java)$")
PACKAGE = re.compile(r"\bpackage\s+([\w.]+)\s*;")
TYPE_DECLARATION = re.compile(r"\b(?:class|interface|enum|record)\s+(\w+)")
IMPORT = re.compile(r"\bimport\s+(?:static\s+)?([\w.]+)\s*;")
ANNOTATION = re.compile(r"@(?:javax\.persistence\.|jakarta\.persistence\.|org\.springframework\.transaction\.annotation\.)?(\w+)(?:\s*\(([^)]*)\))?")
FIELD_RELATION = re.compile(r"@(ManyToOne|OneToMany|OneToOne|ManyToMany)\s*(?:\(([^)]*)\))?\s*(?:private|protected|public)?\s*(?:final\s+)?([\w.$<>?, ]+)\s+(\w+)\s*;", re.MULTILINE)
FIELD = re.compile(r"(?:private|protected|public)\s+(?:final\s+)?([\w.$<>?, ]+)\s+(\w+)\s*(?:=[^;]+)?;", re.MULTILINE)
METHOD = re.compile(r"(?:public|protected|private|static|final|synchronized|\s)+[\w<>, ?\[\].]+\s+(\w+)\s*\([^)]*\)\s*\{", re.MULTILINE)
METHOD_SIGNATURE = re.compile(r"\b(?:public|protected|private)\s+(?:(?:static|final|synchronized|abstract)\s+)*([\w.$<>, ?\[\]]+)\s+(\w+)\s*\(([^)]*)\)", re.MULTILINE)
CALL = re.compile(r"\b([A-Za-z_]\w*)\s*\.\s*([A-Za-z_]\w*)\s*\(")


def _java_sources(source: str | Path) -> Iterable[tuple[str, str]]:
    path = Path(source)
    if path.is_file() and path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as archive:
            for name in archive.namelist():
                if JAVA_FILE.search(name):
                    yield name, archive.read(name).decode("utf-8", errors="replace")
        return
    root = path
    for file_path in root.rglob("*.java"):
        relative = file_path.relative_to(root).as_posix()
        if "src/test" not in relative and (root.name == "java" or "src/main/java/" in f"/{relative}"):
            yield relative, file_path.read_text(encoding="utf-8", errors="replace")


def _annotation_values(text: str) -> dict[str, str]:
    values = {}
    for key, value in re.findall(r"(\w+)\s*=\s*([^,]+)", text):
        values[key] = value.strip().strip('"')
    return values


def parse(source: str | Path) -> dict:
    nodes: dict[str, dict] = {}
    files: list[tuple[str, str, str]] = []
    simple_names: dict[str, str] = {}
    for source_path, text in _java_sources(source):
        package_match = PACKAGE.search(text)
        package = package_match.group(1) if package_match else ""
        declaration = TYPE_DECLARATION.search(text)
        if not declaration:
            continue
        simple_name = declaration.group(1)
        fqcn = f"{package}.{simple_name}" if package else simple_name
        role = "class"
        lowered = simple_name.lower()
        for suffix, candidate in (("controller", "controller"), ("service", "service"), ("repository", "repository")):
            if lowered.endswith(suffix):
                role = candidate
        annotations = [name for name, _ in ANNOTATION.findall(text)]
        fields = [{"type": field_type.strip(), "name": field_name} for field_type, field_name in FIELD.findall(text)]
        methods = [name for name in METHOD.findall(text) if name]
        method_signatures = [
            f"{return_type.strip()} {name}({parameters.strip()})"
            for return_type, name, parameters in METHOD_SIGNATURE.findall(text)
        ]
        comments = re.findall(r"/\*\*(.*?)\*/", text, re.DOTALL)
        nodes[fqcn] = {
            "id": fqcn,
            "fqcn": fqcn,
            "package": package,
            "source_path": source_path,
            "role": role,
            "attributes": {
                "annotations": sorted(set(annotations)),
                "fields": fields,
                "methods": methods,
                "method_signatures": method_signatures,
                "documentation": " ".join(re.sub(r"\s*\* ?", " ", comment).strip() for comment in comments),
            },
        }
        simple_names[simple_name] = fqcn
        files.append((source_path, text, fqcn))

    references, foreign_keys, transactions = [], [], []
    for source_path, text, source_id in files:
        imports = set(IMPORT.findall(text))
        for imported in imports:
            if imported in nodes:
                references.append({"source": source_id, "target": imported, "type": "import"})
        for type_name in re.findall(r"\b(?:new\s+|extends\s+|implements\s+|return\s+|\w+\s+)([A-Z]\w*)", text):
            target = simple_names.get(type_name)
            if target and target != source_id:
                references.append({"source": source_id, "target": target, "type": "type_reference"})
        for relation, annotation_text, field_type, field_name in FIELD_RELATION.findall(text):
            target_name = re.sub(r".*<\s*([A-Z]\w*)\s*>.*", r"\1", field_type).strip()
            target = simple_names.get(target_name, target_name)
            values = _annotation_values(annotation_text or "")
            foreign_keys.append({"source": source_id, "target": target, "type": relation, "field": field_name, "join_column": values.get("name", ""), "cascade": values.get("cascade", "")})
        class_transactional = any(name == "Transactional" for name, _ in ANNOTATION.findall(text[: text.find("{") if "{" in text else 0]))
        methods = [name for name in METHOD.findall(text) if name]
        transactional_methods = []
        for match in re.finditer(r"@Transactional(?:\s*\([^)]*\))?\s*" + METHOD.pattern, text):
            transactional_methods.append(match.group(1))
        if class_transactional or transactional_methods:
            transactions.append({"owner": source_id, "participants": [source_id], "methods": transactional_methods or methods})
        for receiver, method in CALL.findall(text):
            if receiver in simple_names:
                references.append({"source": source_id, "target": simple_names[receiver], "type": "method_call", "method": method})
    return {"schema_version": "1.0", "nodes": list(nodes.values()), "references": references, "foreign_keys": foreign_keys, "transactions": transactions, "method_accesses": [], "commits": [], "embeddings": {}}
