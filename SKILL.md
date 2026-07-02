---
name: openfoam-simulation
description: >
  Plan, build, run, validate, and document OpenFOAM fluid simulations on Linux or WSL.
  Execute this skill whenever the user requests CFD simulation, OpenFOAM case setup,
  mesh generation, solver execution, topology optimization, shape optimization,
  adjoint optimization, fluid topology optimization, flow simulation, heat transfer
  simulation, drag/lift analysis, pressure-loss optimization, duct/pipe flow,
  parametric CFD sweeps, or any task that mentions OpenFOAM, foam, blockMesh,
  snappyHexMesh, simpleFoam, pimpleFoam, adjointOptimisationFoam,
  adjointShapeOptimisationFoam, adjointShapeOptimizationFoam, or fluid dynamics simulation. Use this skill even
  when the user only hints at running a fluid simulation or asks vaguely about
  "simulating flow" or "optimizing a channel/pipe/duct/wing/heat-sink shape."
compatibility: Linux or WSL2 with OpenFOAM Foundation (org) or OpenCFD (com) installed, bash, Python 3
---

# OpenFOAM Simulation

## Execution Contract

This skill enforces a 13-step state machine. Each step gates the next. If any mandatory check fails, stop and report the diagnostic — do not proceed without correction.

1. **Environment gate**
2. **OpenFOAM identity gate**
3. **Structured intake** (includes compute optimization preferences)
4. **Documentation gate**
5. **Problem classification**
6. **Solver capability resolution**
7. **Solver source decision** (use existing binary vs compile vs modify-and-compile)
8. **Workflow resolution**
9. **Case construction**
10. **Staged execution** (includes parallel/GPU configuration)
11. **Validation and reporting**
12. **Learning candidate**
13. **Compute optimization** (applied across Steps 3, 7, and 10)

## Routing

| Situation | Action |
|-----------|--------|
| User says "run simulation", "simulate flow", "optimize X" without a prepared case | Start from Step 1, proceed sequentially |
| User supplies a complete case directory but no simulation spec | Start from Step 2 (verify environment), then jump to Step 9 (staged execution) |
| User asks "what solver for X" | Execute Steps 1-7, present the solver recommendation and compilation options |
| User asks "how to speed up my simulation" | Load `references/compute-optimization.md`, analyze the case, present MPI/GPU options |
| User says "validate my results" | Execute Steps 1-2, then Step 10 |
| OpenFOAM not installed or env not sourced | Stop at Step 1, output diagnostic commands, exit |
| Workflow matches an existing validated learned-workflow | Route through Steps 1-6 for verification, then follow the learned workflow for Steps 7-10 |

## Step 1: Environment Gate

Run `python3 scripts/doctor.py --repository-only`, then detect and record the execution environment with `scripts/detect_environment.sh`. The repository doctor must pass before simulation work begins. The environment script outputs JSON with:
- `host_os`, `host_kernel`, `architecture`
- `is_wsl`, `wsl_version` (if applicable)
- `shell`, `mpi_available`, `mpi_flavors`
- `of_env_loaded`, `WM_PROJECT_DIR`, `WM_PROJECT_VERSION`, `WM_OPTIONS`
- `of_executables_path`, `of_lib_path`
- `python_version`, `required_python_packages`

**Stop conditions:**
- OpenFOAM not installed → output diagnostic with distribution-specific install links, stop
- `WM_PROJECT_DIR` unset → instruct user to source their OpenFOAM bashrc, stop
- Neither Linux nor WSL detected → explain platform requirement, stop

## Step 2: OpenFOAM Identity Gate

Run `scripts/inspect_openfoam.sh` to capture:
- Distribution family: `openfoam.org` (Foundation) or `openfoam.com` (OpenCFD/ESI)
- Version number, build tag, compiler, precision, label size
- Installation root and environment script path
- Available solver applications, libraries, function objects, and tutorials
- `-help` output for candidate solvers

Record this in the simulation specification under `environment.of_identity`.

