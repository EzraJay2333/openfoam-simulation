import json
import re
from pathlib import Path

import jsonschema
import yaml

ROOT = Path(__file__).parents[1]


def test_all_structured_files_parse_and_validate():
    schemas = {
        p.stem.replace(".schema", ""): json.loads(p.read_text(encoding="utf-8"))
        for p in (ROOT / "schemas").glob("*.schema.json")
    }
    assert {"simulation-spec", "workflow", "learning-record", "solver-registry"} <= schemas.keys()

    json.loads((ROOT / "evals/evals.json").read_text(encoding="utf-8"))
    yaml.safe_load((ROOT / "registry/problem-types.yaml").read_text(encoding="utf-8"))
    solver_registry = yaml.safe_load((ROOT / "registry/solvers.yaml").read_text(encoding="utf-8"))
    jsonschema.validate(solver_registry, schemas["solver-registry"])

    for path in (ROOT / "templates").glob("*/workflow.yaml"):
        workflow = yaml.safe_load(path.read_text(encoding="utf-8"))
        jsonschema.validate(workflow, schemas["workflow"])
        assert workflow["workflow"]["status"] == "experimental"


def test_registry_uses_canonical_snake_case_ids():
    text = (ROOT / "registry/problem-types.yaml").read_text(encoding="utf-8")
    forbidden_patterns = [
        r"phases:\s*single-phase",
        r"optimisation_family:\s*density-topology",
        r"objectives:\s*\[[^\]]*pressure-loss",
        r"design_variables:\s*\[[^\]]*boundary-displacement",
    ]
    assert not [pattern for pattern in forbidden_patterns if re.search(pattern, text)]


def test_solver_records_and_workflow_fingerprints_emit_canonical_ids():
    registry = yaml.safe_load((ROOT / "registry/solvers.yaml").read_text(encoding="utf-8"))
    canonical_fields = {
        "distribution",
        "physics",
        "geometry",
        "objectives",
        "design_variables",
        "optimisation_support",
    }
    for solver_name, record in registry["solvers"].items():
        for field in canonical_fields & record.keys():
            values = record[field] if isinstance(record[field], list) else [record[field]]
            for value in values:
                assert not re.search(r"[-.]", value), f"{solver_name}.{field}: {value}"

    for path in (ROOT / "templates").glob("*/workflow.yaml"):
        fingerprint = yaml.safe_load(path.read_text(encoding="utf-8"))["workflow"][
            "problem_fingerprint"
        ]
        for field, raw_values in fingerprint.items():
            values = raw_values if isinstance(raw_values, list) else [raw_values]
            for value in values:
                if isinstance(value, str):
                    assert "-" not in value, f"{path.name}:{field}: {value}"


def test_documented_repository_references_exist():
    required = [
        ROOT / "scripts/parse_of_log.py",
        ROOT / "scripts/doctor.py",
        ROOT / "references/error-diagnostics.md",
        ROOT / "references/geometry-physics-vv.md",
    ]
    required.extend(
        path / "case-skeleton"
        for path in (ROOT / "templates").iterdir()
        if path.is_dir() and (path / "workflow.yaml").is_file()
    )
    assert not [str(path.relative_to(ROOT)) for path in required if not path.exists()]


def test_solver_registry_does_not_overstate_topology_capabilities():
    registry = yaml.safe_load((ROOT / "registry/solvers.yaml").read_text(encoding="utf-8"))

    foundation_legacy = registry["solvers"]["adjointShapeOptimisationFoam"]
    assert foundation_legacy["optimisation_support"] == "legacy_blockage_topology"
    assert foundation_legacy["design_variables"] == ["blockage_field"]
    assert foundation_legacy["objectives"] == ["pressure_loss"]
    assert "heat_transfer" not in foundation_legacy["objectives"]
    assert "multi_objective" not in foundation_legacy["objectives"]

    opencfd_modern = registry["solvers"]["adjointOptimisationFoam"]
    assert opencfd_modern["first_version"] == "1906"
    assert opencfd_modern["topology_first_version"] == "2312"
    assert opencfd_modern["physics"] == ["single_phase", "isothermal"]

    cht = registry["solvers"]["chtMultiRegionFoam"]
    assert cht["optimisation_support"] == "external_only"


def test_solver_guidance_has_no_unverified_thermal_adjoint_claims():
    text = (ROOT / "references/solver-selection.md").read_text(encoding="utf-8")
    assert "adjointOptimisationFoam` with thermal objectives" not in text
    assert "supports topology, shape, and thermal objectives" not in text
    assert "Thermal/CHT adjoint | Not natively available | Unverified" in text


def test_native_topology_template_is_isothermal_only():
    workflow = yaml.safe_load(
        (ROOT / "templates/porous-density-topology/workflow.yaml").read_text(encoding="utf-8")
    )["workflow"]
    fingerprint = workflow["problem_fingerprint"]
    assert fingerprint["physics"] == ["single_phase", "isothermal"]
    assert "heat_transfer" not in fingerprint["objectives"]
    assert "conjugate_heat_transfer" not in fingerprint["physics"]
    assert workflow["support_level"] == "native"


def test_pressure_loss_template_uses_version_qualified_solver_names():
    workflow = yaml.safe_load(
        (ROOT / "templates/internal-flow-pressure-loss/workflow.yaml").read_text(encoding="utf-8")
    )["workflow"]
    prerequisites = "\n".join(workflow["prerequisites"])
    assert "OpenCFD v2312+" in prerequisites
    assert "Foundation 13 adjointShapeOptimisationFoam" in prerequisites
    assert "adjointShapeOptimizationFoam (Foundation)" not in prerequisites


def test_local_topology_setup_tutorial_and_capability_report_contract_exist():
    tutorial = ROOT / "references/local-topology-setup-cn.md"
    assert tutorial.is_file()
    tutorial_text = tutorial.read_text(encoding="utf-8")
    for required in (
        "Foundation 13",
        "OpenCFD v2512",
        "SciPy",
        "DAKOTA",
        "pyOptSparse",
        "不要混用",
    ):
        assert required in tutorial_text

    skill_text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    for field in (
        "required_capabilities",
        "installed_match",
        "missing_capabilities",
        "acquisition_branch",
        "evidence",
        "recommended_next_action",
    ):
        assert field in skill_text
