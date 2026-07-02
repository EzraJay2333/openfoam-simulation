# Validation and Convergence

## Purpose

This reference defines the validation gates used in Steps 9 and 10. Each gate must pass before the next execution stage can begin.

## Stage 9a: Dictionary Syntax Check

### Procedure

```bash
# Expand and validate every dictionary in system/
for d in system/*; do
    foamDictionary -expand "$d" > /dev/null 2>&1
    if [ $? -ne 0 ]; then
        echo "FAIL: $d has syntax errors"
        foamDictionary -expand "$d" 2>&1
    else
        echo "OK: $d"
    fi
done

# Validate boundary condition consistency
foamDictionary -entry boundaryField 0/U 2>&1
foamDictionary -entry boundaryField 0/p 2>&1
```

### Gate conditions
- All dictionaries parse without error
- Boundary condition entries reference patch names that exist in `constant/polyMesh/boundary`
- No `#include` directives fail to resolve
- Dimension sets are consistent (e.g., `[0 2 -2 0 0 0 0]` for kinematic pressure `p_rgh / rho`)

## Stage 9b: Mesh Generation and Quality

### Procedure

```bash
# Generate mesh
blockMesh 2>&1 | tee log.blockMesh
# Or: snappyHexMesh -overwrite 2>&1 | tee log.snappyHexMesh

# Quality check
checkMesh 2>&1 | tee log.checkMesh
```

### Gate conditions

| Metric | Laminar Threshold | RANS Threshold | LES Threshold |
|--------|------------------|----------------|---------------|
| Max non-orthogonality | < 70 | < 65 | < 60 |
| Max skewness | < 4 | < 3 | < 2 |
| Max aspect ratio | < 1000 | < 100 | < 50 |
| Min cell volume | > 0 | > 0 | > 0 |
| Mesh check result | Ok | Ok | Ok |
| Cell count | Within 50% of target | Within 50% of target | Within 50% of target |

If any threshold is violated:
- Report the metric, its value, and the threshold
- Suggest corrective action (add layers, reduce expansion ratio, add refinement regions)
- Do not proceed until mesh qualifies or user overrides (with explicit warning)

## Stage 9c: Bounded Smoke Run

### Purpose
A minimal-cost run to detect gross errors before committing to a full simulation: wrong boundary conditions, solver crashes, immediate divergence.

### Procedure

```bash
# Coarsen the mesh and/or set short endTime
# Run a few iterations
<application> 2>&1 | tee log.smoke
```

### Gate conditions
- Solver starts and completes at least 10 iterations without crash
- No `Floating point exception`, `segmentation fault`, or `foamFatalError`
- Continuity error (first few iterations): decreasing or bounded
- Initial residuals: decreasing after first few iterations
- Mass conservation: check with `postProcess -func "flowRatePatch"` — inlet and outlet flow rates should match within 5%

## Stage 9d: Baseline Primal Simulation

### Procedure

Run the primal solver on the initial design to establish a baseline.

```bash
<application> > log.primal 2>&1
```

### Gate Conditions

#### Residual Convergence

Extract from log using `scripts/parse_of_log.py` or `foamLog`:

```bash
foamLog log.primal
# Check logs/p_0, logs/Ux_0, logs/Uy_0, etc.
```

| Quantity | Steady Target | Transient Target (per timestep) |
|----------|-------------|-------------------------------|
| p/p_rgh | < 1e-6 | < 1e-4 |
| U | < 1e-6 | < 1e-4 |
| k (if RANS) | < 1e-6 | < 1e-4 |
| epsilon/omega (if RANS) | < 1e-6 | < 1e-4 |
| h/e (if thermal) | < 1e-6 | < 1e-4 |

If residuals plateau above targets:
- Check mesh quality near high-gradient regions
- Verify relaxation factors are appropriate (reduce p relaxation if oscillating, increase if stalling)
- Check for reverse flow at outlets (common in separated flows) — acceptable if < 10% of boundary faces

#### Conservation

```bash
# Mass conservation: compare inlet vs outlet flow rate
postProcess -func "flowRatePatch(name=inlet)"
postProcess -func "flowRatePatch(name=outlet)"
```

