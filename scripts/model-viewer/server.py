"""
FastAPI server for the 3D model viewer.
Serves API endpoints and the interactive 3D viewer.
"""

import os
import shutil
import tempfile
import threading
import time
import uuid
from pathlib import Path

import uvicorn
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from step_parser import _model_cache, export_model_glb, get_model, parse_file

# Configuration
STATIC_DIR = Path(__file__).parent / "static"
TEMP_DIR = Path(tempfile.gettempdir()) / "model-viewer"
TEMP_DIR.mkdir(parents=True, exist_ok=True)
MAX_UPLOAD_BYTES = int(os.environ.get("MODEL_VIEWER_MAX_UPLOAD_BYTES", 200 * 1024 * 1024))
MAX_MODELS = int(os.environ.get("MODEL_VIEWER_MAX_MODELS", 8))
MODEL_TTL_SECONDS = int(os.environ.get("MODEL_VIEWER_MODEL_TTL_SECONDS", 3600))
PICK_TTL_SECONDS = int(os.environ.get("MODEL_VIEWER_PICK_TTL_SECONDS", 600))
_state_lock = threading.RLock()
_model_meta: dict[str, dict] = {}

app = FastAPI(title="3D Model Viewer for Simulation")

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https?://(?:localhost|127\.0\.0\.1)(?::\d+)?$",
    allow_methods=["*"],
    allow_headers=["*"],
)


