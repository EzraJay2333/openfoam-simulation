#!/usr/bin/env python3
"""Create a schema-versioned experimental workflow record."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import jsonschema
import yaml

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "learning-record.schema.json"


def canonical_id(value: Any, default: str = "unknown") -> str:
    if value in (None, ""):
        return default
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", str(value).lower())).strip("_") or default


def slugify(text: str) -> str:
    return canonical_id(text, "unnamed").replace("_", "-")


def build_fingerprint(spec: dict[str, Any]) -> dict[str, Any]:
    opt = spec.get("optimisation", {})
    flow = spec.get("flow_regime", {})
    physics = spec.get("physical_models", {})
    dimensions = spec.get("geometry", {}).get("dimensions", {}).get("type", "3d")
    turbulence = physics.get("turbulence", {}).get("model", "laminar")
    thermal = physics.get("thermal", {})
    return {
        "flow_regime": canonical_id(flow.get("time_behavior", flow.get("flow_type", "unknown"))),
        "compressibility": canonical_id(flow.get("compressibility", "incompressible")),
        "turbulence": canonical_id(turbulence),
        "phases": canonical_id(physics.get("phases", "single_phase")),
        "thermal": "heat_transfer" if thermal.get("enabled") else "isothermal",
        "geometry_class": canonical_id(spec.get("geometry", {}).get("class", "unknown")),
        "spatial_dimensions": canonical_id(dimensions),
        "optimisation_family": canonical_id(opt.get("type", "none")),
        "objectives": [canonical_id(item.get("name")) for item in opt.get("objectives", [])],
        "constraints": [canonical_id(item.get("name")) for item in opt.get("constraints", [])],
    }


def build_record(spec: dict[str, Any], results: dict[str, Any]) -> dict[str, Any]:
    identity = spec.get("environment", {}).get("of_identity", {})
    version = str(identity.get("version", "unknown"))
    return {
        "schema_version": "2.0",
        "name": spec.get("project_name", "unnamed"),
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "experimental",
        "distribution": canonical_id(identity.get("distribution_family", "unknown")),
        "version_range": {"min": version, "max": version, "verified_on": [version]},
        "problem_fingerprint": build_fingerprint(spec),
        "solver_selection": {
            "selected": results.get("solver", spec.get("primal_solver", {}).get("application", "unknown")),
            "rejected_alternatives": results.get("rejected_solvers", []),
            "selection_rationale": results.get("solver_rationale", ""),
        },
        "support_level": canonical_id(spec.get("optimisation", {}).get("support_level", "experimental")),
        "sources": results.get("documentation_audit", []),
        "normalized_inputs": {
            key: spec.get(key, {} if key not in {"boundary_conditions"} else [])
            for key in ("geometry", "materials", "flow_regime", "boundary_conditions", "optimisation", "mesh")
        },
        "execution": {
            "case_directory": results.get("case_path", ""),
            "commands": results.get("commands", []),
            "stages_completed": results.get("stages_completed", []),
            "run_manifest": results.get("run_manifest", ""),
        },
        "results": {
            "primal_converged": results.get("primal_converged", False),
            "adjoint_converged": results.get("adjoint_converged", False),
            "objective_initial": results.get("objective_initial"),
            "objective_final": results.get("objective_final"),
            "objective_change_pct": results.get("objective_change_pct"),
            "constraints_satisfied": results.get("constraints_satisfied", []),
            "design_iterations": results.get("design_iterations", 0),
            "final_mesh_cells": results.get("final_mesh_cells", 0),
        },
        "validation": {
            "mass_imbalance": results.get("mass_imbalance"),
            "conservation_ok": results.get("conservation_ok", False),
            "physical_plausibility_ok": results.get("physical_plausibility_ok", False),
            "mesh_quality_ok": results.get("mesh_quality_ok", False),
            "residuals_within_tolerance": results.get("residuals_within_tolerance", False),
            "overall_assessment": results.get("overall_assessment", "UNASSESSED"),
        },
        "known_failure_modes": results.get("failure_modes_encountered", []),
        "recovery_rules": results.get("recovery_rules", []),
        "reusable_files": results.get("key_output_files", []),
        "warnings": results.get("warnings", []),
    }


def validate_record(record: dict[str, Any]) -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(record, schema)


def write_record(record: dict[str, Any], output_path: str | Path) -> None:
    validate_record(record)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        yaml.safe_dump(record, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
        newline="\n",
    )
    parsed = yaml.safe_load(output.read_text(encoding="utf-8"))
    validate_record(parsed)


def scaffold(spec_path: str, results_path: str, output_path: str) -> dict[str, Any]:
    spec = json.loads(Path(spec_path).read_text(encoding="utf-8"))
    results_file = Path(results_path)
    results = json.loads(results_file.read_text(encoding="utf-8")) if results_file.exists() else {}
    record = build_record(spec, results)
    write_record(record, output_path)
    print(f"Learning candidate written to: {output_path}")
    print("Status: experimental")
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", required=True)
    parser.add_argument("--results", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    if not Path(args.spec).is_file():
        print(f"ERROR: spec file not found: {args.spec}", file=sys.stderr)
        return 1
    scaffold(args.spec, args.results, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
