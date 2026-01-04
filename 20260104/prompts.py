from typing import List
from ..utils import truncate_prompt

def prompt_csv_to_json(csv: str, attrs: List[str]) -> str:
    return truncate_prompt(
        f"""You are a data extraction assistant.
Extract the following attributes from the CSV and output JSON.
Return ONLY JSON.

RULES:
- Keep one object per row in order.
- Include all ATTRIBUTES as keys.
- Empty cells are allowed and must be empty strings.
- Do not add extra keys or explanations.

ATTRIBUTES: {', '.join(attrs)}
CSV:
{csv}
"""
    )

def prompt_json_to_csv(js: str) -> str:
    return truncate_prompt(
        f"""Convert the following JSON into CSV. Return ONLY CSV.

JSON:
{js}
"""
    )

def prompt_xml_to_json(xml: str, attrs: List[str]) -> str:
    return truncate_prompt(
        f"""Extract the following attributes from XML and output JSON. Return ONLY JSON.

ATTRIBUTES: {', '.join(attrs)}
XML:
{xml}
"""
    )

def prompt_text_to_json(text: str, attrs: List[str]) -> str:
    return truncate_prompt(
        f"""Extract the following attributes from text and output JSON. Return ONLY JSON.

ATTRIBUTES: {', '.join(attrs)}
TEXT:
{text}
"""
    )

# Schema-constrained generation (JSON)
def prompt_text_to_json_schema(text: str, schema_desc: str) -> str:
    return truncate_prompt(
        f"""You are a structured data generation assistant.
Generate JSON strictly following the SPECIFICATION below.

Return ONLY JSON.

SPECIFICATION:
{schema_desc}

TEXT:
{text}
"""
    )

# Schema-constrained generation (YAML)
def prompt_text_to_yaml_schema(text: str, schema_desc: str) -> str:
    return truncate_prompt(
        f"""You are a structured data generation assistant.
Generate YAML strictly following the SPECIFICATION below.

Return ONLY YAML.

SPECIFICATION:
{schema_desc}

TEXT:
{text}
"""
    )

# Schema-constrained generation (TOML)
def prompt_text_to_toml_schema(text: str, schema_desc: str) -> str:
    return truncate_prompt(
        f"""You are a structured data generation assistant.
Generate TOML strictly following the SPECIFICATION below.

Return ONLY TOML.

SPECIFICATION:
{schema_desc}

TEXT:
{text}
"""
    )

def prompt_json_to_xml(js: str) -> str:
    return truncate_prompt(
        f"""Convert the following JSON into well-formed XML. Return ONLY XML.

XML RULES:
- Root element is <root>.
- For dict keys: use ASCII tag names; if invalid or starting with 'xml', use <k>.
- For lists: wrap items with <item> under their parent.
- Escape special characters (&, <, >). Keep order stable.

JSON:
{js}
"""
    )

def prompt_yaml_to_xml(yml: str) -> str:
    return truncate_prompt(
        f"""Convert the following YAML into well-formed XML. Return ONLY XML.

XML RULES:
- Root element is <root>.
- Map keys -> child elements (ASCII; invalid names or starting with 'xml' -> <k>).
- Sequences -> repeated <item> children.
- Text content is the string value; escape special characters.

YAML:
{yml}
"""
    )

def prompt_csv_to_xml(csv: str) -> str:
    return truncate_prompt(
        f"""Convert the following CSV into well-formed XML. Return ONLY XML.

XML RULES:
- Root element is <root>.
- Each row -> <row> with child elements for each column.
- Use ASCII tag names; otherwise use <k>.
- Preserve row order; escape special characters.

CSV:
{csv}
"""
    )

def prompt_text_to_xml(text: str, attrs: List[str]) -> str:
    return truncate_prompt(
        f"""Extract the following attributes from text and output well-formed XML.
Return ONLY XML.

XML RULES:
- Root <root>; include one <item> element per matched record if multiple.
- Child tag names must be ASCII; invalid or 'xml*' -> <k>.
- Escape special characters; keep only ATTRIBUTES as children.

ATTRIBUTES: {', '.join(attrs)}
TEXT:
{text}
"""
    )

def prompt_json_to_toml(js: str) -> str:
    return truncate_prompt(
        f"""Convert the following JSON into TOML. Return ONLY TOML.

TOML RULES:
- Do NOT use inline tables (no {{...}}). Use tables [a] / nested [a.b].
- For arrays of objects, use arrays-of-tables: [[a.b]] per item.
- Keys must be TOML-safe; quote unsafe keys.
- Null -> empty string.

JSON:
{js}
"""
    )

def prompt_yaml_to_toml(yml: str) -> str:
    return truncate_prompt(
        f"""Convert the following YAML into TOML. Return ONLY TOML.

TOML RULES:
- Do NOT use inline tables (no {{...}}).
- Maps -> tables [a]; nested maps -> [a.b] sections.
- Sequences of objects -> arrays-of-tables: [[a.b]] repeated sections.
- Scalars: bool/int/float/string; null -> empty string.
- Keys must be TOML-safe; quote unsafe keys.

YAML:
{yml}
"""
    )

def prompt_text_to_toml(text: str, attrs: List[str]) -> str:
    return truncate_prompt(
        f"""Extract the following attributes from text and output TOML. Return ONLY TOML.

TOML RULES:
- Do NOT use inline tables (no {{...}}). Place each table on its own line.
- Use tables/arrays-of-tables for nested structures; quote unsafe keys.
- Scalars: bool/int/float/string; represent null as empty string.
- Include only the requested ATTRIBUTES; preserve item order where applicable.

ATTRIBUTES: {', '.join(attrs)}
TEXT:
{text}
"""
    )

def prompt_toml_to_json(toml_s: str) -> str:
    return truncate_prompt(
        f"""Convert the following TOML into JSON. Return ONLY JSON.

TOML:
{toml_s}
"""
    )

def prompt_xml_to_yaml(xml_s: str) -> str:
    return truncate_prompt(
        f"""Convert the following XML into YAML. Return ONLY YAML.

YAML RULES:
- Elements with only text -> scalar.
- Repeated tags -> YAML sequences.
- <item> children -> YAML sequences under the parent key.
- Tag text maps to value; attributes are ignored.

XML:
{xml_s}
"""
    )

def prompt_csv_to_yaml(csv_s: str) -> str:
    return truncate_prompt(
        f"""Convert the following CSV into YAML. Return ONLY YAML.

CSV:
{csv_s}
"""
    )

def prompt_text_to_yaml(text: str, attrs: List[str]) -> str:
    return truncate_prompt(
        f"""Extract the following attributes from text and output YAML. Return ONLY YAML.

ATTRIBUTES: {', '.join(attrs)}
TEXT:
{text}
"""
    )

def prompt_json_to_yaml(js: str) -> str:
    return truncate_prompt(
        f"""Convert the following JSON into YAML. Return ONLY YAML.

JSON:
{js}
"""
    )