**Stop conditions:**
- Distribution family cannot be determined → stop, do not guess
- Version is ambiguously detected → present evidence, ask user to confirm
- Foundation/OpenCFD mix-up possible (both installed) → require explicit user choice

## Step 3: Structured Intake

Use `references/intake-schema.md` to collect a complete normalized simulation specification. The schema covers:

- Environment and execution target
- Geometry and coordinate system — **choice between CAD model upload or text description** (see below)
- Fluid/solid properties with units and temperature dependence
- Flow regime estimates and characteristic scales
- Boundary and initial conditions
- Physical models (turbulence, heat transfer, multiphase, etc.)
- Mesh strategy and quality thresholds
- Primal solver requirements
- Optimisation type, design variables, objectives, constraints, regularisation
- Convergence and validation criteria
- Compute budget, parallelism, restart policy, storage limits
- Requested results and visualization/export formats
- Assumptions, unresolved risks, and source provenance

Before accepting geometry or physics, apply `references/geometry-physics-vv.md`: verify CAD units, scale, watertightness, normals, complete BC coverage, governing dimensionless numbers, and material-property validity.

**Geometry intake — two paths:**

| User has... | Action |
|------------|--------|
| CAD model file (.stp, .stl, .obj, etc.) | Call `pick_face()` from `scripts/model-viewer/pick_face.py` to pop up an interactive 3D face picker for each boundary type. Read `references/model-import.md` for the full workflow. |
| No CAD file / text description only | Collect geometry via structured questions (dimensions, features, BC locations). Skip model-viewer. |

**If user provides a CAD file — agent-driven pick workflow:**

The agent calls `pick_face()` once per boundary type. Each call auto-parses the model, auto-starts the server (if needed), opens a browser pick window, and blocks until the user confirms.

```python
import sys; sys.path.insert(0, 'scripts/model-viewer')
from pick_face import pick_face

# For each boundary type needed, pop up a pick window:
inlet  = pick_face(model_path, label="请点击选择【入口面】(Inlet)")
outlet = pick_face(model_path, label="请点击选择【出口面】(Outlet)")
walls  = pick_face(model_path, label="请点击选择【壁面】(Wall)")
# ... heat_source, symmetry, open, etc.
```

**What happens in each call:**
1. Model file is auto-parsed (STEP/STL/OBJ → face groups)
2. Server auto-starts on port 8765 (reuses existing if running)
3. Browser opens with full-screen 3D picker showing the model
4. User clicks faces to toggle selection (green highlight), multi-select supported
5. User clicks "确认" → window closes → `pick_face()` returns structured data
6. User clicks "取消" → window closes → returns `{"count": 0, "faces": []}`
7. Agent processes the result and proceeds to the next boundary type

**Return format:**
```json
{
  "model_id": "abc123", "file_name": "model.step", "count": 3,
  "faces": [
    {"face_id": 0, "area": 0.0025, "centroid": [0,0,0], "normal": [0,0,1], "face_type": "planar"},
    ...
  ]
}
```

**Interaction rules:**
- Ask only for decision-critical information the user has not already supplied
- Infer defaults from geometry and regime estimates when safe, but label them as assumptions
- Distinguish SI from other unit systems explicitly
- Present a concise simulation contract for user confirmation before proceeding when assumptions materially affect physics, cost, geometry, or optimisation objectives
- When the user provides a CAD file, **always** use interactive BC selection via `pick_face()` — never guess boundary locations from text description

## Step 4: Documentation Gate

Load and follow `references/documentation-policy.md`. Evidence priority:

1. `-help` and capabilities reported by the installed executable
2. Installed tutorials, source, API guides, and local manuals for the detected version
3. Official online documentation and source repository for the same distribution and version
4. Peer-reviewed literature for numerical methods and validation
5. Clearly labeled community material for troubleshooting only

**Rules:**
- Every consequential solver or dictionary decision must record its source
- Never combine Foundation and OpenCFD instructions unless the difference is explicitly mapped and verified against the installed environment
- Use `foamHelp`, `foamInfo`, `foamSearch` when available before online search

