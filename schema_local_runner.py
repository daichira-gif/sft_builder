"""Local runner for schema-driven packs only.

Runs the new TEXT+SCHEMA generation builders with tiny budgets using
synthetic rows, no network, and P0 guard disabled.
"""
import random
from typing import Any, Dict, Iterable, List, Tuple

from .builders import (
    build_core_text_to_json_schema,
    build_core_text_to_json_schema_nested,
    build_core_text_to_yaml_schema,
    build_core_text_to_toml_schema,
    make_outputs_dict,
)
from .config import MAX_ROWS_PER_SAMPLE, SEED
from . import config as cfg
from .p0_guard import P0Guard
from .report import print_report
from .write_outputs import write_outputs


def _synthetic_rows() -> Iterable[Tuple[List[Dict[str, str]], List[str]]]:
    rows: List[Dict[str, str]] = []
    cols = ["title", "vendor", "product_type", "route_id", "route_short_name"]
    for i in range(MAX_ROWS_PER_SAMPLE):
        rows.append(
            {
                "title": f"Product {i}",
                "vendor": "Acme",
                "product_type": "Widget",
                "route_id": f"R{i}",
                "route_short_name": f"S{i}",
            }
        )
    yield rows, cols
    while True:
        yield rows, cols


def main():
    random.seed(SEED)
    # Tiny budgets for schema-only dry-run
    small = {
        "sft_core_c_text_to_json_schema.jsonl": 3,
        "sft_core_c_text_to_json_schema_nested.jsonl": 3,
        "sft_core_c_text_to_yaml_schema.jsonl": 2,
        "sft_core_c_text_to_toml_schema.jsonl": 2,
    }
    cfg.BUDGET.update({k: 0 for k in cfg.BUDGET})
    cfg.BUDGET.update(small)

    it = _synthetic_rows()

    def take_rows(src: str):
        rows, cols = next(it)
        return (rows, cols), src

    outputs = make_outputs_dict()
    p0 = P0Guard(disabled=True)

    build_core_text_to_json_schema(outputs, take_rows, p0)
    build_core_text_to_json_schema_nested(outputs, take_rows, p0)
    build_core_text_to_yaml_schema(outputs, take_rows, p0)
    build_core_text_to_toml_schema(outputs, take_rows, p0)

    print_report(outputs)
    write_outputs(outputs)


if __name__ == "__main__":
    main()

