# Geometry, Physics and Verification Gates

## Geometry QA gate

Before meshing, record units and scale, bounding box, watertightness, non-manifold edges, degenerate faces, normal consistency and boundary-condition coverage. Every exposed face must be assigned or explicitly accepted as wall. A CAD-to-patch mapping must retain source model and face identifiers.

## Physics sanity gate

Compute the dimensionless quantities that control the selected model. At minimum evaluate Reynolds and Mach numbers; add Prandtl, Grashof/Rayleigh, Weber, Froude or Knudsen numbers when the requested physics needs them. Verify material-property temperature ranges and derive turbulence inlet quantities from documented intensity and length-scale assumptions.

## Verification and validation gate

Use at least three systematically refined meshes for decision-critical results. Report observed order, extrapolated value and Grid Convergence Index when the solutions are in the asymptotic range. Transient cases also require timestep independence. Compare against an analytical result, official benchmark or experimental dataset and separate numerical, model-form and input uncertainty.

## Optimised-design re-evaluation

Do not accept an objective computed only on a morphed or porous optimisation mesh. Export the final geometry, construct an independent body-fitted mesh, repeat the primal calculation and report the difference from the optimiser's predicted objective.
