"""Validate generated JSONL packs for structural and syntax correctness.

Usage:
  python -m sft_builder.validate_outputs

It reads files under OUT_DIR (config.py) and validates each assistant output
against the intended subcategory/format.
"""
import os
from typing import Dict, List, Tuple

import orjson

from .config import OUT_DIR
from .report import detect_output_format
from .validators import validate_csv, validate_toml, validate_xml, validate_yaml


def _load_jsonl(path: str):
    with open(path, "rb") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield orjson.loads(line)
            except Exception as e:
                yield {"__load_error__": str(e), "__raw__": line.decode(errors="ignore")}


def _expect_for_file(fname: str, subcat: str) -> str:
    # Return one of: json, csv, xml, toml, yaml
    base = os.path.basename(fname)
    if base == "sft_core_c_tabular.jsonl":
        if subcat.endswith("json_to_csv"):
            return "csv"
        return "json"
    if base == "sft_core_c_xml_in.jsonl":
        return "json"
    if base == "sft_core_c_xml_out.jsonl":
        return "xml"
    if base == "sft_core_c_toml_out.jsonl":
        if subcat.endswith("toml_to_json"):
            return "json"
        return "toml"
    if base == "sft_core_c_yaml_out_min.jsonl":
        return "yaml"
    if base == "sft_core_g_gtfs.jsonl":
        return "json"
    if base == "sft_pack_hard_mixed.jsonl":
        return "json"
    return "unknown"


def _validate_answer(fmt: str, answer: str) -> Tuple[bool, str]:
    if not isinstance(answer, str) or not answer.strip():
        return False, "empty"
    try:
        if fmt == "json":
            orjson.loads(answer)
            return True, "ok"
        if fmt == "csv":
            return (validate_csv(answer), "ok" if validate_csv(answer) else "csv_parse_fail")
        if fmt == "xml":
            return (validate_xml(answer), "ok" if validate_xml(answer) else "xml_invalid")
        if fmt == "toml":
            return (validate_toml(answer), "ok" if validate_toml(answer) else "toml_invalid")
        if fmt == "yaml":
            return (validate_yaml(answer), "ok" if validate_yaml(answer) else "yaml_invalid")
        return False, f"unsupported_fmt:{fmt}"
    except Exception as e:
        return False, f"exception:{type(e).__name__}"


def main():
    files = [
        "sft_core_c_tabular.jsonl",
        "sft_core_c_xml_in.jsonl",
        "sft_core_c_xml_out.jsonl",
        "sft_core_c_toml_out.jsonl",
        "sft_core_c_yaml_out_min.jsonl",
        "sft_core_g_gtfs.jsonl",
        "sft_pack_hard_mixed.jsonl",
    ]

    errors: List[Dict] = []
    totals: Dict[str, int] = {f: 0 for f in files}
    valids: Dict[str, int] = {f: 0 for f in files}

    for fn in files:
        path = os.path.join(OUT_DIR, fn)
        if not os.path.exists(path):
            print("[skip] not found:", path)
            continue
        for obj in _load_jsonl(path):
            totals[fn] += 1
            if "__load_error__" in obj:
                errors.append({"file": fn, "id": None, "reason": "jsonl_load_error", "detail": obj["__load_error__"]})
                continue

            msgs = obj.get("messages", [])
            if not isinstance(msgs, list) or len(msgs) < 2:
                errors.append({"file": fn, "id": obj.get("id"), "reason": "bad_messages"})
                continue
            if msgs[-1].get("role") != "assistant":
                errors.append({"file": fn, "id": obj.get("id"), "reason": "last_not_assistant"})
                continue

            ans = msgs[-1].get("content", "")
            sub = obj.get("subcategory", "")
            expect = _expect_for_file(fn, sub)

            ok, why = _validate_answer(expect, ans)
            if not ok:
                errors.append({"file": fn, "id": obj.get("id"), "subcategory": sub, "expect": expect, "reason": why})
            else:
                valids[fn] += 1

    print("\nValidation summary:")
    for fn in files:
        print(f"- {fn}: {valids[fn]}/{totals[fn]} valid")
    if errors:
        print("\nErrors (up to 50):")
        for e in errors[:50]:
            print(" ", e)
    else:
        print("No structural/syntax errors detected.")


if __name__ == "__main__":
    main()

