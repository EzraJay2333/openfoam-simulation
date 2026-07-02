#!/usr/bin/env python3
"""Run repository and OpenFOAM installation preflight checks."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import jsonschema
import yaml

ROOT = Path(__file__).resolve().parents[1]
APPLICATION_NAMES = (
    "simpleFoam",
    "foamRun",
    "foamMultiRun",
    "incompressibleFluid",
    "solid",
    "porousSimpleFoam",
    "chtMultiRegionFoam",
    "adjointShapeOptimisationFoam",
    "adjointShapeOptimizationFoam",
    "adjointOptimisationFoam",
    "adjointOptimizationFoam",
)


def _check(name: str, ok: bool, detail: str) -> dict[str, str]:
    return {"name": name, "status": "pass" if ok else "fail", "detail": detail}


def _load_schema(root: Path, name: str) -> dict[str, Any]:
    return json.loads((root / "schemas" / f"{name}.schema.json").read_text(encoding="utf-8"))


def run_repository_checks(root: str | Path = ROOT) -> dict[str, Any]:
    root = Path(root)
    checks: list[dict[str, str]] = []
    try:
        json.loads((root / "evals/evals.json").read_text(encoding="utf-8"))
        yaml.safe_load((root / "registry/problem-types.yaml").read_text(encoding="utf-8"))
        solvers = yaml.safe_load((root / "registry/solvers.yaml").read_text(encoding="utf-8"))
        jsonschema.validate(solvers, _load_schema(root, "solver-registry"))
        for path in (root / "templates").glob("*/workflow.yaml"):
            workflow = yaml.safe_load(path.read_text(encoding="utf-8"))
            jsonschema.validate(workflow, _load_schema(root, "workflow"))
        checks.append(_check("structured_data", True, "JSON, YAML and schemas are valid"))
    except Exception as exc:
        checks.append(_check("structured_data", False, str(exc)))

    required = [
        "scripts/parse_of_log.py",
        "scripts/doctor.py",
        "references/error-diagnostics.md",
        "references/geometry-physics-vv.md",
        "references/local-topology-setup-cn.md",
    ]
    required.extend(
        str(path.relative_to(root) / "case-skeleton")
        for path in (root / "templates").iterdir()
        if path.is_dir() and (path / "workflow.yaml").is_file()
    )
    missing = [entry for entry in required if not (root / entry).exists()]
    required_detail = "missing: " + ", ".join(missing) if missing else "complete"
    checks.append(_check("required_files", not missing, required_detail))

    shell_files = list(root.glob("scripts/*.sh")) + list(root.glob("templates/*/case-skeleton/*.sh"))
    bash = shutil.which("bash")
    failures = []
    if bash:
        for path in shell_files:
            result = subprocess.run(
                [bash, "-n"],
                input=path.read_bytes(),
                capture_output=True,
                check=False,
            )
            if result.returncode:
                failures.append(
                    f"{path.relative_to(root)}: {result.stderr.decode('utf-8', errors='replace').strip()}"
                )
    else:
        failures.append("bash not found")
    shell_detail = "; ".join(failures) if failures else f"{len(shell_files)} files"
    checks.append(_check("shell_syntax", not failures, shell_detail))

    return {"schema_version": "1.0", "ok": all(item["status"] == "pass" for item in checks), "checks": checks}


def inspect_openfoam_root(root: str | Path, appbin: str | Path | None = None) -> dict[str, Any]:
    root = Path(root)
    match = re.search(r"OpenFOAM[-_]?([0-9]+)", root.name, re.IGNORECASE)
    version = match.group(1) if match else "unknown"
    appbin_path = Path(appbin) if appbin else None
    applications: dict[str, dict[str, Any]] = {}
    for name in APPLICATION_NAMES:
        binary = appbin_path / name if appbin_path else None
        wrapper = root / "bin" / name
        source_matches = (
            list((root / "applications").glob(f"**/{name}"))
            if (root / "applications").exists()
            else []
        )
        if binary and binary.is_file():
            availability = "binary"
        elif wrapper.is_file():
            availability = "wrapper"
        elif source_matches:
            availability = (
                "module_source"
                if "modules" in source_matches[0].relative_to(root / "applications").parts
                else "source_only"
            )
        else:
            availability = "missing"
        applications[name] = {
            "availability": availability,
            "binary": str(binary) if binary and binary.is_file() else None,
            "wrapper": str(wrapper) if wrapper.is_file() else None,
            "source": str(source_matches[0]) if source_matches else None,
        }
    return {
        "distribution_family": "openfoam_org" if (root / "applications/legacy").exists() else "unknown",
        "version": version,
        "root": str(root),
        "appbin": str(appbin_path) if appbin_path else None,
        "applications": applications,
    }


def inspect_environment() -> dict[str, Any]:
    project = os.environ.get("WM_PROJECT_DIR")
    appbin = os.environ.get("FOAM_APPBIN")
    report = inspect_openfoam_root(project, appbin) if project and Path(project).is_dir() else None
    return {
        "platform": os.name,
        "mpi": shutil.which("mpirun"),
        "openfoam": report,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--repository-only", action="store_true")
    parser.add_argument("--output")
    args = parser.parse_args()
    result = run_repository_checks(args.root)
    if not args.repository_only:
        result["environment"] = inspect_environment()
    encoded = json.dumps(result, indent=2, ensure_ascii=False)
    if args.output:
        Path(args.output).write_text(encoded + "\n", encoding="utf-8", newline="\n")
    else:
        print(encoded)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
