import os
import random
from typing import Any, Dict, Iterable, List, Optional, Tuple

import orjson

from .config import (
    BUDGET,
    DEBUG_DIR,
    MAX_ATTRS,
    MAX_INPUT_CHARS,
    MAX_OUTPUT_CHARS,
    OUT_DIR,
    XML_FAIL_LOG,
    TOML_FAIL_LOG,
    DIVERSIFY_ENABLE,
    DIVERSIFY_ROW_TRIM_ENABLE,
    DIVERSIFY_HARD_MIXED_ENABLE,
    PROB_EMPTY,
    PROB_SUFFIX,
    PROB_PREFIX,
    PROB_CASE,
    ATTR_LENGTH_BIAS_PROB,
    TABULAR_JSON_TO_CSV_PROB,
    XML_OUT_PROBS,
    TOML_OUT_PROBS,
    YAML_OUT_PROBS,
    EXTRACT_MIN_FILLED,
)
from .p0_guard import P0Guard

# In-run uniqueness tracking: file name -> set of seen sample ids
_SEEN_IDS: Dict[str, set] = {}
from .prompts import (
    prompt_csv_to_json,
    prompt_json_to_csv,
    prompt_xml_to_json,
    prompt_text_to_json,
    prompt_json_to_xml,
    prompt_yaml_to_xml,
    prompt_csv_to_xml,
    prompt_text_to_xml,
    prompt_json_to_toml,
    prompt_yaml_to_toml,
    prompt_text_to_toml,
    prompt_toml_to_json,
    prompt_xml_to_yaml,
    prompt_csv_to_yaml,
    prompt_text_to_yaml,
    prompt_json_to_yaml,
)
from .serialization import (
    dict_to_toml,
    dict_to_xml_sized,
    dict_to_yaml,
    get_safe_csv,
    get_safe_structured_data,
    get_safe_xml_input,
    safe_json_sized,
    rows_to_csv,
    rows_to_text,
)
from .utils import now_ms, sha1, append_jsonl, norm
from .validators import validate_xml, validate_toml, validate_yaml


