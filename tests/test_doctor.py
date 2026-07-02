from pathlib import Path

from scripts.doctor import inspect_openfoam_root, run_repository_checks

ROOT = Path(__file__).parents[1]


def test_repository_doctor_reports_structured_success():
    report = run_repository_checks(ROOT)
    assert report["schema_version"] == "1.0"
    assert report["ok"] is True
    assert all(check["status"] == "pass" for check in report["checks"])


def test_openfoam_inspection_distinguishes_binary_and_source(tmp_path):
    root = tmp_path / "OpenFOAM-13"
    (root / "platforms/linux64/bin").mkdir(parents=True)
    (root / "applications/legacy/incompressible/adjointShapeOptimisationFoam").mkdir(parents=True)
    (root / "platforms/linux64/bin/simpleFoam").write_text("", encoding="utf-8")
    report = inspect_openfoam_root(root, appbin=root / "platforms/linux64/bin")
    assert report["version"] == "13"
    assert report["applications"]["simpleFoam"]["availability"] == "binary"
    assert report["applications"]["adjointShapeOptimisationFoam"]["availability"] == "source_only"


def test_openfoam_inspection_detects_foundation_wrappers_and_modules(tmp_path):
    root = tmp_path / "OpenFOAM-13"
    appbin = root / "platforms/linux64/bin"
    appbin.mkdir(parents=True)
    (root / "bin").mkdir()
    (root / "bin/chtMultiRegionFoam").write_text("#!/bin/sh\n", encoding="utf-8")
    (root / "applications/modules/incompressibleFluid").mkdir(parents=True)
    (root / "applications/solvers/foamMultiRun").mkdir(parents=True)
    (appbin / "foamMultiRun").write_text("", encoding="utf-8")

    report = inspect_openfoam_root(root, appbin=appbin)

    assert report["applications"]["chtMultiRegionFoam"]["availability"] == "wrapper"
    assert report["applications"]["chtMultiRegionFoam"]["wrapper"] == str(
        root / "bin/chtMultiRegionFoam"
    )
    assert report["applications"]["incompressibleFluid"]["availability"] == "module_source"
    assert report["applications"]["foamMultiRun"]["availability"] == "binary"