def _safe_remove(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


def cleanup_expired(now: float | None = None) -> None:
    """Bound memory and disk state for this local-only service."""
    now = now or time.time()
    with _state_lock:
        expired = [mid for mid, meta in _model_meta.items() if now - meta["created_at"] > MODEL_TTL_SECONDS]
        survivors = sorted(_model_meta, key=lambda mid: _model_meta[mid]["created_at"])
        expired.extend(survivors[: max(0, len(survivors) - MAX_MODELS)])
        for model_id in set(expired):
            meta = _model_meta.pop(model_id, {})
            _model_cache.pop(model_id, None)
            for raw_path in meta.get("paths", []):
                _safe_remove(Path(raw_path))
        stale_picks = [
            pid
            for pid, item in _pick_results.items()
            if now - item.get("created_at", now) > PICK_TTL_SECONDS
        ]
        for pick_id in stale_picks:
            _pick_results.pop(pick_id, None)
            _pick_events.pop(pick_id, None)


def register_model_paths(model_id: str, paths: list[Path], original_name: str) -> None:
    with _state_lock:
        _model_meta[model_id] = {
            "created_at": time.time(),
            "paths": [str(path) for path in paths],
            "original_name": Path(original_name).name,
        }
    cleanup_expired()


def parse_model_safely(path: str) -> dict:
    with _state_lock:
        return parse_file(path)


@app.get("/")
async def root():
    """Serve the main viewer page."""
    viewer_html = STATIC_DIR / "viewer.html"
    if viewer_html.exists():
        return HTMLResponse(viewer_html.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Viewer not found</h1>", status_code=404)


@app.get("/pick")
async def pick_page():
    """Serve the face picker page (single selection mode)."""
    pick_html = STATIC_DIR / "pick.html"
    if pick_html.exists():
        return HTMLResponse(pick_html.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Picker not found</h1>", status_code=404)


@app.post("/api/upload")
async def upload_model(file: UploadFile = File(...)):
    """Upload and parse a STEP/STP file."""
    if not file.filename:
        raise HTTPException(400, "No file provided")

    ext = Path(file.filename).suffix.lower()
    if ext not in (".stp", ".step", ".stl", ".obj", ".glb", ".gltf", ".ply"):
        raise HTTPException(400, f"Unsupported format: {ext}. "
                                 f"Supported: .stp, .step, .stl, .obj, .glb, .gltf, .ply")

    cleanup_expired()
    safe_name = Path(file.filename.replace("\\", "/")).name
    tmp_path = TEMP_DIR / f"upload_{uuid.uuid4().hex}{ext}"
    size = 0
    try:
        with open(tmp_path, "wb") as handle:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    raise HTTPException(413, f"File exceeds {MAX_UPLOAD_BYTES} byte limit")
                handle.write(chunk)
    except Exception:
        _safe_remove(tmp_path)
        raise

    try:
        # Parse the file
        summary = parse_model_safely(str(tmp_path))
        model_id = summary["model_id"]

        # Export GLB
        glb_path = export_model_glb(model_id, str(TEMP_DIR))

        # Copy GLB to static dir for serving
        static_glb = STATIC_DIR / f"{model_id}.glb"
        shutil.copy2(glb_path, static_glb)
        # Also copy face group map JSON
        fgmap_path = glb_path.replace(".glb", "_fgmap.json")
        if os.path.exists(fgmap_path):
            shutil.copy2(fgmap_path, STATIC_DIR / f"{model_id}_fgmap.json")

        paths = [tmp_path, Path(glb_path), static_glb, STATIC_DIR / f"{model_id}_fgmap.json"]
        register_model_paths(model_id, paths, safe_name)

        return {
            "success": True,
            "model_id": model_id,
            "summary": summary,
            "glb_url": f"/static/{model_id}.glb",
        }
    except Exception as e:
        _safe_remove(tmp_path)
        raise HTTPException(500, f"Failed to parse file: {e}")


@app.get("/api/model/{model_id}")
async def get_model_info(model_id: str):
    """Get parsed model summary."""
    model = get_model(model_id)
    if model is None:
        raise HTTPException(404, f"Model {model_id} not found")
    return model.get_summary()


@app.get("/api/model/{model_id}/faces")
async def get_model_faces(model_id: str):
    """Get face groups for a model."""
    model = get_model(model_id)
    if model is None:
        raise HTTPException(404, f"Model {model_id} not found")
    return {
        "model_id": model_id,
        "face_groups": [fg.to_dict() for fg in model.face_groups],
    }


@app.post("/api/model/{model_id}/boundaries")
async def set_boundaries(model_id: str, data: dict):
    """
    Set boundary conditions for face groups.

    Expected body:
    {
        "boundaries": {
            "0": {"type": "inlet", "label": "Air Inlet"},
            "3": {"type": "outlet", "label": "Hot Air Outlet"},
            "5": {"type": "heat_source", "label": "CPU"},
            "7": {"type": "wall", "label": "Chassis Wall"}
        }
    }

    Valid types: inlet, outlet, wall, heat_source, symmetry, open, interior
    """
    model = get_model(model_id)
    if model is None:
        raise HTTPException(404, f"Model {model_id} not found")

    boundaries = data.get("boundaries", {})
    valid_types = {"inlet", "outlet", "wall", "heat_source", "symmetry", "open", "interior"}

    result = {}
    for face_id_str, bnd in boundaries.items():
        face_id = int(face_id_str)
        bnd_type = bnd.get("type", "wall")
        if bnd_type not in valid_types:
            raise HTTPException(400, f"Invalid boundary type: {bnd_type}. "
                                     f"Valid: {valid_types}")

        # Find the face group
        fg = next((f for f in model.face_groups if f.face_id == face_id), None)
        if fg is None:
            raise HTTPException(404, f"Face group {face_id} not found")

        result[face_id] = {
            "face_id": face_id,
            "type": bnd_type,
            "label": bnd.get("label", f"{bnd_type}_{face_id}"),
            "area": fg.area,
            "centroid": fg.centroid,
            "normal": fg.normal,
            "face_type": fg.face_type,
        }

    return {
        "success": True,
        "model_id": model_id,
        "boundaries": result,
    }


@app.get("/api/model/{model_id}/export")
async def export_boundaries(model_id: str):
    """
    Export the model with boundary assignments as a simulation-ready config.
    """
    model = get_model(model_id)
    if model is None:
        raise HTTPException(404, f"Model {model_id} not found")

    # Build COMSOL-compatible boundary config
    face_groups_info = []
    for fg in model.face_groups:
        face_groups_info.append({
            "face_id": fg.face_id,
            "area": round(fg.area, 6),
            "centroid": [round(c, 4) for c in fg.centroid],
            "normal": [round(n, 4) for n in fg.normal],
            "face_type": fg.face_type,
            "num_triangles": int(fg.triangle_count),
        })

    return {
        "model_id": model_id,
        "file_name": Path(model.file_path).name,
        "face_groups": face_groups_info,
        "total_groups": len(face_groups_info),
        "total_area": round(sum(fg["area"] for fg in face_groups_info), 4),
    }


@app.delete("/api/model/{model_id}")
async def delete_model(model_id: str):
    """Remove a model from cache and cleanup files."""
    with _state_lock:
        _model_cache.pop(model_id, None)
        meta = _model_meta.pop(model_id, {})
    for raw_path in meta.get("paths", []):
        _safe_remove(Path(raw_path))
    _safe_remove(STATIC_DIR / f"{model_id}.glb")
    _safe_remove(STATIC_DIR / f"{model_id}_fgmap.json")
    return {"success": True}


@app.get("/api/models")
async def list_models():
    """List all loaded models."""
    cleanup_expired()
    models = []
    for mid, model in _model_cache.items():
        models.append({
            "model_id": mid,
            "file_name": Path(model.file_path).name if hasattr(model, 'file_path') else "unknown",
            "vertex_count": len(model._mesh.vertices),
            "face_count": len(model._mesh.faces),
            "face_groups": len(model.face_groups),
            "extents": model._mesh.extents.tolist() if hasattr(model._mesh, 'extents') else None,
        })
    return {"models": models, "count": len(models)}


# ── Pick Mode API (for agent-callable face selection) ──

_pick_results: dict[str, dict] = {}
_pick_events: dict[str, threading.Event] = {}

class PickFaceItem(BaseModel):
    face_id: int
    face_data: dict

class PickResult(BaseModel):
    pick_id: str
    faces: list[PickFaceItem]  # multiple faces

@app.post("/api/pick-result")
async def receive_pick_result(data: PickResult):
    """Receive face pick results from the pick-mode viewer (multi-select)."""
    with _state_lock:
        _pick_results[data.pick_id] = {
            "faces": [{"face_id": f.face_id, "face_data": f.face_data} for f in data.faces],
            "count": len(data.faces),
            "created_at": time.time(),
        }
        if data.pick_id in _pick_events:
            _pick_events[data.pick_id].set()
    return {"status": "received"}

@app.get("/api/pick-result/{pick_id}")
async def get_pick_result(pick_id: str):
    """Poll for a pick result."""
    cleanup_expired()
    with _state_lock:
        if pick_id in _pick_results:
            result = _pick_results.pop(pick_id)
            _pick_events.pop(pick_id, None)
            return {"ready": True, "result": result}
    return {"ready": False}


# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def main():
    """Launch the server."""
    import argparse
    parser = argparse.ArgumentParser(description="3D Model Viewer Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8765, help="Port to listen on")
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print("  3D Model Viewer for Simulation")
    print(f"  Open browser: http://{args.host}:{args.port}")
    print(f"{'='*60}\n")

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
