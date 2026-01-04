from io import StringIO
from typing import Any, Dict, List

import pandas as pd
try:
    import tomllib  # Python 3.11+
except Exception:  # Python 3.10 fallback
    import tomli as tomllib
import yaml
from lxml import etree
import orjson


def validate_xml(s: str) -> bool:
    try:
        etree.fromstring(s.encode("utf-8"))
        return True
    except Exception:
        return False


def validate_toml(s: str) -> bool:
    try:
        tomllib.loads(s)
        return True
    except Exception:
        return False


def validate_yaml(s: str) -> bool:
    try:
        yaml.safe_load(s)
        return True
    except Exception:
        return False


def validate_csv(s: str) -> bool:
    try:
        # header-only CSV is valid; ensure pandas can parse it
        pd.read_csv(StringIO(s))
        return True
    except Exception:
        return False


# === Schema-conformance validators (lightweight) ===

def _type_ok(v: Any, typ: str) -> bool:
    if typ == "string":
        return isinstance(v, str)
    if typ == "bool":
        return isinstance(v, bool)
    if typ == "int":
        return isinstance(v, int) and not isinstance(v, bool)
    if typ == "float":
        # allow ints for float fields
        return (isinstance(v, float) or (isinstance(v, int) and not isinstance(v, bool)))
    return True


def _keys_exact(d: Dict[str, Any], keys: List[str]) -> bool:
    try:
        return set(d.keys()) == set(keys)
    except Exception:
        return False


def validate_json_schema_flat(s: str, keys: List[str], types: Dict[str, str]) -> bool:
    try:
        arr = orjson.loads(s)
    except Exception:
        return False
    if not isinstance(arr, list):
        return False
    for it in arr:
        if not isinstance(it, dict):
            return False
        if not _keys_exact(it, keys):
            return False
        for k in keys:
            if not _type_ok(it.get(k, None), types.get(k, "string")):
                return False
    return True


def validate_json_schema_nested(s: str, id_type: str, meta_types: Dict[str, str]) -> bool:
    try:
        arr = orjson.loads(s)
    except Exception:
        return False
    if not isinstance(arr, list):
        return False
    for it in arr:
        if not isinstance(it, dict):
            return False
        if not _keys_exact(it, ["id", "meta", "tags"]):
            return False
        if not _type_ok(it.get("id", None), id_type):
            return False
        meta = it.get("meta")
        if not isinstance(meta, dict):
            return False
        if not _keys_exact(meta, list(meta_types.keys())):
            return False
        for k, t in meta_types.items():
            if not _type_ok(meta.get(k, None), t):
                return False
        tags = it.get("tags")
        if not isinstance(tags, list):
            return False
        for tv in tags:
            if not isinstance(tv, str):
                return False
    return True


def validate_yaml_schema_flat(s: str, keys: List[str], types: Dict[str, str]) -> bool:
    try:
        obj = yaml.safe_load(s)
    except Exception:
        return False
    if not isinstance(obj, list):
        return False
    for it in obj:
        if not isinstance(it, dict):
            return False
        if not _keys_exact(it, keys):
            return False
        for k in keys:
            if not _type_ok(it.get(k, None), types.get(k, "string")):
                return False
    return True


def validate_toml_schema_items(s: str, keys: List[str], types: Dict[str, str]) -> bool:
    try:
        obj = tomllib.loads(s)
    except Exception:
        return False
    if not isinstance(obj, dict):
        return False
    if set(obj.keys()) != {"items"}:
        return False
    items = obj.get("items")
    if not isinstance(items, list):
        return False
    for it in items:
        if not isinstance(it, dict):
            return False
        if not _keys_exact(it, keys):
            return False
        for k in keys:
            if not _type_ok(it.get(k, None), types.get(k, "string")):
                return False
    return True
