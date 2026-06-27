# Internal Flow Pressure-Loss Minimisation

## Problem Class

Optimize the internal geometry of a duct, pipe bend, manifold, or channel to minimize pressure loss (total or static pressure drop) while maintaining a target volume or cross-section constraint.

## Typical Applications

- HVAC duct bend optimization
- Exhaust manifold design
- Pipe junction / T-junction loss reduction
- Heat exchanger header/manifold flow distribution
- Micro-channel network optimization

## Optimisation Approach

### Shape Optimisation (Native on both distributions)

The boundary shape is deformed using adjoint-computed surface sensitivities. Topology is preserved — the duct remains a connected channel.

**Solver**: `adjointShapeOptimizationFoam` (Foundation) or `adjointOptimisationFoam` with shape design variables (OpenCFD v2206+).

### Density-Based Topology Optimisation (Native on OpenCFD v2206+)

A porosity field (α) is optimized in the design domain. The Brinkman penalty term drives α → 0 in solid-like regions and α → 1 in fluid regions.

**Solver**: `adjointOptimisationFoam` with porosity design variables (OpenCFD v2206+).

## Required Inputs

| Parameter | Example | Unit |
|-----------|---------|------|
| Inlet flow rate or velocity | 0.1 kg/s or 1.0 m/s | kg/s or m/s |
| Outlet pressure | 0 Pa (gauge) | Pa |
| Hydraulic diameter | 0.01 | m |
| Design domain dimensions | bounding box | m |
| Fluid properties | ρ, ν (or μ) | kg/m³, m²/s |
| Volume fraction constraint | 0.4 | - |
| Reynolds number (estimated) | 1000 | - |

## Workflow Steps

1. **Environment check** — Verify OpenFOAM distribution and adjoint solver availability
2. **Documentation gate** — Check `-help` output for the selected adjoint solver
3. **Mesh generation** — blockMesh for simple geometries, snappyHexMesh for complex
   - For shape optimization: mesh only the fluid domain
   - For topology optimization: mesh the full design domain (fluid + potential solid)
4. **Case setup**:
   - `0/U`, `0/p` — boundary conditions per intake
   - `constant/transportProperties` — fluid viscosity
   - `constant/physicalProperties` (if OpenCFD) or `constant/transportProperties` (if Foundation)
   - `system/controlDict`, `fvSchemes`, `fvSolution`
   - `system/adjointDict` — cost function, constraints, regularisation
5. **Staged execution**:
   a. Dictionary syntax check
   b. Mesh quality check (checkMesh)
   c. Smoke run (coarse mesh, 50 iterations)
   d. Baseline primal (full convergence)
   e. Sensitivity computation (one adjoint solve)
   f. Full optimisation loop
6. **Validation** — Objective convergence, volume constraint satisfaction, mass conservation

## Typical Results

- Pressure loss reduction: 15-40% (shape), 30-60% (topology)
- Design iterations: 20-80
- Key outputs: optimized geometry, objective history plot, velocity/pressure fields

## Known Issues

- Adjoint may diverge if primal is not fully converged
- Volume constraint may oscillate if step size is too large
- Low-Re kOmegaSST may be needed for transitional flows
- Foundation's adjointShapeOptimizationFoam is laminar only
