"""Quality validation and analysis beyond syntax.

Checks:
- Attribute consistency between prompt and assistant output (where applicable)
- Round-trip checks for toml_to_json, json_to_toml, yaml_to_toml, json_to_yaml
- Basic JSON schema sanity and duplicate id detection
- Distribution summaries (rows/attrs/cell lengths) from prompts/answers

Run:
  python -m StructEvalT.sft_builder.validate_quality
"""
from __future__ import annotations

import json
import os
import re
import statistics as stats
from typing import Any, Dict, Iterable, List, Optional, Tuple

import orjson
import pandas as pd
import tomllib
import yaml

from .config import OUT_DIR
from .validators import validate_csv, validate_toml, validate_yaml
from .serialization import dict_to_xml_sized
from lxml import etree


FILES = [
    "sft_core_c_tabular.jsonl",
    "sft_core_c_xml_in.jsonl",
    "sft_core_c_xml_out.jsonl",
    "sft_core_c_toml_out.jsonl",
    "sft_core_c_yaml_out_min.jsonl",
    "sft_core_g_gtfs.jsonl",
    "sft_pack_hard_mixed.jsonl",
]


def _load_jsonl(path: str):
    with open(path, "rb") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield orjson.loads(line)


def _extract_block(prompt: str, label: str) -> Optional[str]:
    # Finds `label:\n` and returns the rest of the block until end.
    m = re.search(rf"(?ms)\b{re.escape(label)}\s*\n(.*)$", prompt)
    if m:
        return m.group(1).strip()
    return None


def _extract_attributes(prompt: str) -> List[str]:
    """Extract attribute list after 'ATTRIBUTES:' even if newlines were collapsed.

    Accepts both patterns:
      ATTRIBUTES:\ncol1, col2, ...
      ATTRIBUTES: col1, col2, ...
    and stops at next section label like CSV:/JSON:/XML:/YAML:/TEXT:/TOML: or EoS.
    """
    if "ATTRIBUTES:" not in prompt:
        return []
    m = re.search(
        r"(?is)ATTRIBUTES:\s*(.*?)(?:\n\s*\n|\n(?:CSV|JSON|XML|YAML|TEXT|TOML)\s*:|(?:CSV|JSON|XML|YAML|TEXT|TOML)\s*:|$)",
        prompt,
    )
    if not m:
        return []
    raw = m.group(1).strip()
    # attributes are comma-separated; only the first line (if any)
    line = raw.splitlines()[0] if raw else ""
    attrs = [a.strip() for a in line.split(",") if a.strip()]
    return attrs


def _parse_json(s: str) -> Any:
    return orjson.loads(s)


def _parse_csv_to_df(s: str) -> pd.DataFrame:
    from io import StringIO

    return pd.read_csv(StringIO(s))


def _parse_yaml(s: str) -> Any:
    return yaml.safe_load(s)


def _parse_toml(s: str) -> Any:
    return tomllib.loads(s)


def _norm_dict(x: Any) -> Any:
    # Recursively sort keys for comparable equality
    if isinstance(x, dict):
        return {k: _norm_dict(x[k]) for k in sorted(x.keys())}
    if isinstance(x, list):
        return [_norm_dict(v) for v in x]
    return x


def _xml_to_obj(elem: etree._Element) -> Any:
    """Parse XML back to Python structures compatible with dict_to_xml_sized.

    - Elements with only text -> return text
    - Elements with children of mixed names -> dict of tag->value
    - Repeated tag names -> list
    - <item> children -> produce list
    """
    children = list(elem)
    if not children:
        text = (elem.text or "").strip()
        return text

    # Group by tag
    groups: Dict[str, List[etree._Element]] = {}
    for ch in children:
        groups.setdefault(ch.tag, []).append(ch)

    # Special case: list semantics via <item>
    if set(groups.keys()) == {"item"}:
        return [_xml_to_obj(c) for c in groups["item"]]

    out: Dict[str, Any] = {}
    for tag, elems in groups.items():
        if len(elems) == 1:
            out[tag] = _xml_to_obj(elems[0])
        else:
            out[tag] = [_xml_to_obj(e) for e in elems]
    return out


