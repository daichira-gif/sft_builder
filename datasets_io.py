"""Colab/Network-only: load streaming datasets from HuggingFace."""
import random
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pandas as pd
from datasets import get_dataset_config_names, get_dataset_split_names, load_dataset

from .config import MAX_CELL_CHARS, MAX_ROWS_PER_SAMPLE, SAFE_COLS
from .utils import norm


def _pick_split(name: str, config: Optional[str] = None) -> str:
    splits = get_dataset_split_names(name, config) if config else get_dataset_split_names(name)
    return "train" if "train" in splits else splits[0]


def load_streams(seed: int = 42):
    random.seed(seed)

    # Shopify
    shopify_split = _pick_split("Shopify/product-catalogue")
    ds_shopify = load_dataset("Shopify/product-catalogue", split=shopify_split, streaming=True)

    # OpenFoodFacts (config REQUIRED)
    OFF_NAME = "openfoodfacts/product-database"
    off_configs = get_dataset_config_names(OFF_NAME)
    preferred_cfgs = [c for c in ["food", "beauty"] if c in off_configs]
    off_cfgs_use = preferred_cfgs if preferred_cfgs else off_configs[:2]

    ds_off = {}
    for cfg in off_cfgs_use:
        sp = _pick_split(OFF_NAME, cfg)
        ds_off[cfg] = load_dataset(OFF_NAME, cfg, split=sp, streaming=True)

    # GTFS
    gtfs_split = _pick_split("ontologicalapple/vrts-gtfs-archive")
    ds_gtfs = load_dataset("ontologicalapple/vrts-gtfs-archive", split=gtfs_split, streaming=True)

    return {
        "shopify": (ds_shopify, SAFE_COLS["shopify"]),
        "openfoodfacts": ({cfg: (ds_off[cfg], SAFE_COLS["openfoodfacts"]) for cfg in ds_off}, None),
        "gtfs": (ds_gtfs, SAFE_COLS["gtfs"]),
        "openfoodfacts_cfgs": list(ds_off.keys()),
        "splits": {"shopify": shopify_split, "openfoodfacts_configs": list(ds_off.keys()), "gtfs": gtfs_split},
    }


def pick_cols(row: Dict[str, Any], preferred: List[str]) -> List[str]:
    cols: List[str] = []
    for c in preferred:
        if c in row and row.get(c) not in (None, "", [], {}):
            cols.append(c)
    return cols


def rows_from_stream(ds, pref_cols) -> Iterable[Tuple[List[Dict[str, str]], List[str]]]:
    buf: List[Dict[str, str]] = []
    cols: Optional[List[str]] = None

    for r in ds:
        if cols is None:
            cols = pick_cols(r, pref_cols)
            if not cols:
                continue

        rr: Dict[str, str] = {}
        for c in cols:
            v = r.get(c, "")
            if isinstance(v, dict):
                keys = list(v.keys())[:3]
                v = {k: v.get(k, "") for k in keys}
            rr[c] = str(norm(v))[:MAX_CELL_CHARS]

        buf.append(rr)
        if len(buf) >= MAX_ROWS_PER_SAMPLE:
            yield buf, cols
            buf = []

