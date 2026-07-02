# Duct/Bend Shape Optimisation

## Problem Class

Optimize the shape of internal flow passages — bends, diffusers, nozzles, contractions, or transitions — to minimize total pressure loss, improve flow uniformity at the outlet, or both.

## Typical Applications

- 90° pipe bend loss reduction
- Diffuser pressure recovery maximization
- Nozzle contour optimization
- Intake/exhaust port shaping
- Sudden expansion/contraction transition optimization

## Optimisation Approach

### Shape Optimisation (Native on both distributions)

The duct wall boundaries are parameterized (typically via control points or free-form deformation) and deformed using adjoint surface sensitivities.

**Solver**: `adjointOptimisationFoam` with exact-version boundary-displacement
evidence (OpenCFD v1906+), or a Foundation solver only when installed
source/tutorial evidence proves true boundary displacement. Foundation 13
`adjointShapeOptimisationFoam` is not such a solver.

### Multi-Objective Variant

When both pressure loss and outlet uniformity matter, use a weighted cost function:

```
J = w₁ * J_pressureLoss + w₂ * J_uniformity
```

where `J_uniformity` can be defined as the standard deviation of outlet velocity or the deviation from a target flow profile.

## Required Inputs

| Parameter | Example | Unit |
|-----------|---------|------|
| Bend angle | 90 | degrees |
| Pipe diameter / hydraulic diameter | 0.0254 (1 inch) | m |
| Bend radius (initial) | 1.5 × diameter | m |
| Inlet flow rate or velocity | 2.0 m/s | m/s |
| Fluid | Water (ν=1e-6) | m²/s |
| Reynolds number | 50,000 | - |
| Morphing region | ±3D upstream/downstream of bend | m |
| Objectives | pressure_loss, uniformity | - |
| Weights (if multi-objective) | w₁=0.7, w₂=0.3 | - |

## Workflow Steps

1. **Mesh generation** — blockMesh with grading toward walls and bend region
   - Near-wall refinement for boundary layer resolution
   - Bend region refinement for curvature capture
2. **Baseline primal** — Converge to steady state
3. **Adjoint sensitivity** — Compute sensitivities on bend walls
4. **Morph mesh** — Displace wall points, smooth interior
5. **Remesh if needed** — If mesh quality degrades, regenerate
6. **Iterate** — Until objective change < 1e-4
7. **Validate** — Compare baseline vs optimized pressure drop, check flow uniformity

## Key Considerations

- **Mesh quality during morphing**: The bend region sees the largest displacement; ensure sufficient mesh resolution and avoid negative volumes
- **Curvature constraints**: Unconstrained optimization may create non-manufacturable shapes; consider adding curvature regularization
- **Flow separation**: Optimized shapes may eliminate or reduce separation zones in sharp bends
- **Laminar vs turbulent**: choose only an installed solver whose adjoint turbulence treatment is documented for the target release

## Typical Results

- Pressure loss reduction in bends: 20-50%
- Characteristic shape change: bend becomes more gradual, inner radius increases
- Flow uniformity improvement: 10-30% reduction in velocity variance at outlet

## Known Issues

- Adjoint gradients are inaccurate in separated flow regions (if using frozen turbulence)
- Mesh morphing in tight bends may produce invalid cells
- Foundation 13 legacy blockage optimisation must not be substituted for this boundary-displacement workflow
