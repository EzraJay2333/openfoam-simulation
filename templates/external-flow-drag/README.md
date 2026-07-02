# External Aerodynamic Drag Minimisation

## Problem Class

Minimize aerodynamic drag on a body in external flow by optimizing its shape. The body geometry is deformed using adjoint-computed surface sensitivities.

## Typical Applications

- Vehicle aerodynamic shape optimization (car, truck, train)
- Wing/airfoil shape optimization
- Bicycle/rider aerodynamic optimization
- Building wind load reduction
- Sports equipment (helmet, bicycle frame)

## Optimisation Approach

### Shape Optimisation (Native)

Boundary surface points are displaced in the surface-normal direction weighted by adjoint sensitivities. The volume/area of the body is typically constrained.

**Solver**: `adjointOptimisationFoam` with exact-version shape and force-objective
evidence (OpenCFD v1906+), or a Foundation solver only when its installed
source/tutorial proves both capabilities. Foundation 13
`adjointShapeOptimisationFoam` is a pressure-loss blockage solver and must be rejected.

### Key Differences from Internal Flow

- **Far-field boundary conditions**: `freestream` or `inletOutlet` type
- **Turbulence modeling**: Almost always requires RANS (kOmegaSST or SpalartAllmaras)
- **Mesh**: External domain with body-fitted mesh; typically snappyHexMesh
- **Cost function**: Drag force (not pressure drop)
- **Constraints**: Often lift, pitching moment, or body volume

## Required Inputs

| Parameter | Example | Unit |
|-----------|---------|------|
| Freestream velocity | 30.0 | m/s |
| Fluid properties | ρ=1.225, ν=1.5e-5 (air) | kg/m³, m²/s |
| Reference area (for Cd) | 2.0 | m² |
| Body geometry | STL file | - |
| Domain size | 20× body length upstream, 50× downstream | m |
| Turbulence model | kOmegaSST or SpalartAllmaras | - |
| Volume constraint | 0.95 (min 95% of original) | - |

## Workflow Steps

1. **Environment check** — Verify shape, force objective and turbulence-adjoint capabilities from installed evidence
2. **Mesh generation** — snappyHexMesh with boundary layers (y+ < 1 or 30-300 with wall functions)
3. **Baseline primal** — Converge the primal flow field
4. **Adjoint sensitivity** — Compute surface sensitivities for drag
5. **Mesh morphing** — Displace surface points using sensitivities
6. **Iterate** — Loop until drag reduction stalls or max iterations
7. **Validate** — Check final Cd, volume constraint, mesh quality

## Key Considerations

- **Mesh morphing**: Requires `morphMesh` or displacement-based approach; mesh quality degrades with large displacements
- **Turbulence adjoint**: never infer differentiated/frozen-turbulence behaviour from the solver name; verify the installed model and tutorial
- **OpenCFD**: differentiated turbulence models are release-specific; verify the exact installed source before use
- **Blockage ratio**: Domain should be large enough that far-field boundaries don't affect results

## Known Issues

- Large shape deformations cause mesh quality degradation (negative volume cells)
- "Frozen turbulence" approximation may give inaccurate gradients for separated flows
- Drag convergence may be slow for bluff bodies
