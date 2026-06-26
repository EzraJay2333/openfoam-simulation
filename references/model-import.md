# Model Import and Interactive Boundary Condition Selection

## Purpose

When the user has a CAD model file (STEP, STL, OBJ, etc.), use the integrated 3D model viewer to:
1. Parse and display the 3D geometry
2. Let the user interactively select faces and assign boundary condition types
3. Export the face-to-BC mapping for OpenFOAM case setup

This replaces or supplements the text-based geometry description in Step 3 (Structured Intake).

## Two Interaction Modes

### Mode A: Agent-Driven Pick (Recommended)

The agent calls `pick_face()` to pop up a targeted selection window for each boundary type:

```python
# Agent calls this for each boundary:
from pick_face import pick_face

# 1. Ask user to pick inlet faces
inlet = pick_face("model.stp", label="请点击选择【入口面】(Inlet)")

# 2. Ask user to pick outlet faces
outlet = pick_face("model.stp", label="请点击选择【出口面】(Outlet)")

# 3. Ask user to pick wall faces
walls = pick_face("model.stp", label="请点击选择【壁面】(Wall)")
```

Each call:
1. Opens a full-screen 3D picker in the browser
2. User multi-selects faces by clicking (toggle on/off)
3. User clicks "确认" (Confirm) to submit, or "取消" (Cancel) to skip
4. Window closes → `pick_face()` returns the structured face data
5. Agent processes the result and moves to the next boundary

Return format:
```json
{
  "model_id": "abc123",
  "file_name": "model.step",
  "count": 3,
  "faces": [
    {
      "face_id": 0,
      "area": 0.0025,
      "centroid": [0.1, 0.2, 0.3],
      "normal": [0.0, 0.0, 1.0],
      "face_type": "planar",
      "triangle_count": 128
    }
  ]
}
```

### Mode B: Full Viewer (Self-Service)

User opens the complete viewer at `http://127.0.0.1:8765` to explore the model and assign all BCs in one session:

1. Upload model via drag-and-drop
2. Explore in 3D (rotate/zoom/pan)
3. Click faces to select; right panel to assign BC types
4. Export JSON configuration when done

Use this when the user wants to assign all boundaries at once without agent prompting.

## Supported Formats

| Format | Extension | Notes |
|--------|----------|-------|
| STEP | `.stp`, `.step` | Best for CAD — preserves face groups from original CAD faces |
| STL | `.stl` | Triangle mesh — faces grouped by normal+adjacency clustering |
| OBJ | `.obj` | Wavefront — supports multiple objects |
| GLTF/GLB | `.glb`, `.gltf` | Modern 3D format |
| PLY | `.ply` | Stanford format |

## Dependencies

### Windows
```bash
pip install trimesh fastapi uvicorn numpy cascadio
```

### Linux / WSL
```bash
sudo apt install gmsh python3-pip
pip install trimesh fastapi uvicorn numpy gmsh
```

### Verify
```bash
python -c "import trimesh, fastapi, uvicorn; print('OK')"
```

## How to Launch

### Step 1: Start the Server (if not running)

```bash
cd <skill-path>/scripts/model-viewer
python app.py --port 8765 --no-browser
```

The server auto-detects if already running and reuses it.

### Step 2: Agent Opens Pick Windows

For each boundary type needed, call `pick_face()` from `pick_face.py`:

```python
from pick_face import pick_face

# Inlet
inlet_faces = pick_face(model_path, label="请点击选择【入口面】— 流体进入的面")

# Outlet
outlet_faces = pick_face(model_path, label="请点击选择【出口面】— 流体流出的面")

# Walls (optional — remaining unassigned faces default to wall)
wall_faces = pick_face(model_path, label="请点击选择【壁面】— 固定固体壁面")
```

Each call blocks until the user confirms or cancels (5-minute timeout).

If user cancels (clicks "取消" or presses Esc), the function returns `{"count": 0, "faces": []}`.

### Step 3: User Interaction

The pick window shows:
- Full-screen 3D view with the model
- Top bar with the prompt (e.g., "请点击选择【入口面】")
- Click any face to select (green highlight), click again to deselect
- Hover shows face ID, area, and face type
- "清除" clears all selections; "确认" submits; "取消" closes
- Keyboard: Enter = confirm, Esc = cancel

### Step 4: Convert to OpenFOAM Boundary Conditions

Map the exported selections to OpenFOAM patch types:

| Viewer BC Type | OpenFOAM Patch Type | Typical BC Fields |
|---------------|-------------------|-------------------|
| `inlet` | `patch` | U: `fixedValue`, p: `zeroGradient`, T: `fixedValue` |
| `outlet` | `patch` | U: `zeroGradient`, p: `fixedValue` (0 gauge), T: `zeroGradient` |
| `wall` | `wall` | U: `noSlip`, p: `zeroGradient`, T: `zeroGradient` or `fixedValue` |
| `heat_source` | `wall` | U: `noSlip`, p: `zeroGradient`, T: `fixedGradient` or `externalWallHeatFluxTemperature` |
| `symmetry` | `symmetryPlane` or `symmetry` | All: `symmetryPlane` |
| `open` | `patch` | U: `inletOutlet` or `pressureInletOutletVelocity`, p: `totalPressure` |

For faces not assigned a BC type, ask the user — these cannot default to any specific type. Common default: unassigned external faces → `wall`.

## Integration with Geometry Intake

After interactive selection, populate the intake-schema geometry section:

```yaml
geometry:
  source: "cad_model"
  model_file: "heat_sink.step"
  bc_selections:
    inlet:
      - face_id: 0
        area_m2: 0.0025
        normal: [0.0, 0.0, 1.0]
        centroid: [0.1, 0.2, 0.0]
    outlet:
      - face_id: 3
        area_m2: 0.0018
        normal: [0.0, 0.0, -1.0]
    walls:
      - face_id: 1
      - face_id: 2
      - face_id: 4
  unassigned: []
  mesh_strategy:
    generator: "snappyHexMesh"
    surface_file: "heat_sink.stl"
```

## Going Back to Text Description

If the user can't or doesn't want to use the interactive tool:
- Proceed with standard text-based geometry intake (intake-schema.md section 2)
- Ask the user to describe the geometry and boundary locations in words
- Label all face assignments as `[ASSUMED from description]`

## Troubleshooting

| Issue | Solution |
|-------|---------|
| STEP file fails to load | Install cascadio (Windows) or gmsh (Linux/WSL): `pip install gmsh` |
| "No module named 'trimesh'" | `pip install trimesh` |
| Port already in use | Server auto-reuses existing instance. Or: `python app.py --port 8766` |
| No faces detected | Mesh may be too coarse or non-manifold. Try `app.py --gradio` for simpler interface |
| Browser doesn't open in WSL | The script uses `webbrowser.open()`. If it fails, manually open `http://localhost:8765` |
| Pick window shows wrong model | Ensure the model was uploaded/parsed before calling `pick_face()`. The model ID must match. |
| Pick result is empty (count=0) | User clicked "取消". Re-open the picker with a clearer prompt. |
| Highlight looks wrong | Refresh the page. The face-group map (fgmap) must match the GLB. Re-upload if needed. |