## Step 5: Problem Classification

Assign a stable problem fingerprint. Read `registry/problem-types.yaml` for the classification schema.

Each fingerprint records:
- `flow_regime`: steady/transient, incompressible/compressible, laminar/RANS/LES
- `physics`: single-phase, multiphase, isothermal, conjugate-heat-transfer, buoyancy, species, combustion
- `geometry_class`: internal/external, 2D/3D, axisymmetric
- `optimisation_family`: shape, density-topology, level-set, parameter-sweep, external-optimizer
- `objectives`: pressure-loss, drag, lift, uniformity, heat-transfer, multi-objective
- `constraints`: volume, pressure, temperature, manufacturing
- `design_variables`: boundary-displacement, porosity-field, control-points, parametric

## Step 6: Solver Capability Resolution

Load `references/solver-selection.md` and cross-reference with `registry/solvers.yaml`.

Process:
1. Generate candidates from the installed environment (binary names, `-help` output)
2. Match candidates against the problem fingerprint
3. Consult local documentation and `-help` for capability evidence
4. Rank by capability fit, with evidence for each
5. State why each alternative was rejected
6. Record the decision with sources in the simulation specification

Return a `solver_requirement_report` for every solver decision. Keep capability
requirements separate from executable names so missing physics cannot be hidden by
a similarly named solver:

```yaml
solver_requirement_report:
  required_capabilities: []
  installed_match: null
  missing_capabilities: []
  acquisition_branch: A | B | C | D
  evidence: []
  recommended_next_action: ""
```

For topology optimisation, distinguish these routes explicitly:

- Foundation 13 `adjointShapeOptimisationFoam`: legacy blockage-field optimisation
  for total pressure loss only; do not classify it as boundary-displacement shape
  optimisation or a general topology framework.
- OpenCFD `adjointOptimisationFoam`: shape capability is version-dependent; native
  isothermal porosity/level-set topology requires v2312 or newer and exact-version
  tutorial/source evidence.
- CHT or heat-transfer topology: use a primal thermal solver plus an external
  optimiser, or Branch C custom adjoint development, unless the installed version
  supplies direct thermal-adjoint evidence.
- Pareto multi-objective optimisation: require an external multi-objective driver;
  a weighted scalar objective is not evidence of Pareto capability.

**Critical rule:** Never select a solver solely from a remembered name. Solver names and semantics are version-dependent — `adjointOptimisationFoam`, `adjointShapeOptimisationFoam`, and `adjointShapeOptimizationFoam` occur in different distributions and releases. Always verify the exact executable, source and tutorial in the installed environment.

**Stop conditions:**
- No solver matches required capabilities → report gap, suggest alternatives, stop
- Optional capability missing (e.g., thermal requested but only isothermal solver available) → report the limitation, ask whether to proceed with reduced scope
- CHT topology requested without installed thermal-adjoint evidence → route to external/custom and do not generate a native adjoint dictionary
- Pareto front requested with only a scalar optimiser → report the missing multi-objective driver and stop before a production run

## Step 7: Solver Source Decision

After the capability-matched solver is identified, determine how to obtain the executable. Load `references/solver-compilation.md` for the full decision tree and compilation procedures.

The decision has four branches:

| Branch | Condition | Action |
|--------|----------|--------|
| **A: Pre-compiled binary** | Solver exists in `$FOAM_APPBIN/` | Use as-is. No compilation needed. Verify with `-help`. |
| **B: Compile from official source** | Source exists in `$FOAM_SOLVERS/` but binary not compiled | Guide user through `wmake` compilation |
| **C: Modify and compile** | Solver needs source changes for required physics | Copy to `$WM_PROJECT_USER_DIR`, apply patches, compile |
| **D: Third-party/custom** | No matching source in OpenFOAM | Guide to external solver installation or custom development |

**Presentation rules:**
- Always present all viable options to the user with clear trade-offs
- State estimated compilation time and disk space for Branches B/C
- For Branch C: show exactly which files need changes and why
- Never compile without user confirmation
- Always compile to user-writable directories (`$FOAM_USER_APPBIN`, `$WM_PROJECT_USER_DIR`)

