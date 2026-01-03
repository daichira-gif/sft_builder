"""Colab/full pipeline runner.

Installs deps (manually in Colab), loads datasets via streaming, runs full
builders with P0 guard enabled, writes outputs and reports.
"""
import os
import random
from typing import Dict, List, Tuple

from .builders import (
    build_core_gtfs,
    build_core_tabular,
    build_core_toml_out,
    build_core_xml_in,
    build_core_xml_out,
    build_core_yaml_out_min,
    build_pack_hard_mixed,
    make_outputs_dict,
)
from .config import DEBUG_DIR, OUT_DIR, SEED
from .datasets_io import load_streams, rows_from_stream
from .p0_guard import P0Guard
from .report import print_report
from .utils import ensure_dirs
from .write_outputs import write_outputs


def main():
    random.seed(SEED)
    ensure_dirs(OUT_DIR, DEBUG_DIR)

    streams = load_streams(seed=SEED)
    print("Using splits:", streams["splits"])

    # Prepare row iterators
    shop_rows_iter = rows_from_stream(streams["shopify"][0], streams["shopify"][1])
    off_cfgs = streams["openfoodfacts_cfgs"]
    off_iters = {cfg: rows_from_stream(streams["openfoodfacts"][0][cfg][0], streams["openfoodfacts"][0][cfg][1]) for cfg in off_cfgs}
    gtfs_rows_iter = rows_from_stream(streams["gtfs"][0], streams["gtfs"][1])

    def take_rows(src: str):
        if src == "shopify":
            return next(shop_rows_iter), "shopify"
        if src == "openfoodfacts":
            cfg = random.choice(off_cfgs)
            return next(off_iters[cfg]), f"openfoodfacts:{cfg}"
        if src == "gtfs":
            return next(gtfs_rows_iter), "gtfs"
        raise ValueError(src)

    outputs = make_outputs_dict()
    p0 = P0Guard(disabled=False)

    # Build packs
    build_core_tabular(outputs, take_rows, p0)
    print("core_tabular done:", len(outputs["sft_core_c_tabular.jsonl"]))
    build_core_xml_in(outputs, take_rows, p0)
    print("core_xml_in done:", len(outputs["sft_core_c_xml_in.jsonl"]))
    build_core_gtfs(outputs, take_rows, p0)
    print("core_gtfs done:", len(outputs["sft_core_g_gtfs.jsonl"]))
    build_pack_hard_mixed(outputs, take_rows, p0)
    print("pack_hard_mixed done:", len(outputs["sft_pack_hard_mixed.jsonl"]))
    build_core_xml_out(outputs, take_rows, p0)
    print("core_xml_out done:", len(outputs["sft_core_c_xml_out.jsonl"]))
    build_core_toml_out(outputs, take_rows, p0)
    print("core_toml_out done:", len(outputs["sft_core_c_toml_out.jsonl"]))
    build_core_yaml_out_min(outputs, take_rows, p0)
    print("core_yaml_out_min done:", len(outputs["sft_core_c_yaml_out_min.jsonl"]))

    # Report & write
    print_report(outputs)
    write_outputs(outputs)


if __name__ == "__main__":
    main()
