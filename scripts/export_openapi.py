#!/usr/bin/env python
"""Export the FastAPI OpenAPI schema to stdout."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def main() -> int:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "api"))
    os.chdir(Path(__file__).resolve().parents[1] / "apps" / "api")
    from app.main import app
    print(json.dumps(app.openapi(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
