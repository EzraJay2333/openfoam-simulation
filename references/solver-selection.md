# Solver Selection

## Purpose

This reference guides Step 6 (Solver Capability Resolution). It describes the capability-based selection process and known solver families. Always verify availability in the installed environment — never select from memory.

`registry/solvers.yaml` is the machine-readable source of truth. Tables in this file
explain routing policy only; when they disagree with the registry or installed
evidence, stop and report the conflict instead of choosing a solver.

## Selection Process

### Step 6a: Discover Installed Candidates

```bash
# List all installed solver binaries
ls $FOAM_APPBIN/ | grep -i "foam$" | sort

# List all installed solver source directories
ls $FOAM_SOLVERS/ 2>/dev/null || ls $WM_PROJECT_DIR/applications/solvers/

# Check for optimisation applications and both British/American spellings
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
| Legacy pressure-loss blockage topology | Foundation 13 `adjointShapeOptimisationFoam`; verify binary/source at runtime |
| Adjoint — incompressible shape | Version-specific legacy spelling/source (Foundation), `adjointOptimisationFoam` (OpenCFD) |
| Adjoint — incompressible topology | `adjointOptimisationFoam` with porous/design variables (OpenCFD) |
| Adjoint — thermal/CHT topology | No default native selection; require exact-version executable, source and tutorial evidence |
| External optimisation | Any primal solver + external optimiser (SciPy, DAKOTA, pyOptSparse) |
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
| `adjointShapeOptimisationFoam` | Legacy steady incompressible pressure-loss optimisation | v13 spelling verified | Updates a volumetric blockage field; total-pressure-loss objective only |
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
| `adjointOptimisationFoam` | Incompressible adjoint optimisation | v1906 | Shape capability is release-specific; mono-fluid isothermal topology is verified from v2312 |
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
  best_available: "chtMultiRegionFoam or foamMultiRun primal + external optimizer"
  gap: "No installed, version-matched thermal adjoint topology capability"
  options:
    - { approach: "external optimizer coupling",
        feasibility: "works with an existing thermal primal; finite-difference cost grows with design-variable count" }
    - { approach: "custom thermal adjoint",
        feasibility: "requires user-space source development, compilation and gradient verification" }
    - { approach: "reduce scope to isothermal topology",
        risk: "does not optimize heat-transfer performance" }
  recommendation: "<best option with justification>"
  needs_user_confirmation: true
```

**Stop condition**: If no solver matches a required (not optional) capability, stop and report the gap. Do not invent a solver or configure a solver for a purpose its `-help` output does not describe.

## Cross-Distribution Solver Mapping

The same physical capability often has different solver names across distributions:

| Capability | Foundation (org) | OpenCFD (com) |
|-----------|-----------------|---------------|
| Legacy blockage-field pressure-loss optimisation | Foundation 13 `adjointShapeOptimisationFoam` | Not a cross-distribution substitute |
| Incompressible shape adjoint | Version-specific; require local source/tutorial evidence | `adjointOptimisationFoam` (v1906+, release-specific) |
| General topology (porosity/level-set) adjoint | Not natively available as a general framework | `adjointOptimisationFoam` (mono-fluid isothermal, verified from v2312+) |
| Thermal/CHT adjoint | Not natively available | Unverified; require installed source, help, tutorial, and version-matched official evidence |
| Pareto multi-objective | External optimiser required | External optimiser required unless exact-version native evidence proves otherwise |

**Rule**: The mapping table is informational only. Always verify with the installed `-help` output. A solver name from the wrong distribution is not a substitute.
