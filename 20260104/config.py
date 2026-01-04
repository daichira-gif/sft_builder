import os

# Seed
SEED = int(os.environ.get("SFT_SEED", "42"))

# Output directories
OUT_DIR = os.environ.get("SFT_OUT_DIR", "/content/structured_sft_outputs")
DEBUG_DIR = os.path.join(OUT_DIR, "_debug")
XML_FAIL_LOG = os.path.join(DEBUG_DIR, "xml_validation_failures.jsonl")
TOML_FAIL_LOG = os.path.join(DEBUG_DIR, "toml_validation_failures.jsonl")
REJECT_LOG = os.path.join(DEBUG_DIR, "reject_0valid_or_bad_messages.jsonl")

# Sizing
MAX_ROWS_PER_SAMPLE = int(os.environ.get("SFT_MAX_ROWS", "5"))
MAX_CELL_CHARS = int(os.environ.get("SFT_MAX_CELL_CHARS", "180"))
MAX_INPUT_CHARS = int(os.environ.get("SFT_MAX_INPUT_CHARS", "1800"))
MAX_OUTPUT_CHARS = int(os.environ.get("SFT_MAX_OUTPUT_CHARS", "1800"))
MAX_ATTRS = int(os.environ.get("SFT_MAX_ATTRS", "6"))

# Tokenizer / boundary filter
MODEL_NAME = os.environ.get("SFT_TOKENIZER_MODEL", "unsloth/Qwen3-4B-Instruct-2507")
MAX_SEQ_LEN = int(os.environ.get("SFT_MAX_SEQ_LEN", "2048"))

# Budgets (per output file)
BUDGET = {
    "sft_core_c_tabular.jsonl": 4500,            # csv<->json
    "sft_core_c_xml_in.jsonl": 2500,             # xml->json
    "sft_core_c_xml_out.jsonl": 3500,            # -> XML
    "sft_core_c_toml_out.jsonl": 2500,           # -> TOML (+ toml->json)
    "sft_core_c_yaml_out_min.jsonl": 800,        # -> YAML (minimal)
    "sft_core_g_gtfs.jsonl": 2000,               # text->json (GTFS)
    "sft_pack_hard_mixed.jsonl": 2000,           # constraint -> json

    # === NEW: スキーマ指向の生成パック（生成強化） ===
    "sft_core_c_text_to_json_schema.jsonl": 2000,           # TEXT + SPEC(flat) -> JSON
    "sft_core_c_text_to_json_schema_nested.jsonl": 2000,    # TEXT + SPEC(nested objects/arrays) -> JSON
    "sft_core_c_text_to_yaml_schema.jsonl": 1200,           # TEXT + SPEC -> YAML
    "sft_core_c_text_to_toml_schema.jsonl": 1200,           # TEXT + SPEC -> TOML
}

# Desired distribution by output format (tuning target)
def _float_env(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, str(default)))
    except Exception:
        return default

DESIRED_OUTPUT_COUNTS = {"csv": 200, "json": 250, "yaml": 80, "xml": 250, "toml": 120}
FOCUS_MULTIPLIER = {"xml": _float_env("SFT_FOCUS_XML", 3.0), "toml": _float_env("SFT_FOCUS_TOML", 3.0)}

# Focus multipliers (used by auto-budget suggestion).
def _as_bool(val: str, default: bool) -> bool:
    if val is None:
        return default
    return str(val).strip().lower() in {"1", "true", "yes", "on"}

DIVERSIFY_ENABLE = _as_bool(os.environ.get("SFT_DIVERSIFY_ENABLE", "1"), True)
DIVERSIFY_ROW_TRIM_ENABLE = _as_bool(os.environ.get("SFT_DIVERSIFY_ROW_TRIM", "1"), True)
DIVERSIFY_HARD_MIXED_ENABLE = _as_bool(os.environ.get("SFT_DIVERSIFY_HARD_MIXED", "1"), True)

# Value jitter probabilities (0.0–1.0)
PROB_EMPTY = float(os.environ.get("SFT_DIVERSIFY_PROB_EMPTY", "0.05"))
PROB_SUFFIX = float(os.environ.get("SFT_DIVERSIFY_PROB_SUFFIX", "0.05"))
PROB_PREFIX = float(os.environ.get("SFT_DIVERSIFY_PROB_PREFIX", "0.05"))
PROB_CASE = float(os.environ.get("SFT_DIVERSIFY_PROB_CASE", "0.08"))

# Attribute selection bias prob
ATTR_LENGTH_BIAS_PROB = float(os.environ.get("SFT_DIVERSIFY_ATTR_LENGTH_BIAS", "0.5"))

# Tabular routing: probability of selecting JSON->CSV (remaining goes to CSV->JSON)
TABULAR_JSON_TO_CSV_PROB = _float_env("SFT_TABULAR_JSON_TO_CSV_PROB", 0.6)

# Extraction allowance
EXTRACT_MIN_FILLED = int(os.environ.get("SFT_EXTRACT_MIN_FILLED", "1"))