def sample(cat: str, sub: str, task: str, prompt: str, answer: str, seed: Any, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if answer is None or (isinstance(answer, str) and len(answer) == 0):
        raise ValueError("sample(): empty answer is not allowed")
    obj = {
        "id": sha1(str(prompt) + str(answer))[:12],
        "category": cat,
        "subcategory": sub,
        "task": task,
        "seed": seed,
        "messages": [
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": answer},
        ],
    }
    if extra:
        obj.update(extra)
    return obj


def append_with_p0(outputs: Dict[str, List[Dict[str, Any]]], fname: str, s_obj: Dict[str, Any], meta: Dict[str, Any], p0: P0Guard) -> bool:
    keep, _ = p0.reject_if_0valid(s_obj["messages"], sample_meta=meta)
    if not keep:
        return False
    # Generation-time uniqueness: skip if this id already seen for the target file
    rid = s_obj.get("id")
    if rid is None:
        # Fallback to hash of messages content
        try:
            import hashlib
            rid = hashlib.sha1(orjson.dumps(s_obj.get("messages", []))).hexdigest()
        except Exception:
            rid = None
    seen = _SEEN_IDS.setdefault(fname, set())
    if rid is not None and rid in seen:
        return False
    if rid is not None:
        seen.add(rid)
    outputs[fname].append(s_obj)
    return True


def _random_trim_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not rows:
        return rows
    if not DIVERSIFY_ENABLE or not DIVERSIFY_ROW_TRIM_ENABLE:
        return rows
    n = random.randint(1, max(1, len(rows)))
    return rows[:n]


def _filter_rows_min_filled(rows: List[Dict[str, Any]], attrs: List[str], min_filled: int) -> List[Dict[str, Any]]:
    if not rows or not attrs:
        return rows or []
    out: List[Dict[str, Any]] = []
    for r in rows:
        filled = sum(1 for a in attrs if str(r.get(a, "")).strip() != "")
        if filled >= max(0, min_filled):
            out.append(r)
    return out

def _diversify_values(
    rows: List[Dict[str, Any]], *, protect_keys: Optional[List[str]] = None, allow_empty: bool = True
) -> List[Dict[str, Any]]:
    if not rows or not DIVERSIFY_ENABLE:
        return rows
    protect = set(protect_keys or [])
    out: List[Dict[str, Any]] = []
    for r in rows:
        rr: Dict[str, Any] = {}
        for k, v in r.items():
            s = str(v)
            p = random.random()
            if p < PROB_EMPTY and allow_empty and (k not in protect):
                s = ""
            elif p < PROB_EMPTY + PROB_SUFFIX:
                s = s + " - v2"
            elif p < PROB_EMPTY + PROB_SUFFIX + PROB_PREFIX:
                s = "~" + s
            elif p < PROB_EMPTY + PROB_SUFFIX + PROB_PREFIX + PROB_CASE:
                s = s.upper() if random.random() < 0.5 else s.title()
            rr[k] = s
        out.append(rr)
    return out


def _pick_attrs(cols: List[str], rows: List[Dict[str, Any]]) -> List[str]:
    if not cols:
        return []
    limit = min(len(cols), MAX_ATTRS)
    k_min = 2 if limit >= 2 else 1
    k = random.randint(k_min, limit)

    bias = random.random()
    if (not DIVERSIFY_ENABLE) or (bias > ATTR_LENGTH_BIAS_PROB):
        return random.sample(cols, k)

    lens = []
    for c in cols:
        vals = [len(str(r.get(c, ""))) for r in rows]
        m = sum(vals) / len(vals) if vals else 0.0
        lens.append((c, m))
    if bias < ATTR_LENGTH_BIAS_PROB / 2:
        order = [c for c, _ in sorted(lens, key=lambda x: -x[1])]
    else:
        order = [c for c, _ in sorted(lens, key=lambda x: x[1])]
    chosen = order[:k]
    random.shuffle(chosen)
    return chosen


def build_core_tabular(outputs, take_rows, p0: P0Guard):
    target = BUDGET["sft_core_c_tabular.jsonl"]
    while len(outputs["sft_core_c_tabular.jsonl"]) < target:
        (rows, cols), seed = take_rows(random.choice(["shopify", "openfoodfacts"]))
        rows = _random_trim_rows(rows)
        cols = list(cols) if cols else []
        if not cols:
            cols = ["value"]
            rows = [{"value": norm(r) if not isinstance(r, dict) else ""} for r in (rows or [{} for _ in range(1)])]

        attrs = _pick_attrs(cols, rows) or ["value"]

        def _ensure_rows_have_keys(rows_in: List[Dict[str, Any]], keys: List[str]) -> List[Dict[str, Any]]:
            keys = [k for k in (keys or []) if isinstance(k, str) and k.strip()]
            if not keys:
                keys = ["value"]
            out = []
            for r in (rows_in or []):
                if not isinstance(r, dict) or len(r) == 0:
                    out.append({keys[0]: ""})
                    continue
                rr = dict(r)
                if all((k not in rr) for k in keys):
                    rr[keys[0]] = ""
                out.append(rr)
            if not out:
                out = [{keys[0]: ""}]
            return out

        if random.random() < TABULAR_JSON_TO_CSV_PROB:
            # JSON -> CSV (transform)
            rows = _diversify_values(rows)
            rows_for_io = _ensure_rows_have_keys(rows, attrs)
            js_obj = {"items": [{a: r.get(a, "") for a in attrs} for r in rows_for_io]}
            js = safe_json_sized(js_obj, MAX_INPUT_CHARS)
            p = prompt_json_to_csv(js)
            rows_for_csv = [{a: r.get(a, "") for a in attrs} for r in rows_for_io]
            ans = get_safe_csv(rows_for_csv, MAX_OUTPUT_CHARS)
            if not ans:
                continue
            s = sample("C2", "json_to_csv", "transform", p, ans, seed)
        else:
            # CSV -> JSON (extract)
            rows = _diversify_values(rows, protect_keys=attrs, allow_empty=False)
            # 抽出系の品質ゲート（部分的空値許容: SFT_EXTRACT_MIN_FILLED）
            rows_for_in = _filter_rows_min_filled(rows, attrs, min_filled=EXTRACT_MIN_FILLED)
            if not rows_for_in:
                continue
            p = prompt_csv_to_json(get_safe_csv(rows_for_in, MAX_INPUT_CHARS), attrs)
            ans_obj = [{a: r.get(a, "") for a in attrs} for r in rows_for_in]
            ans = orjson.dumps(ans_obj).decode()
            s = sample("C1", "csv_to_json", "extract", p, ans, seed)

        append_with_p0(outputs, "sft_core_c_tabular.jsonl", s, meta={"pack": "tabular", "seed": seed, "subcategory": s["subcategory"]}, p0=p0)


def build_core_xml_in(outputs, take_rows, p0: P0Guard):
    target = BUDGET["sft_core_c_xml_in.jsonl"]
    while len(outputs["sft_core_c_xml_in.jsonl"]) < target:
        (rows, cols), seed = take_rows("openfoodfacts")
        rows = _random_trim_rows(rows)
        attrs = _pick_attrs(cols, rows)
        rows = _diversify_values(rows, protect_keys=attrs, allow_empty=False)
        rows = _filter_rows_min_filled(rows, attrs, min_filled=EXTRACT_MIN_FILLED)
        xml_in = get_safe_xml_input(rows, MAX_INPUT_CHARS)
        if not xml_in:
            continue
        p = prompt_xml_to_json(xml_in, attrs)
        ans = orjson.dumps([{a: r.get(a, "") for a in attrs} for r in rows]).decode()
        s = sample("C3", "xml_to_json", "extract", p, ans, seed)
        append_with_p0(outputs, "sft_core_c_xml_in.jsonl", s, meta={"pack": "xml_in", "seed": seed, "subcategory": s["subcategory"]}, p0=p0)


def build_core_gtfs(outputs, take_rows, p0: P0Guard):
    target = BUDGET["sft_core_g_gtfs.jsonl"]
    while len(outputs["sft_core_g_gtfs.jsonl"]) < target:
        (rows, cols), seed = take_rows("gtfs")
        rows = _random_trim_rows(rows)
        attrs = _pick_attrs(cols, rows)
        rows = _diversify_values(rows, protect_keys=attrs, allow_empty=False)
        rows = _filter_rows_min_filled(rows, attrs, min_filled=EXTRACT_MIN_FILLED)
        if not rows:
            continue
        p = prompt_text_to_json(rows_to_text(rows), attrs)
        ans = orjson.dumps([{a: r.get(a, "") for a in attrs} for r in rows]).decode()
        s = sample("G", "text_to_json", "extract", p, ans, seed)
        append_with_p0(outputs, "sft_core_g_gtfs.jsonl", s, meta={"pack": "gtfs", "seed": seed, "subcategory": s["subcategory"]}, p0=p0)


def build_pack_hard_mixed(outputs, take_rows, p0: P0Guard):
    target = BUDGET["sft_pack_hard_mixed.jsonl"]
    while len(outputs["sft_pack_hard_mixed.jsonl"]) < target:
        (g_rows, _), g_seed = take_rows("gtfs")
        (p_rows, _), p_seed = take_rows("shopify")
        # Basic diversification: shuffle and trim rows lightly
        if DIVERSIFY_HARD_MIXED_ENABLE and DIVERSIFY_ENABLE:
            random.shuffle(g_rows)
            random.shuffle(p_rows)
            # random subset of products to display in prompt
            p_rows = _random_trim_rows(p_rows)

        # Constraint: pick 1-2 keys from GTFS head row, if available
        head = g_rows[0] if g_rows else {}
        keys = list(head.keys())
        if not keys:
            keys = ["route_id"]
        k = 1 if len(keys) == 1 else random.randint(1, min(2, len(keys)))
        sel = random.sample(keys, k)
        constraint = {kk: head.get(kk, "") for kk in sel}

        # Prompt
        p = (
            "You are a data extraction assistant.\n"
            "Filter PRODUCTS under the given constraint and output a JSON list.\n"
            "Return ONLY JSON.\n\n"
            f"CONSTRAINT:\n{orjson.dumps(constraint).decode()}\n\n"
            f"TRANSIT:\n{rows_to_text(g_rows)}\n\n"
            f"PRODUCTS:\n{rows_to_text(p_rows)}\n\n"
            "RULE:\n- If no products match, return [].\n- Keep the original order.\n"
        )

        # Answer: return a random subset (could be empty), maintaining order
        if not p_rows or not any(str(v).strip() for v in constraint.values()):
            chosen: List[Dict[str, Any]] = []
        else:
            nmax = len(p_rows)
            nsel = random.randint(0, nmax)
            chosen = p_rows[:nsel]
        ans = orjson.dumps(chosen).decode()
        seed = f"{g_seed}+{p_seed}"
        s = sample("GC", "constraint_to_json", "filter", p, ans, seed)
        append_with_p0(outputs, "sft_pack_hard_mixed.jsonl", s, meta={"pack": "hard_mixed", "seed": seed, "subcategory": s["subcategory"]}, p0=p0)


def _dump_xml_failure(meta: Dict[str, Any]) -> None:
    append_jsonl(XML_FAIL_LOG, meta)


def _dump_toml_failure(meta: Dict[str, Any]) -> None:
    append_jsonl(TOML_FAIL_LOG, meta)


def build_core_xml_out(outputs, take_rows, p0: P0Guard):
    target = BUDGET["sft_core_c_xml_out.jsonl"]
    attempts = 0
    failures = 0
    while len(outputs["sft_core_c_xml_out.jsonl"]) < target:
        attempts += 1
        (rows, cols), seed = take_rows(random.choice(["shopify", "openfoodfacts", "gtfs"]))
        rows = _random_trim_rows(rows)
        rows = _diversify_values(rows)
        attrs = _pick_attrs(cols, rows)
        obj = {"items": [{a: r.get(a, "") for a in attrs} for r in rows]}
        r = random.random()
        cut_json = XML_OUT_PROBS.get("json", 0.0)
        cut_yaml = cut_json + XML_OUT_PROBS.get("yaml", 0.0)
        cut_csv  = cut_yaml + XML_OUT_PROBS.get("csv", 0.0)

        if r < cut_json:
            js = safe_json_sized(obj, MAX_INPUT_CHARS)
            p = prompt_json_to_xml(js)
            ans = dict_to_xml_sized(obj, root_name="root")
            sub, task = "json_to_xml", "transform"
        elif r < cut_yaml:
            yml = get_safe_structured_data(obj, "yaml", MAX_INPUT_CHARS)
            if not yml:
                failures += 1
                continue
            p = prompt_yaml_to_xml(yml)
            ans = dict_to_xml_sized(obj, root_name="root")
            sub, task = "yaml_to_xml", "transform"
        elif r < cut_csv:
            csv_in = get_safe_csv(obj["items"], MAX_INPUT_CHARS)
            if not csv_in:
                failures += 1
                continue
            p = prompt_csv_to_xml(csv_in)
            ans = dict_to_xml_sized(obj, root_name="root")
            sub, task = "csv_to_xml", "transform"
        else:
            text_in = rows_to_text(obj["items"])
            p = prompt_text_to_xml(text_in, attrs)
            ans = dict_to_xml_sized(obj, root_name="root")
            sub, task = "text_to_xml", "extract"

        if not validate_xml(ans) or len(ans) > MAX_OUTPUT_CHARS:
            failures += 1
            _dump_xml_failure(
                {
                    "ts_ms": now_ms(),
                    "pack": "xml_out",
                    "seed": seed,
                    "subcategory": sub,
                    "attempt": attempts,
                    "len_ans": len(ans) if isinstance(ans, str) else -1,
                    "ans_tail": (ans[-200:] if isinstance(ans, str) else ""),
                    "attrs_n": len(attrs),
                    "rows_n": len(rows),
                }
            )
            continue

        s = sample("C_XML", sub, task, p, ans, seed)
        append_with_p0(outputs, "sft_core_c_xml_out.jsonl", s, meta={"pack": "xml_out", "seed": seed, "subcategory": sub}, p0=p0)


def build_core_toml_out(outputs, take_rows, p0: P0Guard):
    target = BUDGET["sft_core_c_toml_out.jsonl"]
    attempts = 0
    failures = 0
    while len(outputs["sft_core_c_toml_out.jsonl"]) < target:
        attempts += 1
        (rows, cols), seed = take_rows(random.choice(["shopify", "openfoodfacts", "gtfs"]))
        rows = _random_trim_rows(rows)
        rows = _diversify_values(rows)
        attrs = _pick_attrs(cols, rows)
        obj = {"items": [{a: r.get(a, "") for a in attrs} for r in rows]}
        r = random.random()
        cut_json = TOML_OUT_PROBS.get("json", 0.0)
        cut_yaml = cut_json + TOML_OUT_PROBS.get("yaml", 0.0)
        cut_text = cut_yaml + TOML_OUT_PROBS.get("text", 0.0)

        if r < cut_json:
            js = safe_json_sized(obj, MAX_INPUT_CHARS)
            ans = dict_to_toml(obj)
            p = prompt_json_to_toml(js)
            sub, task = "json_to_toml", "transform"

            if (not validate_toml(ans)) or (len(ans) > MAX_OUTPUT_CHARS):
                failures += 1
                _dump_toml_failure({"ts_ms": now_ms(), "pack": "toml_out", "seed": seed, "subcategory": sub, "attempt": attempts, "len_ans": len(ans)})
                continue

            s = sample("C_TOML", sub, task, p, ans, seed)
            append_with_p0(outputs, "sft_core_c_toml_out.jsonl", s, meta={"pack": "toml_out", "seed": seed, "subcategory": sub}, p0=p0)

        elif r < cut_yaml:
            yml = dict_to_yaml(obj)
            ans = dict_to_toml(obj)
            p = prompt_yaml_to_toml(yml)
            sub, task = "yaml_to_toml", "transform"

            if (not validate_toml(ans)) or (len(ans) > MAX_OUTPUT_CHARS):
                failures += 1
                _dump_toml_failure({"ts_ms": now_ms(), "pack": "toml_out", "seed": seed, "subcategory": sub, "attempt": attempts, "len_ans": len(ans)})
                continue

            s = sample("C_TOML", sub, task, p, ans, seed)
            append_with_p0(outputs, "sft_core_c_toml_out.jsonl", s, meta={"pack": "toml_out", "seed": seed, "subcategory": sub}, p0=p0)

        elif r < cut_text:
            text_in = rows_to_text(obj["items"])
            ans = dict_to_toml(obj)
            p = prompt_text_to_toml(text_in, attrs)
            sub, task = "text_to_toml", "extract"

            if (not validate_toml(ans)) or (len(ans) > MAX_OUTPUT_CHARS):
                failures += 1
                _dump_toml_failure({"ts_ms": now_ms(), "pack": "toml_out", "seed": seed, "subcategory": sub, "attempt": attempts, "len_ans": len(ans)})
                continue

            s = sample("C_TOML", sub, task, p, ans, seed)
            append_with_p0(outputs, "sft_core_c_toml_out.jsonl", s, meta={"pack": "toml_out", "seed": seed, "subcategory": sub}, p0=p0)

        else:
            toml_s = get_safe_structured_data(obj, "toml", MAX_INPUT_CHARS)
            if not toml_s:
                failures += 1
                _dump_toml_failure({"ts_ms": now_ms(), "pack": "toml_out", "seed": seed, "subcategory": "toml_to_json", "attempt": attempts, "reason": "toml_gen_or_size_failed"})
                continue

            p = prompt_toml_to_json(toml_s)
            # defer parse to caller if needed; here we return TOML string as prompt and JSON-ified parsed answer
            try:
                import tomllib  # Python 3.11+
            except Exception:
                import tomli as tomllib  # Python 3.10 fallback

            parsed = tomllib.loads(toml_s)
            ans = orjson.dumps(parsed).decode()
            sub, task = "toml_to_json", "transform"

            s = sample("C_TOML", sub, task, p, ans, seed)
            append_with_p0(outputs, "sft_core_c_toml_out.jsonl", s, meta={"pack": "toml_out", "seed": seed, "subcategory": sub}, p0=p0)


def build_core_yaml_out_min(outputs, take_rows, p0: P0Guard):
    target = BUDGET["sft_core_c_yaml_out_min.jsonl"]
    attempts = 0
    failures = 0
    while len(outputs["sft_core_c_yaml_out_min.jsonl"]) < target:
        attempts += 1
        (rows, cols), seed = take_rows(random.choice(["shopify", "openfoodfacts", "gtfs"]))
        rows = _random_trim_rows(rows)
        rows = _diversify_values(rows)
        attrs = _pick_attrs(cols, rows)
        obj = {"items": [{a: r.get(a, "") for a in attrs} for r in rows]}

        r = random.random()
        cut_xml = YAML_OUT_PROBS.get("xml", 0.0)
        cut_csv = cut_xml + YAML_OUT_PROBS.get("csv", 0.0)
        cut_text = cut_csv + YAML_OUT_PROBS.get("text", 0.0)
        if r < cut_xml:
            xml_in = dict_to_xml_sized(obj, root_name="root", max_chars=MAX_INPUT_CHARS)
            p = prompt_xml_to_yaml(xml_in)
            ans = get_safe_structured_data(obj, "yaml", MAX_OUTPUT_CHARS)
            sub, task = "xml_to_yaml", "transform"
        elif r < cut_csv:
            csv_in = get_safe_csv(obj["items"], MAX_INPUT_CHARS)
            if not csv_in:
                continue
            p = prompt_csv_to_yaml(csv_in)
            ans = get_safe_structured_data(obj, "yaml", MAX_OUTPUT_CHARS)
            sub, task = "csv_to_yaml", "transform"
        elif r < cut_text:
            text_in = rows_to_text(obj["items"])
            p = prompt_text_to_yaml(text_in, attrs)
            ans = get_safe_structured_data(obj, "yaml", MAX_OUTPUT_CHARS)
            sub, task = "text_to_yaml", "extract"
        else:
            js = safe_json_sized(obj, MAX_INPUT_CHARS)
            p = prompt_json_to_yaml(js)
            ans = get_safe_structured_data(obj, "yaml", MAX_OUTPUT_CHARS)
            sub, task = "json_to_yaml", "transform"

        if (not ans) or (not validate_yaml(ans)) or (len(ans) > MAX_OUTPUT_CHARS):
            failures += 1
            continue

        s = sample("C_YAML", sub, task, p, ans, seed)
        append_with_p0(outputs, "sft_core_c_yaml_out_min.jsonl", s, meta={"pack": "yaml_out_min", "seed": seed, "subcategory": sub}, p0=p0)


def make_outputs_dict():
    return {k: [] for k in BUDGET}