**Safety rules for compilation:**
- Never `sudo wmake` — compile only to user directories
- Always copy (don't modify) original source
- Always verify the compiled binary with `-help` before using it
- Always record the diff or git commit of any source changes
- Always run smoke test (Step 10c) with a compiled solver before full run

## Step 8: Workflow Resolution

Search `registry/learned-workflows/` for the highest-compatible validated workflow matching the problem fingerprint.

- **Match found with status `validated`**: Load the workflow, verify version compatibility, follow its execution steps. Document that a validated workflow is in use.
- **Match found with status `experimental`**: Load it but warn the user. Follow its steps while treating every decision as provisional.
- **No match**: Enter exploratory mode. Read `references/topology-optimization.md` for topology optimization cases. Load the nearest classic template from `templates/` if applicable. Label all unverified decisions explicitly.

## Step 9: Case Construction

1. Copy from a template or tutorial, or create a fresh case directory
2. Never mutate the source; always work in a dedicated run directory
3. Record provenance: which template/tutorial was copied, what was changed, and why
4. Generate or modify dictionaries using evidence from Step 4
5. Write a `simulation_spec.json` alongside the case recording all decisions
6. Run the case-construction record through `scripts/validate_case.sh` for syntax and structure checks
7. Create `run_manifest.json` with `scripts/create_run_manifest.py` before and after execution

## Step 10: Staged Execution

Execute in order, with a gate after each stage. Before reaching Stage 10g, load `references/compute-optimization.md` and present parallel/GPU options to the user.

| Stage | Action | Gate condition |
|-------|--------|---------------|
| 10a | Dictionary syntax check (`foamDictionary -expand`, checkMesh dry-run) | All dictionaries parse without error |
| 10b | Mesh generation and quality check | `checkMesh` passes quality thresholds |
| 10c | Bounded smoke run (coarse mesh, serial, few iterations) | Solver starts, no divergence, mass conservation OK |
| 10d | Baseline primal simulation | Converged, residuals within targets, conservation satisfied |
| 10e | Sensitivity/gradient check (adjoint cases) | Gradients computed, non-zero, physically plausible |
| 10f | Compute resource configuration — present MPI/GPU options to user | User confirms parallel decomposition and GPU settings |
| 10g | Authorized full run (optimisation loop or production solve) | User confirmation obtained before launching |

**Stage 10f details — Compute resource configuration:**

Before the full run, present a compute estimate and let the user choose:

1. **Profile the case**: cell count, solver type, steady/transient
2. **Detect available hardware**: CPU cores, GPU presence, MPI flavor
3. **Present options with estimates**:
   - Serial baseline (wall time estimate)
   - MPI parallel (recommended core count, estimated speedup)
   - GPU acceleration (if available and solver-compatible)
4. **User selects** → configure `system/decomposeParDict` and execution command
5. For MPI: run `decomposePar` before solver; `reconstructPar` after

**Stop conditions for any stage:**
- Residual divergence or solver crash → capture logs, diagnose using `references/validation-and-convergence.md`, report
- Conservation violation → stop, report the violation with magnitude and location
- Mesh quality below threshold → stop, recommend mesh improvements
- Compiled solver crashes → check compilation, compare with `-help`, isolate with minimal test case

## Step 11: Validation and Reporting

Follow `references/validation-and-convergence.md` and `references/geometry-physics-vv.md`. Decision-critical work requires mesh/timestep independence and benchmark evidence. Optimised designs require an independent body-fitted primal re-evaluation. Generate a validation report covering:

- Numerical convergence (residuals, iterations, CFL if transient)
- Conservation checks (mass, momentum, energy where applicable)
- Mesh quality and mesh independence summary
- Physical plausibility (order-of-magnitude checks, expected trends)
- Objective history and constraint satisfaction (optimisation cases)
- Reproducibility record (commands, versions, file hashes or summaries, logs, metrics, output paths)

The output is a Markdown report saved alongside the case.

## Step 12: Learning Candidate

For workflows not already registered as `validated`:

1. Run `scripts/scaffold_learning_record.py` to create a candidate record from the simulation specification and results
2. The record includes: problem fingerprint, version compatibility, source citations, solver selection rationale, normalized inputs, execution commands, convergence and validation results, known failure modes observed, and reusable file references
3. Status is set to `experimental` (never `validated` automatically)
4. Save to `registry/learned-workflows/<problem-fingerprint-slug>.yaml`
5. Present a summary to the user:
   - "This workflow succeeded and is now recorded as **experimental**."
   - "To promote it to validated, re-run with a clean case and confirm the results."

**Promotion rules (user must explicitly request):**
- From `experimental` to `validated`: requires a successful clean rerun, all validation thresholds met, no unresolved fatal warnings, and explicit user approval
- From `validated` to `deprecated`: when a newer OpenFOAM version breaks compatibility
- Records are scoped by distribution family and version range — conflicting records for different versions coexist

## Safety Rules

- **Never** install or upgrade OpenFOAM, WSL, MPI, compilers, or third-party optimizers
- **Never** alter shell startup files (.bashrc, .profile, etc.)
- **Never** overwrite a source case; always copy to a dedicated run directory
- **Never** select a solver or write a dictionary based solely on memory — always verify against the installed environment
- **Never** claim a solver or dictionary is portable between Foundation and OpenCFD distributions
- **Never** promote a workflow based only on solver convergence without physical and reproducibility checks
- **Never** compile with `sudo` — always compile to user-writable directories (`$FOAM_USER_APPBIN`, `$WM_PROJECT_USER_DIR`)
- **Never** modify original solver source in place — always copy first
- **Always** require user confirmation before high-cost runs (estimated > 1000 core-hours), broad filesystem changes, destructive cleanup, or solver compilation
- **Always** use bounded smoke runs before full optimisation
- **Always** run smoke test with a newly compiled solver before full execution
- **Always** preserve failed logs and configuration snapshots for diagnosis
- **Always** treat solver convergence as necessary but not sufficient evidence of correctness

## Outputs

Every completed run must produce:
1. Normalized simulation specification (`simulation_spec.json`)
2. Environment and OpenFOAM identity report
3. Problem classification and solver decision record
4. Documentation and source record
5. Reproducible case directory or patch set
6. Exact serial/parallel commands used
7. Validation and convergence report
8. Result summary with objective and constraint histories
9. Learning candidate (when workflow was previously unregistered)
10. Immutable run manifest (`run_manifest.json`)

## Reference Files

| File | When to Read |
|------|-------------|
| `references/intake-schema.md` | Step 3 — every structured intake |
| `references/model-import.md` | Step 3 — when user has a CAD model file (STP/STL/OBJ) |
| `references/documentation-policy.md` | Step 4 — before consulting any documentation |
| `references/solver-selection.md` | Step 6 — before proposing any solver |
| `references/solver-compilation.md` | Step 7 — solver source decision (binary vs compile vs custom) |
| `references/topology-optimization.md` | Step 8 — when optimisation family is topology or shape optimisation |
| `references/validation-and-convergence.md` | Steps 10-11 — for gate criteria, validation, and ParaView post-processing |
| `references/geometry-physics-vv.md` | Steps 3, 9, and 11 — geometry QA, physics sanity, GCI, and optimised-design re-evaluation |
| `references/error-diagnostics.md` | Step 10 — failure classification and recovery evidence |
| `references/compute-optimization.md` | Step 3 and Step 10f — MPI/GPU configuration and performance estimation |
| `references/local-topology-setup-cn.md` | Steps 1, 6, and 7 — local Foundation/OpenCFD/external-optimiser setup tutorial |
| `registry/solvers.yaml` | Step 6 — solver capability matching |
| `registry/problem-types.yaml` | Step 5 — problem fingerprinting |
| `registry/learned-workflows/` | Step 8 — workflow resolution |
| `templates/*/` | Step 8-9 — when a classic template matches the problem class |
