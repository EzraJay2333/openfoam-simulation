#!/usr/bin/env python3
"""Create a reproducibility manifest for an OpenFOAM case directory."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
from datetime import datetime, timezone
from pathlib import Path


def file_hashes(case: Path) -> dict[str, str]:
    result = {}
    for directory in ("0", "constant", "system"):
        for path in sorted((case / directory).glob("**/*")):
            if path.is_file():
                relative = str(path.relative_to(case)).replace("\\", "/")
                result[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def build_manifest(case: Path, commands: list[str]) -> dict:
    return {
        "schema_version": "1.0",
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "case_directory": str(case.resolve()),
        "openfoam": {
            "distribution": os.environ.get("WM_PROJECT", "unknown"),
            "version": os.environ.get("WM_PROJECT_VERSION", "unknown"),
            "root": os.environ.get("WM_PROJECT_DIR", ""),
            "options": os.environ.get("WM_OPTIONS", ""),
        },
        "host": {"system": platform.system(), "release": platform.release(), "machine": platform.machine()},
        "mpi": {"flavor": os.environ.get("MPI_ARCH_PATH", ""), "ranks": int(os.environ.get("OF_NP", "1"))},
        "commands": commands,
        "file_sha256": file_hashes(case),
        "logs": sorted(path.name for path in case.glob("log.*")),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case")
    parser.add_argument("--command", action="append", default=[])
    parser.add_argument("--output", default="run_manifest.json")
    args = parser.parse_args()
    case = Path(args.case)
    if not case.is_dir():
        parser.error(f"case directory not found: {case}")
    output = Path(args.output)
    if not output.is_absolute():
        output = case / output
    output.write_text(
        json.dumps(build_manifest(case, args.command), indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