def main():
    # Aggregates
    duplicates: List[str] = []
    seen_ids: set = set()
    schema_errors: List[Dict[str, Any]] = []
    attr_issues: List[Dict[str, Any]] = []
    roundtrip_issues: List[Dict[str, Any]] = []

    # Distributions
    dist_attrs: List[int] = []
    dist_rows_prompt: List[int] = []
    dist_rows_answer: List[int] = []
    dist_cell_len: List[int] = []
    dist_ans_chars: List[int] = []

    for fn in FILES:
        path = os.path.join(OUT_DIR, fn)
        if not os.path.exists(path):
            continue
        for obj in _load_jsonl(path):
            # schema sanity
            sid = obj.get("id")
            if sid in seen_ids:
                duplicates.append(sid)
            else:
                seen_ids.add(sid)
            msgs = obj.get("messages")
            if not isinstance(msgs, list) or len(msgs) < 2:
                schema_errors.append({"file": fn, "id": sid, "why": "bad_messages"})
                continue
            if msgs[-1].get("role") != "assistant" or not isinstance(msgs[-1].get("content", ""), str):
                schema_errors.append({"file": fn, "id": sid, "why": "assistant_bad"})
                continue

            prompt = msgs[0].get("content", "")
            answer = msgs[-1].get("content", "")
            subcat = obj.get("subcategory", "")

            # attribute consistency where applicable
            attrs = _extract_attributes(prompt)
            if attrs:
                dist_attrs.append(len(attrs))

            try:
                if subcat in ("csv_to_json", "xml_to_json", "text_to_json", "text_to_yaml", "text_to_toml"):
                    if subcat.endswith("_to_json"):
                        ans = _parse_json(answer)
                        if isinstance(ans, list) and all(isinstance(x, dict) for x in ans) and attrs:
                            # Check all keys exist; compute non-empty ratio
                            empty_cnt = 0
                            for row in ans:
                                for k in attrs:
                                    if k not in row or (str(row.get(k) or "").strip() == ""):
                                        empty_cnt += 1
                            if empty_cnt > 0:
                                attr_issues.append({"file": fn, "id": sid, "why": "missing_or_empty_attrs", "count": empty_cnt})
                        # rows distribution
                        dist_rows_answer.append(len(ans) if isinstance(ans, list) else 0)
                    elif subcat.endswith("_to_yaml"):
                        y = _parse_yaml(answer)
                        # not enforcing attr equality strictly for YAML; syntax already validated
                elif subcat == "json_to_csv":
                    # prompt JSON vs answer CSV
                    prompt_json = _parse_json(_extract_block(prompt, "JSON:") or "{}")
                    df_csv = _parse_csv_to_df(answer)
                    if isinstance(prompt_json, list) and prompt_json:
                        keys = sorted({k for r in prompt_json if isinstance(r, dict) for k in r.keys()})
                        cols = list(df_csv.columns)
                        if not set(keys).issubset(set(cols)):
                            roundtrip_issues.append({"file": fn, "id": sid, "why": "csv_missing_cols", "expected": keys, "got": cols})
                        # row count check (allow equal only)
                        if len(df_csv) != len(prompt_json):
                            roundtrip_issues.append({"file": fn, "id": sid, "why": "csv_row_mismatch", "exp": len(prompt_json), "got": len(df_csv)})
                        dist_rows_prompt.append(len(prompt_json))
                        dist_rows_answer.append(len(df_csv))
                elif subcat == "toml_to_json":
                    # prompt TOML -> answer JSON strict equality
                    toml_s = _extract_block(prompt, "TOML:") or ""
                    j_ans = _parse_json(answer)
                    if toml_s.strip():
                        parsed = _parse_toml(toml_s)
                        if _norm_dict(parsed) != _norm_dict(j_ans):
                            roundtrip_issues.append({"file": fn, "id": sid, "why": "toml_to_json_roundtrip_mismatch"})
                elif subcat == "json_to_toml":
                    js = _extract_block(prompt, "JSON:") or ""
                    if js.strip():
                        j = _parse_json(js)
                        # parse assistant TOML and compare
                        if validate_toml(answer):
                            t = _parse_toml(answer)
                            if _norm_dict(t) != _norm_dict(j):
                                roundtrip_issues.append({"file": fn, "id": sid, "why": "json_to_toml_roundtrip_mismatch"})
                elif subcat == "yaml_to_toml":
                    yml = _extract_block(prompt, "YAML:") or ""
                    if yml.strip():
                        y = _parse_yaml(yml)
                        if validate_toml(answer):
                            t = _parse_toml(answer)
                            if _norm_dict(t) != _norm_dict(y):
                                roundtrip_issues.append({"file": fn, "id": sid, "why": "yaml_to_toml_roundtrip_mismatch"})
                elif subcat == "json_to_yaml":
                    js = _extract_block(prompt, "JSON:") or ""
                    if js.strip():
                        j = _parse_json(js)
                        y = _parse_yaml(answer)
                        if _norm_dict(j) != _norm_dict(y):
                            roundtrip_issues.append({"file": fn, "id": sid, "why": "json_to_yaml_roundtrip_mismatch"})
                # XML round-trip checks (json/yaml/csv -> xml). 'text_to_xml' is skipped.
                if subcat in ("json_to_xml", "yaml_to_xml", "csv_to_xml"):
                    # build reference object from prompt
                    ref_obj: Optional[Dict[str, Any]] = None
                    if subcat == "json_to_xml":
                        js = _extract_block(prompt, "JSON:") or ""
                        if js.strip():
                            ref = _parse_json(js)
                            ref_obj = ref if isinstance(ref, dict) else {"value": ref}
                    elif subcat == "yaml_to_xml":
                        yml = _extract_block(prompt, "YAML:") or ""
                        if yml.strip():
                            ref = _parse_yaml(yml)
                            ref_obj = ref if isinstance(ref, dict) else {"value": ref}
                    elif subcat == "csv_to_xml":
                        csv_s = _extract_block(prompt, "CSV:") or ""
                        if csv_s.strip():
                            try:
                                df = _parse_csv_to_df(csv_s)
                                ref_obj = {"items": df.fillna("").astype(str).to_dict(orient="records")}
                            except Exception:
                                ref_obj = None

                    if ref_obj is not None:
                        # parse assistant XML -> obj and compare normalized forms
                        try:
                            root = etree.fromstring(answer.encode("utf-8"))
                            got_obj = _xml_to_obj(root)
                            # normalize both sides under a common root
                            lhs = _norm_dict({"root": ref_obj})
                            rhs = _norm_dict({"root": got_obj})
                            if lhs != rhs:
                                roundtrip_issues.append({"file": fn, "id": sid, "why": f"{subcat}_xml_roundtrip_mismatch"})
                        except Exception:
                            roundtrip_issues.append({"file": fn, "id": sid, "why": f"{subcat}_xml_parse_or_compare_error"})

            except Exception as e:
                roundtrip_issues.append({"file": fn, "id": sid, "why": f"exception:{type(e).__name__}"})

            # crude cell length & answer length sampling
            dist_ans_chars.append(len(answer))
            # CSV cell length sampling
            if subcat == "json_to_csv":
                try:
                    df = _parse_csv_to_df(answer)
                    for val in df.astype(str).values.ravel().tolist()[:50]:
                        dist_cell_len.append(len(val))
                except Exception:
                    pass

    # Reporting
    print("Quality report:\n")
    print("- Duplicate ids:", len(duplicates))
    print("- Schema errors:", len(schema_errors))
    print("- Attribute issues:", len(attr_issues))
    print("- Round-trip issues:", len(roundtrip_issues))

    if attr_issues:
        print("\nSample attribute issues (up to 10):")
        for e in attr_issues[:10]:
            print(" ", e)
    if roundtrip_issues:
        print("\nSample round-trip issues (up to 10):")
        for e in roundtrip_issues[:10]:
            print(" ", e)

    def _summ(name: str, arr: List[int]):
        if not arr:
            print(f"- {name}: n=0")
            return
        arr_sorted = sorted(arr)
        n = len(arr_sorted)
        p10 = arr_sorted[int(0.10 * (n - 1))]
        p50 = arr_sorted[int(0.50 * (n - 1))]
        p90 = arr_sorted[int(0.90 * (n - 1))]
        mean = sum(arr_sorted) / n
        # std (population)
        var = sum((x - mean) ** 2 for x in arr_sorted) / n
        std = var ** 0.5
        print(f"- {name}: n={n} min={arr_sorted[0]} p10={p10} p50={p50} p90={p90} max={arr_sorted[-1]} mean={mean:.1f} std={std:.1f}")

    print("\nDistributions:")
    _summ("attributes_per_prompt", dist_attrs)
    _summ("rows_in_prompt", dist_rows_prompt)
    _summ("rows_in_answer", dist_rows_answer)
    _summ("cell_length_samples", dist_cell_len)
    _summ("answer_char_length", dist_ans_chars)


if __name__ == "__main__":
    main()