Mass imbalance: `|ṁ_in - ṁ_out| / ṁ_in < 1e-6`

For thermal cases, also check energy balance.

#### Physical Plausibility

- Maximum velocity within expected range (e.g., not Mach > 0.3 for incompressible)
- Pressure drop in expected direction
- No negative absolute pressure or temperature (unless physically valid)
- Wall y+ values within turbulence model range
  - kEpsilon with wall functions: 30 < y+ < 300
  - kOmegaSST without wall functions: y+ < 1
  - Check with: `postProcess -func yPlus`

## Stage 9e: Adjoint Sensitivity Check (Adjoint Cases Only)

### Procedure

```bash
# Run adjoint solver
<adjoint-application> > log.adjoint 2>&1

# Check sensitivity field
postProcess -func "sensitivity" 2>&1
```

### Gate Conditions
- Adjoint residuals converge (typically looser than primal: < 1e-4)
- Sensitivity field is non-zero in design regions
- Sensitivity field is physically plausible:
  - High sensitivity near high-gradient regions (corners, bends)
  - Sensitivity decays away from regions of interest
  - No extreme localized spikes (may indicate mesh issues)
- Adjoint-transpose consistency check (if available): < 1% discrepancy

## Stage 9f: Full Run Authorisation

Before launching the full optimisation or production run:

1. Present a concise summary:
   - Baseline objective value
   - Expected number of design iterations
   - Estimated wall-clock time per iteration
   - Total estimated runtime and core-hours
   - Disk space estimate

2. Require explicit user confirmation for:
   - Estimated > 1000 core-hours
   - Any run with `custom` or `external` support level
   - Destructive operations (overwrite, clean, etc.)

3. After confirmation, launch the run:
   ```bash
   # Serial
   <application> > log.run 2>&1

   # Parallel
   mpirun -np <N> <application> -parallel > log.run 2>&1
   ```

## Stage 10: Validation Report

### Report Template

```markdown
# Validation Report: <project_name>

## 1. Environment
- OpenFOAM: <distribution> v<version> (<build>)
- Host: <host_os>, <architecture>
- Cores: <np>, MPI: <flavor>

## 2. Mesh
- Generator: <blockMesh|snappyHexMesh>
- Cell count: <n_cells>
- Max non-orthogonality: <value> (threshold: <threshold>) [PASS|FAIL]
- Max skewness: <value> (threshold: <threshold>) [PASS|FAIL]
- Mesh independence: <description or N/A>

## 3. Numerical Convergence
### Primal
| Variable | Final Residual | Target | Status |
|----------|---------------|--------|--------|
| p        | <value>       | <target> | PASS/FAIL |
| U        | <value>       | <target> | PASS/FAIL |

### Adjoint (if applicable)
| Variable | Final Residual | Target | Status |
|----------|---------------|--------|--------|
| adj-U    | <value>       | <target> | PASS/FAIL |
| adj-p    | <value>       | <target> | PASS/FAIL |

## 4. Conservation
- Mass imbalance: <value> (target: < 1e-6) [PASS|FAIL]
- <additional conservation checks>

## 5. Physical Plausibility
- Max velocity: <value> m/s (expected: <range>) [PASS|FAIL|REVIEW]
- Pressure drop direction: <inlet> Pa → <outlet> Pa [PASS|FAIL]
- y+ range: <min> to <max> [PASS|FAIL|REVIEW]

## 6. Optimisation Results
- Initial objective: <value>
- Final objective: <value> (change: <delta>%)
- Constraint status: <description>
- Design iterations: <n>
- Convergence: [converged|max iterations reached|stalled]

## 7. Reproducibility
- Exact command: `<full-command>`
- Case directory: <path>
- Git commit / file hashes: <hashes>
- Key log files: <paths>

## 8. Warnings and Caveats
- <warning 1>
- <warning 2>

## 9. Overall Assessment
[PASS|PASS WITH WARNINGS|FAIL]
```

### Assessment Criteria

