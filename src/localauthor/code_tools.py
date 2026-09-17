"""Inventário LEXICAL, não substitui resolução semântica do Roslyn."""
import re
from pathlib import Path
from .safety import PathPolicy


def symbols(root: Path, relative: str) -> list[dict]:
    content = PathPolicy(root).read(relative).decode("utf-8")
    rules = [
        ("type", re.compile(r"\b(?:class|interface|struct|record|enum)\s+([A-Za-z_]\w*)")),
        ("method_candidate", re.compile(r"\b(?:public|private|protected|internal)\s+(?:(?:static|async|virtual|override)\s+)*[\w<>\[\]?.,]+\s+([A-Za-z_]\w*)\s*\(")),
        ("python_function", re.compile(r"^\s*(?:async\s+)?def\s+(\w+)\s*\(")),
    ]
    result = []
    for number, line in enumerate(content.splitlines(), 1):
        for kind, pattern in rules:
            for match in pattern.finditer(line):
                result.append({"name": match.group(1), "kind": kind, "line": number, "path": relative, "method": "lexical_not_semantic"})
    return result
