#!/usr/bin/env python3
"""scaffold_learning_record.py — Step 11: Learning Candidate Scaffold

Reads a simulation specification JSON and results summary, and produces a
YAML learning candidate record for storage in registry/learned-workflows/.

Usage:
    python3 scaffold_learning_record.py \\
        --spec simulation_spec.json \\
        --results results_summary.json \\
        --output registry/learned-workflows/<slug>.yaml

The output is always status: experimental. Promotion to validated requires
a separate rerun and explicit user approval.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone


def slugify(text: str) -> str:
    """Convert a problem description to a filesystem-safe slug."""
    return (
        text.lower()
        .replace(" ", "-")
        .replace("_", "-")
        .replace("/", "-")
        .replace("\\", "-")
    )


def build_fingerprint(spec: dict) -> dict:
    """Extract a stable problem fingerprint from the simulation spec."""
    opt = spec.get("optimisation", {})
    flow = spec.get("flow_regime", {})
    physics = spec.get("physical_models", {})

    return {
        "flow_regime": flow.get("flow_type", "unknown"),
        "compressibility": "incompressible",     # infer from spec
        "turbulence": physics.get("turbulence", {}).get("model", "laminar"),
        "phases": "single-phase",
        "thermal": "isothermal",                  # update from physics.thermal
        "geometry_class": spec.get("geometry", {}).get("dimensions", {}).get("type", "unknown"),
        "spatial_dimensions": spec.get("geometry", {}).get("dimensions", {}).get("type", "3d"),
        "optimisation_family": opt.get("type", "none"),
        "objectives": [o.get("name") for o in opt.get("objectives", [])],
        "constraints": [c.get("name") for c in opt.get("constraints", [])],
    }


def scaffold(spec_path: str, results_path: str, output_path: str) -> dict:
    """Generate a learning candidate YAML record."""

    spec = {}
    if os.path.exists(spec_path):
        with open(spec_path) as f:
            spec = json.load(f)

    results = {}
    if os.path.exists(results_path):
        with open(results_path) as f:
            results = json.load(f)

    fingerprint = build_fingerprint(spec)
    slug = slugify(spec.get("project_name", "unnamed"))

    # Determine distribution compatibility from spec
    of_identity = spec.get("environment", {}).get("of_identity", {})
    distribution = of_identity.get("distribution_family", "unknown")
    version = of_identity.get("version", "unknown")

    record = {
        # Metadata
        "name": spec.get("project_name", "unnamed"),
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "experimental",

        # Version scoping
        "distribution": distribution,
        "version_range": {
            "min": version,
            "max": version,
            "verified_on": [version],
        },

        # Problem fingerprint
        "problem_fingerprint": fingerprint,

        # Solver selection
        "solver_selection": {
            "selected": results.get("solver", spec.get("primal_solver", {}).get("application", "unknown")),
            "rejected_alternatives": results.get("rejected_solvers", []),
            "selection_rationale": results.get("solver_rationale", ""),
        },

        # Support level
        "support_level": spec.get("optimisation", {}).get("support_level", "native"),

        # Sources
        "sources": results.get("documentation_audit", []),

        # Inputs
        "normalized_inputs": {
            "geometry": spec.get("geometry", {}),
            "materials": spec.get("materials", {}),
            "flow_regime": spec.get("flow_regime", {}),
            "boundary_conditions": spec.get("boundary_conditions", []),
            "optimisation": spec.get("optimisation", {}),
            "mesh": spec.get("mesh", {}),
        },

        # Execution
        "execution": {
            "case_directory": results.get("case_path", ""),
            "commands": results.get("commands", []),
            "stages_completed": results.get("stages_completed", []),
        },

        # Results
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

        # Validation
        "validation": {
            "mass_imbalance": results.get("mass_imbalance"),
            "conservation_ok": results.get("conservation_ok", False),
            "physical_plausibility_ok": results.get("physical_plausibility_ok", False),
            "mesh_quality_ok": results.get("mesh_quality_ok", False),
            "residuals_within_tolerance": results.get("residuals_within_tolerance", False),
            "overall_assessment": results.get("overall_assessment", "UNASSESSED"),
        },

        # Failure modes
        "known_failure_modes": results.get("failure_modes_encountered", []),
        "recovery_rules": results.get("recovery_rules", []),

        # Reusable files
        "reusable_files": results.get("key_output_files", []),

        # Warnings
        "warnings": results.get("warnings", []),
    }

    # Write YAML
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    with open(output_path, "w") as f:
        f.write(yaml_dump(record))

    print(f"Learning candidate written to: {output_path}")
    print(f"Status: experimental")
    print(f"To promote to validated: re-run with a clean case, confirm all validation thresholds, and request promotion.")
    return record


def yaml_dump(data: dict, indent: int = 0) -> str:
    """Simple YAML dumper (no PyYAML dependency required)."""
    lines = []
    prefix = "  " * indent

    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"{prefix}{key}:")
            lines.append(yaml_dump(value, indent + 1))
        elif isinstance(value, list):
            if not value:
                lines.append(f"{prefix}{key}: []")
            else:
                lines.append(f"{prefix}{key}:")
                for item in value:
                    if isinstance(item, dict):
                        lines.append(f"{prefix}  - ")
                        lines.append(yaml_dump(item, indent + 2).lstrip())
                    elif isinstance(item, str):
                        escaped = item.replace("'", "''")
                        lines.append(f"{prefix}  - '{escaped}'")
                    else:
                        lines.append(f"{prefix}  - {item}")
        elif isinstance(value, bool):
            lines.append(f"{prefix}{key}: {'true' if value else 'false'}")
        elif value is None:
            lines.append(f"{prefix}{key}: null")
        elif isinstance(value, str):
            if "\n" in value or '"' in value or len(value) > 80:
                escaped = value.replace("'", "''")
                lines.append(f"{prefix}{key}: '{escaped}'")
            else:
                lines.append(f"{prefix}{key}: '{value}'")
        else:
            lines.append(f"{prefix}{key}: {value}")

    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(
        description="Scaffold a learning candidate record from simulation results."
    )
    parser.add_argument("--spec", required=True, help="Path to simulation_spec.json")
    parser.add_argument("--results", required=True, help="Path to results summary JSON")
    parser.add_argument("--output", required=True, help="Output YAML path")
    args = parser.parse_args()

    if not os.path.exists(args.spec):
        print(f"ERROR: spec file not found: {args.spec}", file=sys.stderr)
        sys.exit(1)

    scaffold(args.spec, args.results, args.output)


if __name__ == "__main__":
    main()
