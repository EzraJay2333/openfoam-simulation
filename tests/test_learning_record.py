import json
from pathlib import Path

import jsonschema
import yaml

from scripts.scaffold_learning_record import build_record, write_record

ROOT = Path(__file__).parents[1]


def sample_spec():
    return {
        "schema_version": "2.0",
        "project_name": "Pipe / Bend",
        "environment": {"of_identity": {"distribution_family": "openfoam_org", "version": "13"}},
        "geometry": {"dimensions": {"type": "3d"}},
        "flow_regime": {"time_behavior": "steady", "compressibility": "incompressible"},
        "physical_models": {"turbulence": {"model": "laminar"}, "thermal": {"enabled": False}},
        "optimisation": {
            "type": "shape",
            "support_level": "experimental",
            "objectives": [{"name": "pressure_loss"}],
            "constraints": [{"name": "volume"}],
        },
    }


def test_learning_record_round_trips_and_validates(tmp_path):
    record = build_record(sample_spec(), {"solver": "simpleFoam", "commands": ["simpleFoam"]})
    output = tmp_path / "record.yaml"
    write_record(record, output)
    loaded = yaml.safe_load(output.read_text(encoding="utf-8"))
    schema = json.loads((ROOT / "schemas/learning-record.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(loaded, schema)
    assert loaded["status"] == "experimental"
    assert loaded["problem_fingerprint"]["objectives"] == ["pressure_loss"]
