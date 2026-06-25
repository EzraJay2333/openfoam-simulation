# Model Import and Interactive Boundary Condition Selection

## Purpose

When the user has a CAD model file (STEP, STL, OBJ, etc.), use the integrated 3D model viewer to:
1. Parse and display the 3D geometry
2. Let the user interactively select faces and assign boundary condition types
3. Export the face-to-BC mapping for OpenFOAM case setup

This replaces or supplements the text-based geometry description in Step 3 (Structured Intake).

## Supported Formats

| Format | Extension | Notes |
|--------|----------|-------|
| STEP | `.stp`, `.step` | Best for CAD — preserves face groups from original CAD faces |
| STL | `.stl` | Triangle mesh — faces are grouped by normal clustering |
| OBJ | `.obj` | Wavefront — supports multiple objects |
| GLTF/GLB | `.gltf`, `.glb` | Modern 3D format |
| PLY | `.ply` | Stanford format |
| 3MF | `.3mf` | 3D Manufacturing Format |
| DAE | `.dae` | COLLADA |

## When to Use

Enter this workflow when:
- User says "I have an STL/STEP/STP file", "here's my model", "import this geometry"
- User drags or shares a CAD file path
- User wants to visually assign boundary conditions on the geometry

## How to Launch

### Step 1: Check Dependencies

```bash
# Check required Python packages
python3 -c "import trimesh, fastapi, uvicorn; print('OK')" 2>&1

# If missing, install:
pip install trimesh fastapi uvicorn gradio numpy
```

For STEP file support on **Windows**: `pip install cascadio` (auto-selected by trimesh)
For STEP file support on **Linux/WSL**: `pip install gmsh` or `sudo apt install gmsh`

### Step 2: Start the Server

```bash
cd <skill-path>/scripts/model-viewer
python app.py --port 8765 --no-browser
```

**Important notes:**
- The server runs on `http://127.0.0.1:8765` by default
- Use `--no-browser` when running in a terminal-only environment — tell the user to open the URL in their browser
- The server stays running until the user closes it
- The `--port` flag changes the port if 8765 is occupied

### Step 3: User Interacts with the 3D Viewer

Guide the user through these steps:

1. **Open browser** at `http://127.0.0.1:8765`
2. **Upload model** — drag & drop the CAD file onto the page, or click "选择文件"
3. **Explore model** — rotate (left-drag), zoom (scroll), pan (right-drag)
4. **Select faces** — click a face to select it (highlighted in color)
   - `Shift + Click` to add/remove faces from selection
   - Hover over a face to see its area and normal vector
5. **Assign boundary type** — click one of the BC buttons:
   - 🔵 **Inlet** (入口) — flow inlet faces
   - 🔴 **Outlet** (出口) — flow outlet faces
   - ⚪ **Wall** (壁面) — solid wall faces
   - 🟠 **Heat Source** (热源) — faces with heat flux
   - 🟢 **Symmetry** (对称面) — symmetry planes
   - 🟡 **Open** (开放边界) — far-field open boundary
6. **Export** — click "导出配置" to download `face_selections.json`

### Step 4: Read the Export

After the user exports, the JSON file contains:

```json
{
  "file_name": "heat_sink.step",
  "total_faces": 24,
  "face_groups": [
    {
      "id": 0,
      "area_m2": 0.0025,
      "normal": [0.0, 0.0, 1.0],
      "type": "planar",
      "triangle_count": 128
    }
  ],
  "bc_selections": {
    "0": {"label": "inlet", "type": "inlet", "color": "#4488ff"},
    "1": {"label": "outlet", "type": "outlet", "color": "#ff4444"},
    "5": {"label": "heat_source", "type": "heat_source", "color": "#ff8800"}
  },
  "unassigned": ["2", "3", "4", "6"]
}
```

### Step 5: Convert to OpenFOAM Boundary Conditions

Map the exported selections to OpenFOAM patch types:

| Viewer BC Type | OpenFOAM Patch Type | Typical BC Fields |
|---------------|-------------------|-------------------|
| `inlet` | `patch` | U: `fixedValue`, p: `zeroGradient`, T: `fixedValue` |
| `outlet` | `patch` | U: `zeroGradient`, p: `fixedValue` (0 gauge), T: `zeroGradient` |
| `wall` | `wall` | U: `noSlip`, p: `zeroGradient`, T: `zeroGradient` or `fixedValue` |
| `heat_source` | `wall` | U: `noSlip`, p: `zeroGradient`, T: `fixedGradient` or `externalWallHeatFluxTemperature` |
| `symmetry` | `symmetryPlane` or `symmetry` | All: `symmetryPlane` |
| `open` | `patch` | U: `inletOutlet` or `pressureInletOutletVelocity`, p: `totalPressure` |

For faces not assigned a BC type, ask the user — these cannot default to any specific type.

## Integration with Geometry Intake

After the interactive session, populate the intake-schema geometry section:

```yaml
geometry:
  source: "cad_model"
  model_file: "heat_sink.step"
  bc_selections_file: "face_selections.json"
  model_viewer_url: "http://127.0.0.1:8765"
  boundary_conditions:  # auto-populated from face_selections.json
    - patch: "face_group_0"
      area: 0.0025
      normal: [0.0, 0.0, 1.0]
      bc_type: "inlet"
      openfoam_patch: "patch"
    - patch: "face_group_1"
      area: 0.0025
      normal: [0.0, 0.0, -1.0]
      bc_type: "outlet"
      openfoam_patch: "patch"
  unassigned_warning: "Faces 2,3,4,6 need BC type assignment"
  mesh_strategy:
    generator: "snappyHexMesh"  # snappyHexMesh is the default for STL/STP input
    surface_file: "heat_sink.stl"  # exported from the model
```

## Going Back to Text Description

If the user can't or doesn't want to use the interactive tool:
- Proceed with standard text-based geometry intake (intake-schema.md section 2)
- Ask the user to describe the geometry and boundary locations in words
- Label all face assignments as `[ASSUMED from description]`

## Troubleshooting

| Issue | Solution |
|-------|---------|
| STEP file fails to load | Try converting to STL first (use FreeCAD or online converter). STL is more universally supported. |
| "No module named 'trimesh'" | `pip install trimesh` |
| Port already in use | `python app.py --port 8766` (try another port) |
| No faces detected | Mesh may be too coarse or non-manifold. Try `python app.py --gradio` for a simpler interface. |
| Server doesn't start on Windows | Use `python app.py` directly (not `python3`). Windows Python is `python`. |
| Can't open browser in WSL | Use `--no-browser`, then open the URL in your Windows browser manually. WSL servers are accessible at `http://localhost:8765`. |
