from pathlib import Path

from scripts.parse_of_log import parse_log_text

ROOT = Path(__file__).parents[1]


def test_every_template_has_baseline_case_and_gate():
    for template in (ROOT / "templates").iterdir():
        if not template.is_dir() or not (template / "workflow.yaml").is_file():
            continue
        case = template / "case-skeleton"
        required_files = [
            "0/U",
            "0/p",
            "constant/physicalProperties",
            "system/controlDict",
            "system/fvSchemes",
            "system/fvSolution",
            "system/blockMeshDict",
            "run-baseline.sh",
            "run-optimisation.sh",
        ]
        for required in required_files:
            assert (case / required).is_file(), f"{template.name}: missing {required}"


def test_log_parser_extracts_residuals_times_and_fatal_errors():
    text = """
Time = 1
smoothSolver:  Solving for Ux, Initial residual = 0.1, Final residual = 1e-05, No Iterations 2
ExecutionTime = 0.42 s  ClockTime = 1 s
FOAM FATAL ERROR: bad dictionary
"""
    result = parse_log_text(text)
    assert result["times"] == [1.0]
    assert result["residuals"]["Ux"][-1]["final"] == 1e-5
    assert result["execution_time_seconds"] == 0.42
    assert result["fatal_errors"] == ["bad dictionary"]
