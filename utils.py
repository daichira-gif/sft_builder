import hashlib
import os
import re
import time
from typing import Any

import orjson

from .config import (
    MAX_INPUT_CHARS,
    MAX_OUTPUT_CHARS,
)


def ensure_dirs(*paths: str) -> None:
    for p in paths:
        os.makedirs(p, exist_ok=True)


def now_ms() -> int:
    return int(time.time() * 1000)


def sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


def clip(s: Any, n: int) -> str:
    s = str(s) if s is not None else ""
    return s if len(s) <= n else s[:n] + "…"


def clip_raw(s: Any, n: int) -> str:
    s = str(s) if s is not None else ""
    return s if len(s) <= n else s[:n] + "…"


def norm(s: Any) -> str:
    return re.sub(r"\s+", " ", str(s)).strip() if s is not None else ""


def truncate_prompt(s: Any) -> str:
    return clip(norm(s), MAX_INPUT_CHARS)


def truncate(s: Any) -> str:
    return truncate_prompt(s)


def safe_json(obj: Any, max_chars: int = MAX_OUTPUT_CHARS) -> str:
    """Serialize to JSON; if too long try shrinking common shape {"items": [...]}."""

    def dumps(x: Any) -> str:
        return orjson.dumps(x, option=orjson.OPT_SORT_KEYS).decode()

    try:
        s = dumps(obj)
        if len(s) <= max_chars:
            return s
    except Exception:
        return "{}"

    # Defer actual shrinking to callers (serialization layer) to avoid imports cycle
    try:
        return dumps({})
    except Exception:
        return "{}"


def append_jsonl(path: str, obj: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "ab") as f:
        f.write(orjson.dumps(obj) + b"\n")


def is_ascii_key(s: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_\-\.]*", s or ""))


def sanitize_toml_key(k: str) -> str:
    k = str(k).strip()
    if not k:
        return "field"
    if is_ascii_key(k):
        return k
    k_esc = k.replace("\\", "\\\\").replace('"', '\"')
    return f'"{k_esc}"'