| Grade | Criteria |
|-------|---------|
| PASS | All mandatory gates pass, no fatal warnings |
| PASS WITH WARNINGS | All mandatory gates pass, non-fatal warnings present (e.g., minor reverse flow, y+ borderline) |
| FAIL | Any mandatory gate fails |

## Failure Diagnosis

When any gate fails, read `references/error-diagnostics.md` and preserve the complete failed-run manifest.

### Solver Divergence

1. Check initial conditions are physically reasonable
2. Reduce relaxation factors (especially p: 0.3 → 0.1)
3. Check mesh quality in regions of high gradient
4. Run a laminar case first before enabling turbulence
5. Start from a potential flow solution (`potentialFoam`)

### Conservation Violations

1. Check boundary condition consistency (inlet = fixedValue, outlet = fixedValue or zeroGradient)
2. Verify patch types in `constant/polyMesh/boundary`
3. Check for missing or duplicate patches
4. Ensure no internal faces are incorrectly assigned as patches

### Adjoint Issues

1. Ensure primal is fully converged before adjoint solve
2. Check that cost function patches are correctly specified
3. Verify adjoint boundary conditions in `system/adjointDict`
4. For topology optimisation: check regularization parameters (filter radius ≥ 2× cell size)

## Reproducibility Record

To enable clean rerun and learning promotion:

```bash
# Capture version information
foamVersion > case/version_info.txt 2>&1

# Record exact commands
echo "<exact command with all arguments>" > case/commands.sh

# File summaries (hashes or file listings)
find case/{0,constant,system} -type f -exec sha256sum {} \; > case/file_hashes.txt 2>/dev/null || \
find case/{0,constant,system} -type f > case/file_list.txt
```

## ParaView Post-Processing

### Creating a case.foam placeholder

ParaView reads OpenFOAM cases through a `.foam` placeholder. Create it in the case directory:

```bash
cd <case-directory>
touch case.foam
```

### Automated / Headless Rendering

Use `pvpython --force-offscreen-rendering` for scripted visualization. The `--force-offscreen-rendering` flag is **critical** in WSL and headless Linux environments — without it, ParaView crashes with SIGSEGV because it tries to create an X11/OpenGL render window that requires GPU passthrough.

**Minimum working example:**

```bash
pvpython --force-offscreen-rendering << 'EOF'
from paraview.simple import *

case = OpenFOAMReader(FileName="case.foam")
case.MeshRegions = ["internalMesh"]
case.CellArrays = ["U", "p"]  # fields to load
case.UpdatePipeline()

view = CreateView("RenderView")
display = Show(case, view)
view.ViewSize = [1600, 900]

# Velocity
ColorBy(display, ("CELLS", "U"))
LoadPalette("Black Blue and White")
Render()
SaveScreenshot("velocity.png")

# Pressure
ColorBy(display, ("CELLS", "p"))
LoadPalette("Cool to Warm (Extended)")
Render()
SaveScreenshot("pressure.png")
EOF
```

**Common operations:**

| Task | ParaView Python API |
|------|-------------------|
| Load case | `OpenFOAMReader(FileName="case.foam")` |
| Clip to midplane | `Clip(Input=case).ClipType = "Plane"` |
| Streamlines | `StreamTracer(Input=case, SeedType="Line")` |
| Velocity vectors | `Glyph(Input=case, GlyphType="Arrow")` |
| Mesh surface | `display.Representation = "Surface"` |
| Wireframe | `display.Representation = "Wireframe"` |

**Environment-specific notes:**

- **WSL2 with WSLg (GUI)**: Run `paraview case.foam` directly in an interactive WSL terminal — WSLg displays it as a native Windows window
- **WSL2 headless**: `pvpython --force-offscreen-rendering` (uses Mesa EGL software rasterizer)
- **Native Linux with GPU**: `pvpython` without flags works if `/dev/dri` exists
- **HPC cluster**: Use `pvbatch --force-offscreen-rendering` for MPI-parallel rendering

### Export for external tools

```bash
# Export all fields to VTK (readable by ParaView, Visit, Python VTK)
foamToVTK -latestTime

# Export single field to CSV along a line
postProcess -func "sets" -latestTime
```
