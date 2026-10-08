"""Conservative presentation hints; never parse, execute or rewrite user content."""
import json
import re

_CODE_LINE = re.compile(
    r"^\s*(?:"
    r"(?:def|async\s+def|class)\s+\w+[^\n]*[:{]\s*$|"
    r"(?:export\s+)?(?:async\s+)?function\s+\w+\s*\(|"
    r"(?:const|let|var|string|int|bool|double|decimal)\s+\w+\s*=|"
    r"(?:public|private|protected|internal)\s+(?:static\s+)?(?:class|void|async|Task|[A-Z]\w*)\b|"
    r"(?:from\s+[\w.]+\s+import\s+|import\s+(?:[\w.]+|[{'\"])|using\s+[\w.]+\s*;)|"
    r"(?:SELECT\s+.+\s+FROM\b|INSERT\s+INTO\b|CREATE\s+TABLE\b|UPDATE\s+\w+\s+SET\b)|"
    r"(?:console\.(?:log|error)|print|Assert\.\w+|assert\.\w+)\s*\(|"
    r"(?:if|for|while)\s*\([^\n]*\)\s*[{:]|"
    r"(?:handle|reverse_proxy|server|location)\s+[^\n]*[{}]|"
    r"(?:return|throw)\s+[^\n]+;\s*$"
    r")", re.MULTILINE | re.IGNORECASE)
_FENCE = re.compile(r"^\s{0,3}(?:`{3,}|~{3,})", re.MULTILINE)
_MARKUP = re.compile(r"\s*<([A-Za-z][\w:-]*)\b[^>]*>[\s\S]*</\1>\s*", re.IGNORECASE)


def detect_message_format(message: str) -> str:
    if _FENCE.search(message) or _CODE_LINE.search(message) or _MARKUP.fullmatch(message):
        return "code"
    if message.lstrip().startswith(("{", "[")):
        try:
            if isinstance(json.loads(message), (dict, list)):
                return "code"
        except (ValueError, RecursionError):
            pass
    return "text"


def resolve_message_format(message: str, requested: str = "auto") -> str:
    # Preserve older API clients' explicit presentation hint.
    return detect_message_format(message) if requested == "auto" else requested
