"""Run a real-LLM CCP vs text comparison.

This wrapper keeps the historical command path working while the implementation
lives in smaller modules under real_llm_comparison/.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from real_llm_comparison.cli import main


if __name__ == "__main__":
    main()
