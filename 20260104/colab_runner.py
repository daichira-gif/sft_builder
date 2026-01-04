import random
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
from .config import DEBUG_DIR, OUT_DIR, SEED
from ..datasets_io import load_streams, rows_from_stream
from ..p0_guard import P0Guard
from ..report import print_report
from ..utils import ensure_dirs
from ..write_outputs import write_outputs


def main():
    random.seed(SEED)
    ensure_dirs(OUT_DIR, DEBUG_DIR)

    streams = load_streams(seed=SEED)
    print("Using splits:", streams["splits"])

    shop_rows_iter = rows_from_stream(streams["shopify"][0], streams["shopify"][1])
    off_cfgs = streams["openfoodfacts_cfgs"]
    off_iters = {
        cfg: rows_from_stream(streams["openfoodfacts"][0][cfg][0], streams["openfoodfacts"][0][cfg][1])
        for cfg in off_cfgs
    }
    gtfs_rows_iter = rows_from_stream(streams["gtfs"][0], streams["gtfs"][1])

    def take_rows(src: str):
        nonlocal shop_rows_iter, off_iters, gtfs_rows_iter

        def _next_shopify():
            nonlocal shop_rows_iter
            try:
                return next(shop_rows_iter)
            except StopIteration:
                shop_rows_iter = rows_from_stream(streams["shopify"][0], streams["shopify"][1])
                return next(shop_rows_iter)

        def _next_off(cfg: str):
            nonlocal off_iters
            it = off_iters.get(cfg)
            if it is None:
                it = rows_from_stream(streams["openfoodfacts"][0][cfg][0], streams["openfoodfacts"][0][cfg][1])
                off_iters[cfg] = it
            try:
                return next(it)
            except StopIteration:
                off_iters[cfg] = rows_from_stream(streams["openfoodfacts"][0][cfg][0], streams["openfoodfacts"][0][cfg][1])
                return next(off_iters[cfg])

        def _next_gtfs():
            nonlocal gtfs_rows_iter
            try:
                return next(gtfs_rows_iter)
            except StopIteration:
                gtfs_rows_iter = rows_from_stream(streams["gtfs"][0], streams["gtfs"][1])
                return next(gtfs_rows_iter)

        if src == "shopify":
            return _next_shopify(), "shopify"
        if src == "openfoodfacts":
            cfg = random.choice(off_cfgs)
            return _next_off(cfg), f"openfoodfacts:{cfg}"
        if src == "gtfs":
            return _next_gtfs(), "gtfs"
        raise ValueError(src)

    outputs = make_outputs_dict()
    p0 = P0Guard(disabled=False)

    build_core_tabular(outputs, take_rows, p0)
    print("core_tabular done:", len(outputs["sft_core_c_tabular.jsonl"]))

    build_core_xml_in(outputs, take_rows, p0)
    print("core_xml_in done:", len(outputs["sft_core_c_xml_in.jsonl"]))

    build_core_gtfs(outputs, take_rows, p0)
    print("core_gtfs done:", len(outputs["sft_core_g_gtfs.jsonl"]))

    # NEW packs
    build_core_text_to_json_schema(outputs, take_rows, p0)
    print("core_text_to_json_schema done:", len(outputs["sft_core_c_text_to_json_schema.jsonl"]))

    build_core_text_to_json_schema_nested(outputs, take_rows, p0)
    print("core_text_to_json_schema_nested done:", len(outputs["sft_core_c_text_to_json_schema_nested.jsonl"]))

    build_core_text_to_yaml_schema(outputs, take_rows, p0)
    print("core_text_to_yaml_schema done:", len(outputs["sft_core_c_text_to_yaml_schema.jsonl"]))

    build_core_text_to_toml_schema(outputs, take_rows, p0)
    print("core_text_to_toml_schema done:", len(outputs["sft_core_c_text_to_toml_schema.jsonl"]))

    build_pack_hard_mixed(outputs, take_rows, p0)
    print("pack_hard_mixed done:", len(outputs["sft_pack_hard_mixed.jsonl"]))

    build_core_xml_out(outputs, take_rows, p0)
    print("core_xml_out done:", len(outputs["sft_core_c_xml_out.jsonl"]))

    build_core_toml_out(outputs, take_rows, p0)
    print("core_toml_out done:", len(outputs["sft_core_c_toml_out.jsonl"]))

    build_core_yaml_out_min(outputs, take_rows, p0)
    print("core_yaml_out_min done:", len(outputs["sft_core_c_yaml_out_min.jsonl"]))

    print_report(outputs)
    write_outputs(outputs)


if __name__ == "__main__":
    main()
