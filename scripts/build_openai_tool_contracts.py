#!/usr/bin/env python3
"""Generate the versioned deterministic OpenAI tool contract artifact."""

from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = ROOT / "packages" / "openai" / "python"
OUTPUT = ROOT / "packages" / "openai" / "tool_contracts.json"
sys.path.insert(0, str(PACKAGE_ROOT))

from butterflylens_openai import contract_document  # noqa: E402


def main() -> None:
    OUTPUT.write_text(
        json.dumps(contract_document(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
