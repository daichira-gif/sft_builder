import random
from typing import Dict, Iterable, List, Tuple

from .builders import (
    build_core_gtfs,
    build_core_tabular,
    build_core_toml_out,
    build_core_xml_in,
    build_core_xml_out,
    build_core_yaml_out_min,
    build_pack_hard_mixed,
    build_core_text_to_json_schema,
    build_core_text_to_json_schema_nested,
    build_core_text_to_yaml_schema,
    build_core_text_to_toml_schema,
    make_outputs_dict,
)
from .config import MAX_ROWS_PER_SAMPLE, SEED
from . import config as cfg
from ..p0_guard import P0Guard
from ..report import print_report
from ..write_outputs import write_outputs


def _synthetic_rows() -> Iterable[Tuple[List[Dict[str, str]], List[str]]]:
    rows: List[Dict[str, str]] = []
    cols = ["title", "vendor", "product_type", "route_id", "route_short_name", "tags"]
    for i in range(MAX_ROWS_PER_SAMPLE):
        rows.append(
            {
                "title": f"Product {i}",
                "vendor": "Acme",
                "product_type": "Widget",
                "route_id": f"R{i}",
                "route_short_name": f"S{i}",
                "tags": "alpha,beta",
            }
        )
    yield rows, cols
    while True:
        yield rows, cols


def main():
    random.seed(SEED)

    # Downscale budgets for local dry-run
    small = {
        "sft_core_c_tabular.jsonl": 20,
        "sft_core_c_xml_in.jsonl": 10,
        "sft_core_c_xml_out.jsonl": 15,
        "sft_core_c_toml_out.jsonl": 12,
        "sft_core_c_yaml_out_min.jsonl": 8,
        "sft_core_g_gtfs.jsonl": 10,
        "sft_pack_hard_mixed.jsonl": 10,
        "sft_core_c_text_to_json_schema.jsonl": 10,
        "sft_core_c_text_to_json_schema_nested.jsonl": 10,
        "sft_core_c_text_to_yaml_schema.jsonl": 8,
        "sft_core_c_text_to_toml_schema.jsonl": 8,
    }
    cfg.BUDGET.update(small)

    it = _synthetic_rows()

    def take_rows(src: str):
        rows, cols = next(it)
        return (rows, cols), src

    outputs = make_outputs_dict()
    p0 = P0Guard(disabled=True)

    build_core_tabular(outputs, take_rows, p0)
    build_core_xml_in(outputs, take_rows, p0)
    build_core_gtfs(outputs, take_rows, p0)

    build_core_text_to_json_schema(outputs, take_rows, p0)
    build_core_text_to_json_schema_nested(outputs, take_rows, p0)
    build_core_text_to_yaml_schema(outputs, take_rows, p0)
    build_core_text_to_toml_schema(outputs, take_rows, p0)

    build_pack_hard_mixed(outputs, take_rows, p0)
    build_core_xml_out(outputs, take_rows, p0)
    build_core_toml_out(outputs, take_rows, p0)
    build_core_yaml_out_min(outputs, take_rows, p0)

    print_report(outputs)
    write_outputs(outputs)


if __name__ == "__main__":
    main()
