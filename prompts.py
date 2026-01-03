from typing import List

from .utils import truncate_prompt


def prompt_csv_to_json(csv: str, attrs: List[str]) -> str:
    return truncate_prompt(
        f"""You are a data extraction assistant.
Extract the following attributes from the CSV and output JSON.
Return ONLY JSON.

ATTRIBUTES:
{', '.join(attrs)}

CSV:
{csv}
"""
    )


def prompt_json_to_csv(js: str) -> str:
    return truncate_prompt(
        f"""Convert the following JSON into CSV.
Return ONLY CSV.

JSON:
{js}
"""
    )


def prompt_xml_to_json(xml: str, attrs: List[str]) -> str:
    return truncate_prompt(
        f"""Extract the following attributes from XML and output JSON.
Return ONLY JSON.

ATTRIBUTES:
{', '.join(attrs)}

XML:
{xml}
"""
    )


def prompt_text_to_json(text: str, attrs: List[str]) -> str:
    return truncate_prompt(
        f"""Extract the following attributes from text and output JSON.
Return ONLY JSON.

ATTRIBUTES:
{', '.join(attrs)}

TEXT:
{text}
"""
    )


def prompt_json_to_xml(js: str) -> str:
    return truncate_prompt(
        f"""Convert the following JSON into well-formed XML.
Return ONLY XML.

JSON:
{js}
"""
    )


def prompt_yaml_to_xml(yml: str) -> str:
    return truncate_prompt(
        f"""Convert the following YAML into well-formed XML.
Return ONLY XML.

YAML:
{yml}
"""
    )


def prompt_csv_to_xml(csv: str) -> str:
    return truncate_prompt(
        f"""Convert the following CSV into well-formed XML.
Return ONLY XML.

CSV:
{csv}
"""
    )


def prompt_text_to_xml(text: str, attrs: List[str]) -> str:
    return truncate_prompt(
        f"""Extract the following attributes from text and output well-formed XML.
Return ONLY XML.

ATTRIBUTES:
{', '.join(attrs)}

TEXT:
{text}
"""
    )


def prompt_json_to_toml(js: str) -> str:
    return truncate_prompt(
        f"""Convert the following JSON into TOML.
Return ONLY TOML.

JSON:
{js}
"""
    )


def prompt_yaml_to_toml(yml: str) -> str:
    return truncate_prompt(
        f"""Convert the following YAML into TOML.
Return ONLY TOML.

YAML:
{yml}
"""
    )


def prompt_text_to_toml(text: str, attrs: List[str]) -> str:
    return truncate_prompt(
        f"""Extract the following attributes from text and output TOML.
Return ONLY TOML.

ATTRIBUTES:
{', '.join(attrs)}

TEXT:
{text}
"""
    )


def prompt_toml_to_json(toml_s: str) -> str:
    return truncate_prompt(
        f"""Convert the following TOML into JSON.
Return ONLY JSON.

TOML:
{toml_s}
"""
    )


def prompt_xml_to_yaml(xml_s: str) -> str:
    return truncate_prompt(
        f"""Convert the following XML into YAML.
Return ONLY YAML.

XML:
{xml_s}
"""
    )


def prompt_csv_to_yaml(csv_s: str) -> str:
    return truncate_prompt(
        f"""Convert the following CSV into YAML.
Return ONLY YAML.

CSV:
{csv_s}
"""
    )


def prompt_text_to_yaml(text: str, attrs: List[str]) -> str:
    return truncate_prompt(
        f"""Extract the following attributes from text and output YAML.
Return ONLY YAML.

ATTRIBUTES:
{', '.join(attrs)}

TEXT:
{text}
"""
    )


def prompt_json_to_yaml(js: str) -> str:
    return truncate_prompt(
        f"""Convert the following JSON into YAML.
Return ONLY YAML.

JSON:
{js}
"""
    )

