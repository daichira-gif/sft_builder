from io import StringIO

import pandas as pd
import tomllib
import yaml
from lxml import etree


def validate_xml(s: str) -> bool:
    try:
        etree.fromstring(s.encode("utf-8"))
        return True
    except Exception:
        return False


def validate_toml(s: str) -> bool:
    try:
        tomllib.loads(s)
        return True
    except Exception:
        return False


def validate_yaml(s: str) -> bool:
    try:
        yaml.safe_load(s)
        return True
    except Exception:
        return False


def validate_csv(s: str) -> bool:
    try:
        # header-only CSV is valid; ensure pandas can parse it
        pd.read_csv(StringIO(s))
        return True
    except Exception:
        return False

