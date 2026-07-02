import importlib
from pathlib import Path

import numpy as np
import trimesh
from fastapi.testclient import TestClient

MV = Path(__file__).parents[1] / "scripts/model-viewer"


def load_modules(monkeypatch, tmp_path):
    monkeypatch.syspath_prepend(str(MV))
    server = importlib.import_module("server")
    server.TEMP_DIR = tmp_path / "temp"
    server.STATIC_DIR = tmp_path / "static"
    server.TEMP_DIR.mkdir()
    server.STATIC_DIR.mkdir()
    return server


def test_upload_rejects_large_files(monkeypatch, tmp_path):
    server = load_modules(monkeypatch, tmp_path)
    monkeypatch.setattr(server, "MAX_UPLOAD_BYTES", 4)
    with TestClient(server.app) as client:
        files = {"file": ("box.stl", b"12345", "application/octet-stream")}
        response = client.post("/api/upload", files=files)
    assert response.status_code == 413


def test_upload_filename_is_sanitized(monkeypatch, tmp_path):
    server = load_modules(monkeypatch, tmp_path)
    seen = {}

    def fake_parse(path):
        seen["path"] = Path(path)
        return {"model_id": "abc", "file_name": "box.stl", "face_groups": []}

    monkeypatch.setattr(server, "parse_file", fake_parse)
    def fake_export(*_):
        path = server.TEMP_DIR / "abc.glb"
        path.write_bytes(b"glb")
        return str(path)

    monkeypatch.setattr(server, "export_model_glb", fake_export)
    with TestClient(server.app) as client:
        files = {"file": ("../../box.stl", b"solid", "application/octet-stream")}
        response = client.post("/api/upload", files=files)
    assert response.status_code == 200
    assert seen["path"].parent == server.TEMP_DIR
    assert ".." not in seen["path"].name


def test_cors_allows_localhost_ports_but_not_external_origins(monkeypatch, tmp_path):
    server = load_modules(monkeypatch, tmp_path)
    with TestClient(server.app) as client:
        local = client.options(
            "/api/models",
            headers={
                "Origin": "http://localhost:9999",
                "Access-Control-Request-Method": "GET",
            },
        )
        external = client.options(
            "/api/models",
            headers={
                "Origin": "https://attacker.example",
                "Access-Control-Request-Method": "GET",
            },
        )
    assert local.headers["access-control-allow-origin"] == "http://localhost:9999"
    assert "access-control-allow-origin" not in external.headers


def test_cleanup_evicts_expired_models(monkeypatch, tmp_path):
    server = load_modules(monkeypatch, tmp_path)
    generated = tmp_path / "generated.glb"
    generated.write_bytes(b"data")
    server._model_cache["old"] = object()
    server._model_meta["old"] = {"created_at": 1.0, "paths": [str(generated)]}
    server.cleanup_expired(now=server.MODEL_TTL_SECONDS + 2.0)
    assert "old" not in server._model_cache
    assert not generated.exists()


def test_multibody_face_groups_reference_combined_mesh():
    import sys
    sys.path.insert(0, str(MV))
    from step_parser import FaceGroup, StepModel

    a = trimesh.creation.box()
    b = trimesh.creation.box()
    combined = trimesh.util.concatenate([a, b])
    model = StepModel.__new__(StepModel)
    model._mesh = combined
    groups = [
        FaceGroup(0, np.arange(0, len(a.faces)), combined),
        FaceGroup(1, np.arange(len(a.faces), len(a.faces) + len(b.faces)), combined),
    ]
    assert sum(group.triangle_count for group in groups) == len(combined.faces)
    assert all(group.area > 0 for group in groups)


def test_scene_loader_splits_each_body_at_sharp_edges(monkeypatch):
    import sys
    sys.path.insert(0, str(MV))
    from step_parser import StepModel

    scene = trimesh.Scene()
    scene.add_geometry(trimesh.creation.box(), geom_name="a")
    scene.add_geometry(trimesh.creation.box(), geom_name="b")
    monkeypatch.setattr(StepModel, "_load_step", lambda self: scene)
    model = StepModel("synthetic.step")
    assert len(model.face_groups) == 12
    assert sum(group.triangle_count for group in model.face_groups) == len(model._mesh.faces)


def test_viewer_uses_local_threejs_and_single_pass_highlighting():
    html = (MV / "static/viewer.html").read_text(encoding="utf-8")
    assert "https://unpkg.com" not in html
    assert "function applyCompositeHighlights" in html
    assert (MV / "static/vendor/three.module.js").is_file()
