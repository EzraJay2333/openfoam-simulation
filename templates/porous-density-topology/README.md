# Porous Density Topology Optimisation

## Problem Class

Optimize the material distribution (fluid vs solid) within a design domain to minimize flow resistance, dissipated power, or maximize heat transfer. A scalar porosity/impermeability field (α) is the design variable. The Brinkman penalty term in the momentum equation drives the field toward a binary fluid-solid partition.

## Typical Applications

- Heat sink / cold plate channel topology
- Micro-fluidic network design
- Flow manifold / distributor optimization (e.g., fuel cells, batteries)
- Internal cooling channel design
- Fluid diode / Tesla valve design

## Optimisation Approach

### Density-Based Topology Optimisation (Native on OpenCFD v2206+)

A scalar field α ∈ [0, 1] (or [0, α_max]) defines material distribution:
- α = 1: Pure fluid (no penalty)
- α = 0: Solid (maximum Brinkman penalty → U ≈ 0)

The Brinkman term in the momentum equation is:

```
-α * U
```

where large α values approximate solid regions.

**Solver**: `adjointOptimisationFoam` with porosity design variables (OpenCFD v2206+).

**Required components**:
- Porosity field initialization (uniform α=1, all fluid)
- Brinkman penalty in momentum equation (auto-handled by solver)
- Adjoint for volume sensitivity computation
- Helmholtz filter for regularization (filter radius ≥ 2× cell size)
- Heaviside projection for sharp interface (optional, tunable sharpness)
- Volume constraint enforcement (augmented Lagrangian or MMA)

### External Optimisation Variant

For Foundation distribution or older OpenCFD versions, use `porousSimpleFoam` as the primal solver with an external optimizer (SciPy, pyOpt, DAKOTA):

1. SciPy optimizer proposes α field
2. OpenFOAM evaluates primal (porousSimpleFoam)
3. Finite-difference or adjoint gradients computed externally
4. Loop until convergence

Status: `external` support level.

## Required Inputs

| Parameter | Example | Unit |
|-----------|---------|------|
| Design domain dimensions | 0.1 × 0.05 × 0.02 | m |
| Inlet/outlet locations | [0,0,0] → [0.1,0,0] | m |
| Flow rate or pressure drop | 0.1 m/s or 100 Pa | m/s or Pa |
| Fluid properties | ρ, ν | kg/m³, m²/s |
| Volume fraction constraint | 0.4 (max 40% solid) | - |
| Filter radius | 0.002 (≥ 2× cell size) | m |
| Regularisation parameters | Helmholtz filter, Heaviside sharpness | - |
| Thermal properties (if CHT) | k_solid, k_fluid, cp | W/(m·K), J/(kg·K) |

## Workflow Steps

1. **Mesh full design domain** — Uniform or graded blockMesh covering all potential fluid/solid regions
2. **Initialize α field** — Set α = α_max everywhere (all fluid); write to `0/alpha` or `0/porosity`
3. **Case setup** — Configure adjointOptimisationFoam with:
   - Design variables: porosity field
   - Objective: pressureDrop or dissipatedPower
   - Constraint: volume ≤ V_max
   - Regularisation: Helmholtz filter with specified radius
4. **Staged execution**:
   a. Syntax and mesh quality check
   b. Smoke run with uniform α (should give un-penalized flow)
   c. Test sensitivity computation (one design iteration)
   d. Full optimisation loop (50-200 iterations)
5. **Post-processing** — Visualize final α field, velocity streamlines, pressure field

## Expected Results

- Binary or near-binary fluid-solid partition
- Optimized channel geometry emerging from uniform initialization
- Pressure loss typically 30-70% lower than initial uniform-porosity design
- Results depend strongly on mesh resolution and filter radius

## Key Considerations

- **Mesh resolution**: Must resolve expected channel width with at least 5-8 cells; too coarse → checkerboard patterns
- **Filter radius**: Controls minimum feature size; r_filter ≥ 2× cell size essential to avoid checkerboarding
- **Volume constraint**: Start with a loose constraint, tighten gradually
- **Heaviside sharpness**: Start low (β=1), increase gradually (β doubling every 50 iterations) for stable convergence
- **Continuation strategy**: Start with large filter radius, reduce as optimization progresses

## Known Issues

- Gray (intermediate α) regions may persist; increase Heaviside sharpness or run more iterations
- Checkerboard patterns indicate insufficient filter radius
- Optimizer may get stuck in local minima — try different initial α fields
- Large pressure drops in solid-like regions (α ≈ 0) can cause solver instability; clamp minimum permeability
