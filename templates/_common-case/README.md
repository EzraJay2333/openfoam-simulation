# Foundation 13 baseline smoke case

This small laminar channel is shared by the four workflow templates only to verify environment sourcing, dictionary parsing, meshing, `checkMesh`, bounded primal execution, log parsing, and manifest generation.

It is not a validated physical model of external aerodynamics, topology optimisation, heat transfer, or a specific duct design. Each production workflow must replace the geometry and dictionaries from its confirmed `simulation_spec.json` and pass all 13 gates.
