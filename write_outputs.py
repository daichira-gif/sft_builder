import os
from typing import Dict, List, Tuple

import orjson

from .config import DEBUG_DIR, OUT_DIR, XML_FAIL_LOG, TOML_FAIL_LOG, REJECT_LOG
from .utils import ensure_dirs


def _deduplicate_outputs(outputs: Dict[str, List[dict]]) -> Tuple[Dict[str, List[dict]], Dict[str, int]]:
    """Remove duplicate samples per file based on stable `id`.

    Returns (deduped_outputs, removed_counts).
    """
    deduped: Dict[str, List[dict]] = {}
    removed: Dict[str, int] = {}
    for name, data in outputs.items():
        seen = set()
        out = []
        rm = 0
        for r in data:
            rid = r.get("id")
            if rid is None:
                # fallback to hash of messages
                try:
                    import hashlib, orjson

                    key = hashlib.sha1(orjson.dumps(r.get("messages", []))).hexdigest()
                except Exception:
                    key = None
                rid = key
            if rid in seen and rid is not None:
                rm += 1
                continue
            seen.add(rid)
            out.append(r)
        deduped[name] = out
        removed[name] = rm
    return deduped, removed


def write_outputs(outputs: Dict[str, List[dict]]):
    ensure_dirs(OUT_DIR, DEBUG_DIR)
    # Deduplicate by id to avoid overweighting identical samples
    outputs, removed = _deduplicate_outputs(outputs)
    if any(v > 0 for v in removed.values()):
        print("[dedup] removed duplicates per file:", removed)
    for name, data in outputs.items():
        path = os.path.join(OUT_DIR, name)
        with open(path, "w", encoding="utf-8") as f:
            for r in data:
                f.write(orjson.dumps(r).decode() + "\n")
        print("Wrote", name, ":", len(data), "samples ->", path)

    print("[XML failure log]", XML_FAIL_LOG, "exists:", os.path.exists(XML_FAIL_LOG), "size:", os.path.getsize(XML_FAIL_LOG) if os.path.exists(XML_FAIL_LOG) else 0)
    print("[TOML failure log]", TOML_FAIL_LOG, "exists:", os.path.exists(TOML_FAIL_LOG), "size:", os.path.getsize(TOML_FAIL_LOG) if os.path.exists(TOML_FAIL_LOG) else 0)
    print("[P0 reject log]", REJECT_LOG, "exists:", os.path.exists(REJECT_LOG), "size:", os.path.getsize(REJECT_LOG) if os.path.exists(REJECT_LOG) else 0)

    present = sorted([fn for fn in os.listdir(OUT_DIR) if fn.endswith(".jsonl")])
    debug = sorted(os.listdir(DEBUG_DIR)) if os.path.exists(DEBUG_DIR) else []
    print("Present files:", present)
    print("Debug files:", debug)
