"""Structured SFT dataset builder (modularized).

This package splits network/Colab-only parts (datasets/tokenizer) from
local CPU-safe utilities (validators/serializers/builders/reporting).

Runners (module entry points):
- sft_builder/colab_runner.py
- sft_builder/local_runner.py
"""

