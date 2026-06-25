"""
FastAPI server for the 3D model viewer.
Serves API endpoints and the interactive 3D viewer.
"""

import json
import os
import shutil
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from step_parser import parse_file, export_model_glb, get_model, _model_cache

# Configuration
STATIC_DIR = Path(__file__).parent / "static"
TEMP_DIR = Path(tempfile.gettempdir()) / "model-viewer"
TEMP_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="3D Model Viewer for Simulation")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


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

    # Save uploaded file
    tmp_path = TEMP_DIR / f"upload_{file.filename}"
    with open(tmp_path, "wb") as f:
        content = await file.read()
        f.write(content)

    try:
        # Parse the file
        summary = parse_file(str(tmp_path))
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

        return {
            "success": True,
            "model_id": model_id,
            "summary": summary,
            "glb_url": f"/static/{model_id}.glb",
        }
    except Exception as e:
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
    if model_id in _model_cache:
        del _model_cache[model_id]
    # Cleanup GLB
    glb_file = STATIC_DIR / f"{model_id}.glb"
    if glb_file.exists():
        glb_file.unlink()
    return {"success": True}


@app.get("/api/models")
async def list_models():
    """List all loaded models."""
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
import threading
from pydantic import BaseModel

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
    _pick_results[data.pick_id] = {
        "faces": [{"face_id": f.face_id, "face_data": f.face_data} for f in data.faces],
        "count": len(data.faces),
    }
    if data.pick_id in _pick_events:
        _pick_events[data.pick_id].set()
    return {"status": "received"}

@app.get("/api/pick-result/{pick_id}")
async def get_pick_result(pick_id: str):
    """Poll for a pick result."""
    if pick_id in _pick_results:
        return {"ready": True, "result": _pick_results[pick_id]}
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
    print(f"  3D Model Viewer for Simulation")
    print(f"  Open browser: http://{args.host}:{args.port}")
    print(f"{'='*60}\n")

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
