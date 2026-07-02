#!/usr/bin/env python3
"""Parse key convergence and failure signals from an OpenFOAM log."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

TIME_RE = re.compile(r"^Time\s*=\s*([-+0-9.eE]+)", re.MULTILINE)
RESIDUAL_RE = re.compile(
    r"Solving for\s+([^,]+),\s+Initial residual\s*=\s*([-+0-9.eE]+),\s+"
    r"Final residual\s*=\s*([-+0-9.eE]+),\s+No Iterations\s+(\d+)"
)
EXEC_RE = re.compile(r"ExecutionTime\s*=\s*([-+0-9.eE]+)\s*s")
FATAL_RE = re.compile(r"FOAM FATAL (?:IO )?ERROR:\s*([^\r\n]+)")


def parse_log_text(text: str) -> dict[str, Any]:
    residuals: dict[str, list[dict[str, Any]]] = {}
    for field, initial, final, iterations in RESIDUAL_RE.findall(text):
        residuals.setdefault(field.strip(), []).append(
            {"initial": float(initial), "final": float(final), "iterations": int(iterations)}
        )
    execution = EXEC_RE.findall(text)
    return {
        "times": [float(value) for value in TIME_RE.findall(text)],
        "residuals": residuals,
        "execution_time_seconds": float(execution[-1]) if execution else None,
        "fatal_errors": [message.strip() for message in FATAL_RE.findall(text)],
        "floating_point_exception": "Floating point exception" in text,
        "segmentation_fault": "segmentation fault" in text.lower(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log")
    parser.add_argument("--output")
    args = parser.parse_args()
    result = parse_log_text(Path(args.log).read_text(encoding="utf-8", errors="replace"))
    encoded = json.dumps(result, indent=2, ensure_ascii=False)
    if args.output:
        Path(args.output).write_text(encoded + "\n", encoding="utf-8", newline="\n")
    else:
        print(encoded)
    failed = result["fatal_errors"] or result["floating_point_exception"] or result["segmentation_fault"]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
