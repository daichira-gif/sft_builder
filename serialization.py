from io import StringIO
from typing import Any, Dict, List, Optional

import pandas as pd
import yaml
from lxml import etree

from .config import (
    MAX_ATTRS,
    MAX_CELL_CHARS,
    MAX_INPUT_CHARS,
    MAX_OUTPUT_CHARS,
    MAX_ROWS_PER_SAMPLE,
)
from .utils import clip, norm, is_ascii_key, sanitize_toml_key
from .validators import validate_csv, validate_xml, validate_toml, validate_yaml


def xml_escape_text(s: str) -> str:
    s = str(s)
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _shrink_obj_for_output(obj: Dict[str, Any], max_rows: int, max_attrs: int, max_cell_chars: int) -> Dict[str, Any]:
    items = obj.get("items", [])
    if not isinstance(items, list):
        return {"items": []}

    shrunk_items = []
    for r in items[:max_rows]:
        if isinstance(r, dict):
            keys = list(r.keys())[:max_attrs]
            rr = {}
            for k in keys:
                v = r.get(k, "")
                rr[k] = clip(norm(v), max_cell_chars)
            shrunk_items.append(rr)
        else:
            shrunk_items.append({"value": clip(norm(r), max_cell_chars)})

    return {"items": shrunk_items}


def _rows_from_items_obj(obj: Dict[str, Any]) -> List[Dict[str, Any]]:
    items = obj.get("items", [])
    out: List[Dict[str, Any]] = []
    for r in items:
        if isinstance(r, dict):
            out.append(r)
        else:
            out.append({"value": str(r)})
    return out


def _sizing_plans():
    return [
        (MAX_ROWS_PER_SAMPLE, MAX_ATTRS, MAX_CELL_CHARS),
        (min(4, MAX_ROWS_PER_SAMPLE), min(5, MAX_ATTRS), min(160, MAX_CELL_CHARS)),
        (min(3, MAX_ROWS_PER_SAMPLE), min(4, MAX_ATTRS), min(120, MAX_CELL_CHARS)),
        (min(2, MAX_ROWS_PER_SAMPLE), min(3, MAX_ATTRS), min(90, MAX_CELL_CHARS)),
        (1, 2, min(70, MAX_CELL_CHARS)),
    ]


def safe_json_sized(obj: Dict[str, Any], max_chars: int) -> str:
    """Serialize to JSON and keep within max_chars by shrinking items if needed."""
    import orjson

    def dumps(x: Any) -> str:
        return orjson.dumps(x, option=orjson.OPT_SORT_KEYS).decode()

    try:
        s = dumps(obj)
        if len(s) <= max_chars:
            return s
    except Exception:
        return dumps({})

    if isinstance(obj, dict) and isinstance(obj.get("items"), list):
        for (mr, ma, mc) in _sizing_plans():
            shrunk = _shrink_obj_for_output(obj, mr, ma, mc)
            try:
                s2 = dumps(shrunk)
                if len(s2) <= max_chars:
                    return s2
            except Exception:
                continue
    return dumps({})


def rows_to_csv(rows: List[Dict[str, Any]]) -> str:
    """Basic CSV stringify; size control via get_safe_csv."""
    if not rows:
        # Minimal non-empty CSV with dummy header/value
        return "value\n\n"

    df = pd.DataFrame(rows)

    # If no columns, enforce a dummy column so CSV is non-empty.
    if df.shape[1] == 0:
        df = pd.DataFrame({"value": [""] * len(rows)})

    s = df.to_csv(index=False)
    if s is None or s.strip() == "":
        s = "value\n\n"
    return s


def rows_to_text(rows: List[Dict[str, Any]]) -> str:
    return "\n".join(" | ".join(f"{k}:{v}" for k, v in r.items() if v) for r in rows)


def rows_to_xml_input(rows: List[Dict[str, Any]]) -> str:
    xs = ["<items>"]
    for r in rows:
        xs.append("<item>")
        for k, v in r.items():
            kk = k if is_ascii_key(k) else "field"
            xs.append(f"<{kk}>{xml_escape_text(clip(v, 100))}</{kk}>")
        xs.append("</item>")
    xs.append("</items>")
    s = "\n".join(xs)
    if len(s) > MAX_OUTPUT_CHARS:
        return rows_to_xml_input(rows[:2])
    if not validate_xml(s):
        return "<items></items>"
    return s


def get_safe_csv(rows: List[Dict[str, Any]], max_chars: int) -> str:
    obj = {"items": rows}
    for mr, ma, mc in _sizing_plans():
        shrunk = _shrink_obj_for_output(obj, mr, ma, mc)
        s = rows_to_csv(_rows_from_items_obj(shrunk))
        if len(s) <= max_chars and validate_csv(s):
            return s
    return ""


