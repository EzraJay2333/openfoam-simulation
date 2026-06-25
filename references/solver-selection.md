# Solver Selection

## Purpose

This reference guides Step 6 (Solver Capability Resolution). It describes the capability-based selection process and known solver families. Always verify availability in the installed environment — never select from memory.

## Selection Process

### Step 6a: Discover Installed Candidates

```bash
# List all installed solver binaries
ls $FOAM_APPBIN/ | grep -i "foam$" | sort

# List all installed solver source directories
ls $FOAM_SOLVERS/ 2>/dev/null || ls $WM_PROJECT_DIR/applications/solvers/

# Check for modular solvers (OpenCFD v2206+)
ls $FOAM_APPBIN/ 2>/dev/null | grep -i "adjoint\|optim"
```

For each candidate, capture `-help` output:

```bash
for solver in <candidate-list>; do
    echo "=== $solver ===" >> solver_help.txt
    $solver -help 2>&1 >> solver_help.txt
done
```

### Step 6b: Classify Candidates by Capability

Map each candidate to one or more capability dimensions:

| Capability | Required Solver Features |
|-----------|------------------------|
| Incompressible steady primal | `simpleFoam`, `porousSimpleFoam` |
| Incompressible transient primal | `pisoFoam`, `pimpleFoam` |
| Compressible steady primal | `rhoSimpleFoam` |
| Compressible transient primal | `rhoPimpleFoam` |
| Conjugate heat transfer | `chtMultiRegionFoam` |
| Adjoint — incompressible shape | `adjointShapeOptimizationFoam` (Foundation), `adjointOptimisationFoam` (OpenCFD) |
| Adjoint — incompressible topology | `adjointOptimisationFoam` with porous/design variables (OpenCFD) |
| Adjoint — thermal | `adjointOptimisationFoam` with thermal objectives (OpenCFD) |
| External optimisation | Any primal solver + external optimiser (DAKOTA, pyOpt) |
| Porous media (Brinkman/Darcy) | `porousSimpleFoam` |
| Moving/rotating mesh | `pimpleFoam` with AMI, `overPimpleDyMFoam` |
| Multiphase | `interFoam`, `multiphaseEulerFoam` |

### Step 6c: Rank by Capability Fit

For each candidate that matches required capabilities, score:

1. **Direct match**: The solver's documented purpose matches the problem exactly (+3)
2. **Partial match with known workaround**: Solver can be adapted with documented modifications (+1)
3. **Version match**: Solver is present in the detected OpenFOAM version (+2)
4. **Tutorial available**: An installed tutorial demonstrates similar usage (+1)
5. **Documentation quality**: -help output is complete and clear (+1)

### Step 6d: Select and Justify

Pick the highest-scoring candidate. Record:

- Why this solver was selected (with source references)
- Why each alternative was rejected
- Any capability gaps and how they are mitigated

## Known Solver Families

### Foundation Distribution (openfoam.org)

| Solver | Purpose | First Available | Notes |
|--------|---------|----------------|-------|
| `simpleFoam` | Steady incompressible turbulent flow (SIMPLE) | v1.0 | Primal solver |
| `pisoFoam` | Transient incompressible turbulent flow (PISO) | v1.0 | Primal solver |
| `pimpleFoam` | Transient incompressible (PIMPLE = PISO+SIMPLE) | v1.6 | Larger timesteps |
| `porousSimpleFoam` | Steady incompressible with porous media | v1.0 | Darcy-Forchheimer |
| `adjointShapeOptimizationFoam` | Steady incompressible adjoint shape optimisation | v2.0 | Surface sensitivities; laminar only in older versions |
| `rhoSimpleFoam` | Steady compressible turbulent flow | v1.0 | |
| `rhoPimpleFoam` | Transient compressible | v2.0 | |
| `chtMultiRegionFoam` | Conjugate heat transfer (multi-region) | v2.0 | |
| `buoyantSimpleFoam` | Steady buoyant flow | v1.6 | |
| `buoyantPimpleFoam` | Transient buoyant flow | v2.0 | |
| `interFoam` | Two-phase incompressible (VOF) | v1.0 | |

### OpenCFD Distribution (openfoam.com)

| Solver | Purpose | First Available | Notes |
|--------|---------|----------------|-------|
| `simpleFoam` | Steady incompressible turbulent flow | v1.0 | Primal solver |
| `pimpleFoam` | Transient incompressible (PIMPLE) | v1.6 | |
| `porousSimpleFoam` | Steady incompressible with porous media | v1.0 | |
| `adjointOptimisationFoam` | Incompressible adjoint optimisation | v2206 | Major overhaul of adjoint library; supports topology, shape, and thermal objectives |
| `adjointShapeOptimizationFoam` | Incompressible adjoint shape optimisation (legacy) | v1912 | Present in older ESI versions; superseded by `adjointOptimisationFoam` |
| `rhoSimpleFoam` | Steady compressible | v1.0 | |
| `chtMultiRegionFoam` | Conjugate heat transfer | v2.0 | |
| `buoyantSimpleFoam` | Steady buoyant flow | | |
| `overPimpleDyMFoam` | Overset mesh + dynamic mesh | v1912 | |

## Capability Gap Handling

When no installed solver fully matches the problem:

```yaml
capability_gap:
  problem_requirement: "topology optimization with conjugate heat transfer"
  best_available: "adjointOptimisationFoam"
  gap: "Thermal objective support not verified in -help output"
  options:
    - { approach: "use adjointOptimisationFoam without thermal objective",
        risk: "may not optimize heat transfer directly" }
    - { approach: "multi-objective with weighted cost function",
        feasibility: "requires custom cost function compilation" }
    - { approach: "external optimizer coupling",
        feasibility: "requires DAKOTA or pyOpt installation" }
  recommendation: "<best option with justification>"
  needs_user_confirmation: true
```

**Stop condition**: If no solver matches a required (not optional) capability, stop and report the gap. Do not invent a solver or configure a solver for a purpose its `-help` output does not describe.

## Cross-Distribution Solver Mapping

The same physical capability often has different solver names across distributions:

| Capability | Foundation (org) | OpenCFD (com) |
|-----------|-----------------|---------------|
| Incompressible shape adjoint | `adjointShapeOptimizationFoam` | `adjointOptimisationFoam` (v2206+) or `adjointShapeOptimizationFoam` (pre-2206) |
| Topology (porosity) adjoint | Not natively available | `adjointOptimisationFoam` (v2206+) |
| Thermal adjoint | Not natively available | `adjointOptimisationFoam` (v2206+) with thermal objectives |

**Rule**: The mapping table is informational only. Always verify with the installed `-help` output. A solver name from the wrong distribution is not a substitute.
