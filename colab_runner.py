"""Compatibility runner: dispatch to 20260104 strategy runner.

This ensures any import of `StructEvalT.sft_builder.colab_runner` runs the
latest strategy-aligned pipeline (includes schema packs), keeping compatibility
with historical import paths.
"""

from .20260104.colab_runner import *  # re-export
from .20260104.colab_runner import main as main  # alias

if __name__ == "__main__":
    main()
