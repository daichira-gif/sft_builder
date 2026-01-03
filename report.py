from typing import Any, Dict, List, Optional
import re

from .config import BUDGET, DESIRED_OUTPUT_COUNTS, FOCUS_MULTIPLIER


def detect_output_format_from_subcategory(subcat: str) -> Optional[str]:
    if not isinstance(subcat, str):
        return None
    m = re.search(r"_to_([a-z0-9]+)$", subcat.strip().lower())
    return m.group(1) if m else None


def detect_output_format_from_answer(ans: str) -> str:
    if not isinstance(ans, str):
        ans = str(ans)
    s = ans.strip()
    if not s:
        return "unknown"
    if (s.startswith("{") and s.endswith("}")) or (s.startswith("[") and s.endswith("]")):
        return "json"
    if s.startswith("<") and (">" in s) and ("</" in s or s.endswith("/>")):
        return "xml"
    if re.search(r"(?m)^\s*\[.+\]\s*$", s) or re.search(r"(?m)^\s*[\w\.\-]+\s*=\s*.+$", s):
        return "toml"
    if re.search(r"(?m)^\s*[-\w\"']+\s*:\s+.+$", s) and "\n" in s:
        return "yaml"
    if "\n" in s and ("," in s.splitlines()[0]):
        return "csv"
    return "unknown"


def detect_output_format(sample_obj: Dict[str, Any]) -> str:
    sub = sample_obj.get("subcategory", "")
    fmt = detect_output_format_from_subcategory(sub)
    if fmt:
        return fmt
    msgs = sample_obj.get("messages", [])
    ans = msgs[-1].get("content", "") if isinstance(msgs, list) and msgs else ""
    return detect_output_format_from_answer(ans)


def count_output_formats(outputs: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Dict[str, int]]:
    per_file: Dict[str, Dict[str, int]] = {}
    for fname, rows in outputs.items():
        d: Dict[str, int] = {}
        for r in rows:
            fmt = detect_output_format(r)
            d[fmt] = d.get(fmt, 0) + 1
        per_file[fname] = d
    return per_file


def summarize_fmt_counts(per_file_counts: Dict[str, Dict[str, int]]) -> Dict[str, int]:
    total = {"xml": 0, "toml": 0, "yaml": 0}
    for _, d in per_file_counts.items():
        for k in total:
            total[k] += d.get(k, 0)
    return total


def _normalize_desired_counts(desired: Dict[str, int], focus_mult: Dict[str, float]) -> Dict[str, float]:
    w = {}
    for k, v in desired.items():
        w[k] = float(v) * float(focus_mult.get(k, 1.0))
    s = sum(w.values())
    return {k: (w[k] / s if s > 0 else 0.0) for k in w}


def suggest_budget_from_output_mix(
    current_budget: Dict[str, int],
    per_file_counts: Dict[str, Dict[str, int]],
    desired_output_share: Dict[str, float],
    total_budget: Optional[int] = None,
) -> Dict[str, int]:
    if total_budget is None:
        total_budget = sum(current_budget.values())

    file_probs = {}
    support = {k: 0.0 for k in desired_output_share.keys()}

    for fname, counts in per_file_counts.items():
        n = sum(counts.values())
        if n == 0:
            continue
        probs = {k: counts.get(k, 0) / n for k in desired_output_share.keys()}
        file_probs[fname] = probs
        for k in support:
            support[k] += probs.get(k, 0)

    unsatisfied = [k for k, v in support.items() if v <= 0 and desired_output_share.get(k, 0) > 0]
    if unsatisfied:
        return dict(current_budget)

    scores = {}
    for fname, probs in file_probs.items():
        score = 0.0
        for fmt, tgt in desired_output_share.items():
            score += probs.get(fmt, 0.0) * tgt
        scores[fname] = score

    eps = 1e-9
    ssum = sum(v + eps for v in scores.values())
    alloc = {f: int(round(total_budget * ((scores.get(f, 0.0) + eps) / ssum))) for f in current_budget.keys()}

    drift = total_budget - sum(alloc.values())
    if drift != 0 and scores:
        best = max(scores.keys(), key=lambda k: scores[k])
        alloc[best] = max(0, alloc.get(best, 0) + drift)
    return alloc


def print_report(outputs):
    per_file_counts = count_output_formats(outputs)
    totals = summarize_fmt_counts(per_file_counts)
    print("\n=========================")
    print("Output-format counts (per file)")
    print("=========================")
    for fname, d in per_file_counts.items():
        total = sum(d.values())
        print(f"- {fname}: total={total}  counts={d}")
    print("\n[XML/TOML/YAML totals]", totals)

    desired_share = _normalize_desired_counts(DESIRED_OUTPUT_COUNTS, FOCUS_MULTIPLIER)
    suggested = suggest_budget_from_output_mix(
        current_budget=BUDGET,
        per_file_counts=per_file_counts,
        desired_output_share=desired_share,
        total_budget=sum(BUDGET.values()),
    )
    print("\n=========================")
    print("AUTO-BUDGET suggestion (based on OUTPUT formats)")
    print("=========================")
    print("Desired share:", desired_share)
    print("Current BUDGET:", BUDGET)
    print("Suggested BUDGET:", suggested)