def get_safe_xml_input(rows: List[Dict[str, Any]], max_chars: int) -> str:
    obj = {"items": rows}
    for mr, ma, mc in _sizing_plans():
        shrunk = _shrink_obj_for_output(obj, mr, ma, mc)
        s = rows_to_xml_input(_rows_from_items_obj(shrunk))
        if len(s) <= max_chars and validate_xml(s):
            return s
    return ""


def dict_to_yaml(obj: Any) -> str:
    return yaml.safe_dump(obj, allow_unicode=True, sort_keys=True)


def get_safe_structured_data(obj: Dict[str, Any], fmt: str, max_chars: int) -> str:
    for mr, ma, mc in _sizing_plans():
        shrunk = _shrink_obj_for_output(obj, mr, ma, mc)
        if fmt == "toml":
            s = dict_to_toml(shrunk)
            if len(s) <= max_chars and validate_toml(s):
                return s
        elif fmt == "yaml":
            s = dict_to_yaml(shrunk)
            if len(s) <= max_chars and validate_yaml(s):
                return s
        else:
            raise ValueError(f"Unsupported fmt: {fmt}")
    return ""


def dict_to_xml_sized(obj: Dict[str, Any], root_name: str = "root", max_chars: int = MAX_OUTPUT_CHARS) -> str:
    def sanitize_tag(k: str) -> str:
        k = (k or "").strip()
        if not is_ascii_key(k):
            return "field"
        if k.lower().startswith("xml"):
            return "field"
        return k

    def build(parent, x):
        if isinstance(x, dict):
            for k in sorted(x.keys()):
                tag = sanitize_tag(str(k))
                child = etree.SubElement(parent, tag)
                build(child, x[k])
        elif isinstance(x, list):
            for it in x:
                child = etree.SubElement(parent, "item")
                build(child, it)
        else:
            parent.text = xml_escape_text(clip(norm(x), MAX_CELL_CHARS))

    last_xml = ""
    for (mr, ma, mc) in _sizing_plans():
        o2 = _shrink_obj_for_output(obj, mr, ma, mc)
        root = etree.Element(root_name)
        build(root, o2)
        xml_bytes = etree.tostring(
            root, encoding="utf-8", pretty_print=False, xml_declaration=False
        )
        s = xml_bytes.decode("utf-8")
        last_xml = s
        if len(s) <= max_chars and validate_xml(s):
            return s

    if validate_xml(last_xml):
        return last_xml
    return "<root></root>"


def toml_quote(s: str) -> str:
    s = str(s).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{s}"'


def scalar_to_toml(v: Any) -> str:
    if v is None:
        return toml_quote("")
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        if v != v or v in (float("inf"), float("-inf")):
            return "0.0"
        return str(v)
    return toml_quote(clip(norm(v), MAX_CELL_CHARS))


def dict_to_toml(obj: Any) -> str:
    lines: List[str] = []

    def emit_table(prefix: List[str], d: Dict[str, Any]):
        scalars, nested_dicts, list_dicts, list_scalars = {}, {}, {}, {}

        for k, v in d.items():
            kk = sanitize_toml_key(str(k))
            if isinstance(v, dict):
                nested_dicts[kk] = v
            elif isinstance(v, list) and len(v) > 0 and all(isinstance(x, dict) for x in v):
                list_dicts[kk] = v
            elif isinstance(v, list):
                list_scalars[kk] = v
            else:
                scalars[kk] = v

        for k in sorted(scalars.keys()):
            lines.append(f"{k} = {scalar_to_toml(scalars[k])}")

        for k in sorted(list_scalars.keys()):
            arr = list_scalars[k][:20]
            arr_vals = ", ".join(
                scalar_to_toml(x) for x in arr if not isinstance(x, (dict, list))
            )
            lines.append(f"{k} = [{arr_vals}]")

        for k in sorted(nested_dicts.keys()):
            sect = prefix + [k]
            lines.append("")
            lines.append(f"[{'.'.join(sect)}]")
            emit_table(sect, nested_dicts[k])

        for k in sorted(list_dicts.keys()):
            sect = prefix + [k]
            for item in list_dicts[k][:10]:
                lines.append("")
                lines.append(f"[[{'.'.join(sect)}]]")
                emit_table(sect, item)

    if isinstance(obj, dict):
        emit_table([], obj)
    else:
        emit_table([], {"value": obj})

    s = "\n".join(lines).strip() + "\n"
    return s if len(s) <= MAX_OUTPUT_CHARS else s[: MAX_OUTPUT_CHARS - 1] + "\n"