# Optional budget overrides
def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except Exception:
        return default

# Apply overrides if provided
BUDGET["sft_core_c_xml_out.jsonl"] = _int_env("SFT_BUDGET_XML_OUT", BUDGET["sft_core_c_xml_out.jsonl"])
BUDGET["sft_core_c_tabular.jsonl"] = _int_env("SFT_BUDGET_TABULAR", BUDGET["sft_core_c_tabular.jsonl"])
BUDGET["sft_core_c_xml_in.jsonl"] = _int_env("SFT_BUDGET_XML_IN", BUDGET["sft_core_c_xml_in.jsonl"])
BUDGET["sft_core_c_toml_out.jsonl"] = _int_env("SFT_BUDGET_TOML_OUT", BUDGET["sft_core_c_toml_out.jsonl"])
BUDGET["sft_core_c_yaml_out_min.jsonl"] = _int_env("SFT_BUDGET_YAML_OUT", BUDGET["sft_core_c_yaml_out_min.jsonl"])
BUDGET["sft_core_g_gtfs.jsonl"] = _int_env("SFT_BUDGET_GTFS", BUDGET["sft_core_g_gtfs.jsonl"])
BUDGET["sft_pack_hard_mixed.jsonl"] = _int_env("SFT_BUDGET_HARD_MIXED", BUDGET["sft_pack_hard_mixed.jsonl"])

# NEW overrides
BUDGET["sft_core_c_text_to_json_schema.jsonl"] = _int_env(
    "SFT_BUDGET_TEXT_JSON_SCHEMA",
    BUDGET["sft_core_c_text_to_json_schema.jsonl"],
)
BUDGET["sft_core_c_text_to_json_schema_nested.jsonl"] = _int_env(
    "SFT_BUDGET_TEXT_JSON_SCHEMA_NESTED",
    BUDGET["sft_core_c_text_to_json_schema_nested.jsonl"],
)
BUDGET["sft_core_c_text_to_yaml_schema.jsonl"] = _int_env(
    "SFT_BUDGET_TEXT_YAML_SCHEMA",
    BUDGET["sft_core_c_text_to_yaml_schema.jsonl"],
)
BUDGET["sft_core_c_text_to_toml_schema.jsonl"] = _int_env(
    "SFT_BUDGET_TEXT_TOML_SCHEMA",
    BUDGET["sft_core_c_text_to_toml_schema.jsonl"],
)

# Curriculum phase tuning (1: basic, 2: default, 3: advanced)
CURRICULUM_PHASE = int(os.environ.get("SFT_CURRICULUM_PHASE", "2"))
if CURRICULUM_PHASE == 1:
    PROB_EMPTY *= 0.3
    PROB_SUFFIX *= 0.6
    PROB_PREFIX *= 0.6
    PROB_CASE *= 0.6
    ATTR_LENGTH_BIAS_PROB = min(1.0, ATTR_LENGTH_BIAS_PROB * 0.7)
    DIVERSIFY_ROW_TRIM_ENABLE = _as_bool(os.environ.get("SFT_DIVERSIFY_ROW_TRIM", "0"), False)
elif CURRICULUM_PHASE == 3:
    PROB_EMPTY *= 1.5
    PROB_SUFFIX *= 1.3
    PROB_PREFIX *= 1.3
    PROB_CASE *= 1.3
    ATTR_LENGTH_BIAS_PROB = min(1.0, ATTR_LENGTH_BIAS_PROB * 1.2)

def _normalize_probs(d):
    s = sum(max(0.0, v) for v in d.values())
    return {k: (max(0.0, v) / s if s > 0 else 0.0) for k, v in d.items()}

# XML OUT input-source mix
XML_OUT_PROBS = _normalize_probs(
    {
        "json": _float_env("SFT_XML_OUT_PROB_JSON", 0.35),
        "yaml": _float_env("SFT_XML_OUT_PROB_YAML", 0.20),
        "csv": _float_env("SFT_XML_OUT_PROB_CSV", 0.20),
        "text": _float_env("SFT_XML_OUT_PROB_TEXT", 0.25),
    }
)

# TOML OUT mode mix
TOML_OUT_PROBS = _normalize_probs(
    {
        "json": _float_env("SFT_TOML_OUT_PROB_JSON", 0.40),
        "yaml": _float_env("SFT_TOML_OUT_PROB_YAML", 0.25),
        "text": _float_env("SFT_TOML_OUT_PROB_TEXT", 0.20),
        "toml2json": _float_env("SFT_TOML_OUT_PROB_TOML2JSON", 0.15),
    }
)

# YAML OUT mode mix (minimal pack)
YAML_OUT_PROBS = _normalize_probs(
    {
        "xml": _float_env("SFT_YAML_OUT_PROB_XML", 0.40),
        "csv": _float_env("SFT_YAML_OUT_PROB_CSV", 0.30),
        "text": _float_env("SFT_YAML_OUT_PROB_TEXT", 0.20),
        "json": _float_env("SFT_YAML_OUT_PROB_JSON", 0.10),
    }
)
