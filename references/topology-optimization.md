# Topology Optimisation Policy

## Purpose

This reference guides topology and shape optimisation workflows. It defines the taxonomy of optimisation approaches, support levels, and the classic workflow templates shipped with this skill.

## Optimisation Type Taxonomy

### Shape Optimisation

**Definition**: Existing boundaries move while the topology (connectivity) is preserved. The design variable is boundary displacement.

**Characteristics**:
- Design variables: boundary point displacements or control point positions
- Adjoint method computes surface sensitivities (gradient of objective w.r.t. boundary displacement)
- Mesh morphing required after each design update
- Preserves topology — no holes can form or close
- Best for: duct bend shape, wing profile, diffuser contour

**OpenFOAM support**:
- Foundation: `adjointShapeOptimizationFoam` (laminar, steady)
- OpenCFD: `adjointOptimisationFoam` with `shape` design variables (v2206+)

**Typical workflow**:
1. Run primal solver to convergence
2. Solve adjoint equations for cost function gradients
3. Compute surface sensitivities
4. Morph mesh using sensitivity-weighted displacement
5. Repeat until convergence or max iterations

### Density/Porosity Topology Optimisation

**Definition**: A distributed scalar design field (α, ranging [0,1] or [0,∞)) penalizes flow through solid-like regions via Darcy or Brinkman terms. The interface between fluid (α=1) and solid (α=0) emerges from the optimisation.

**Characteristics**:
- Design variable: scalar field (porosity or impermeability)
- Brinkman penalty term added to momentum equation: `-α(α_max) * U`
- Adjoint computes volume sensitivities
- Requires regularisation (Helmholtz or Laplace filter, Heaviside projection)
- Can create arbitrary topologies including new holes
- Best for: internal manifold design, heat sink topology, flow distribution

**OpenFOAM support**:
- Foundation: Not natively available; requires custom solver or external optimizer
- OpenCFD: `adjointOptimisationFoam` with `porosity` or `topology` design variables (v2206+)

**Typical workflow**:
1. Define initial design domain (all fluid, α=1)
2. Run primal solver with Brinkman penalty in solid-like regions
3. Solve adjoint for volume sensitivities
4. Filter sensitivities (Helmholtz PDE)
5. Update design field (steepest descent, MMA, or IPOPT via external coupling)
6. Apply Heaviside projection for sharp fluid-solid interface
7. Repeat until convergence

### Level-Set / Explicit Topology Methods

**Definition**: The fluid-solid interface is explicitly tracked as an iso-surface (level-set) or explicitly meshed. The interface moves according to shape sensitivities.

**Characteristics**:
- Sharp interface (no gray regions)
- May require re-meshing or adaptive mesh refinement
- Less common in OpenFOAM; often requires third-party libraries
- Best for: problems requiring sharp interfaces, two-material optimisation

**OpenFOAM support**: Custom or third-party only. Not natively available.

### Parameter Sweep Optimisation

**Definition**: Discrete geometric or physical parameters are varied across a pre-defined range. The objective is evaluated at each point.

**Characteristics**:
- No gradient information needed
- Design variables: geometric parameters (length, angle, etc.) or physical parameters (flow rate, temperature)
- Brute-force or Latin hypercube / DOE sampling
- Best for: low-dimensional design spaces (≤10 parameters), sensitivity studies

**OpenFOAM support**:
- Any solver; orchestrated externally
- This skill provides the `sweep` workflow pattern

### External Optimisation Orchestration

**Definition**: OpenFOAM supplies primal (and optionally adjoint) evaluations. An external tool (DAKOTA, pyOpt, SciPy, custom Python) drives the design updates.

**Characteristics**:
- Maximum flexibility in optimisation algorithms
- Overhead from file I/O between iterations
- Can use gradient-free (genetic, particle swarm) or gradient-based methods
- Best for: problems exceeding native adjoint capabilities, multi-physics, custom objectives

**OpenFOAM support**: Any solver; requires external optimiser installation.

## Support Levels

Every workflow declares one of three levels:

| Level | Symbol | Definition | User Action Required |
|-------|--------|-----------|---------------------|
| `native` | ✓ | Supported by detected installation with official examples or documentation | None |
| `custom` | ⚙ | Requires compiled user code or source modification | User must compile and verify custom code |
| `external` | ⇄ | Requires separately installed optimizer or coupling framework | User must install and configure external tool |

**Assignment rules**:
- Check `-help` output and installed tutorials before assigning `native`
- If source code modification is needed, assign `custom`
- If a separate tool is called to update design variables, assign `external`
- A single workflow may have different support levels for different OpenFOAM distributions

## Initial Classic Workflows

The following classic templates ship with the skill in `templates/`. Each template directory contains a `README.md` describing the problem class, expected inputs, workflow steps, and example case structure.

### 1. Internal Flow Pressure-Loss Minimisation
- **Directory**: `templates/internal-flow-pressure-loss/`
- **Problem**: Minimize pressure drop through a duct, pipe bend, or manifold
- **Optimisation family**: shape (native on Foundation/OpenCFD) or density-topology (native on OpenCFD v2206+)
- **Typical objectives**: total pressure loss, dissipated power
- **Typical constraints**: volume/area fraction ≤ threshold
- **Flow**: steady, incompressible, laminar or turbulent (RANS)

### 2. External Aerodynamic Drag Minimisation
- **Directory**: `templates/external-flow-drag/`
- **Problem**: Minimize drag on a body in external flow
- **Optimisation family**: shape (native on Foundation/OpenCFD)
- **Typical objectives**: drag coefficient, drag force
- **Typical constraints**: volume, lift, geometry packaging
- **Flow**: steady, incompressible, turbulent (RANS)

### 3. Duct/Bend Shape Optimisation
- **Directory**: `templates/duct-shape-optimization/`
- **Problem**: Optimize the shape of a duct bend, diffuser, or nozzle
- **Optimisation family**: shape (native on both distributions)
- **Typical objectives**: pressure recovery, flow uniformity at outlet
- **Typical constraints**: bounding geometry, curvature limits
- **Flow**: steady, incompressible, laminar or turbulent

### 4. Porous Density Topology Optimisation
- **Directory**: `templates/porous-density-topology/`
- **Problem**: Optimize material distribution in a design domain to minimize flow resistance
- **Optimisation family**: density-topology (native on OpenCFD v2206+)
- **Typical objectives**: dissipated power, pressure loss, flow uniformity
- **Typical constraints**: volume fraction, maximum temperature (with CHT)
- **Flow**: steady, incompressible, laminar or turbulent

### 5. Outlet Flow Uniformity Optimisation
- **Directory**: `registry/learned-workflows/` (to be populated)
- **Problem**: Maximize flow distribution uniformity across multiple outlets (e.g., fuel cell manifold, HVAC)
- **Optimisation family**: shape or density-topology
- **Typical objectives**: standard deviation of outlet flow rates, velocity variance
- **Typical constraints**: total pressure loss ≤ threshold
- **Flow**: steady, incompressible

### 6. Conjugate Heat Transfer Topology Optimisation
- **Directory**: `registry/learned-workflows/` (to be populated)
- **Problem**: Optimize solid/fluid distribution for thermal performance (heat sink, cooling channel)
- **Optimisation family**: density-topology with thermal objectives
- **Typical objectives**: minimize max temperature, maximize heat transfer
- **Typical constraints**: pressure loss, volume fraction
- **Flow**: steady, incompressible with conjugate heat transfer

### 7. Time-Averaged Transient Optimisation
- **Directory**: `registry/learned-workflows/` (to be populated)
- **Problem**: Optimize geometry for time-averaged performance metrics
- **Optimisation family**: shape or external
- **Typical objectives**: time-averaged pressure loss, RMS fluctuations
- **Typical constraints**: instantaneous pressure limits
- **Flow**: transient (URANS or LES), incompressible

### 8. Multi-Objective Optimisation with Volume Constraints
- **Directory**: `registry/learned-workflows/` (to be populated)
- **Problem**: Trade off competing objectives (e.g., pressure loss vs heat transfer, drag vs lift)
- **Optimisation family**: shape or density-topology, parameter sweep, or external
- **Typical objectives**: weighted sum or Pareto front
- **Typical constraints**: volume fraction, manufacturing constraints
- **Flow**: steady, incompressible, any physics

## Workflow Template Structure

Each template directory in `templates/` must contain:

```
templates/<template-name>/
├── README.md            # Problem description, inputs, workflow steps
├── case-skeleton/       # Minimal OpenFOAM case directory structure
│   ├── 0/               # Initial/boundary condition templates
│   │   ├── U
│   │   ├── p
│   │   └── ...
│   ├── constant/        # Physical properties, mesh, scheme/solution templates
│   │   ├── transportProperties
│   │   └── ...
│   └── system/          # Solver control templates
│       ├── controlDict
│       ├── fvSchemes
│       ├── fvSolution
│       └── ...
└── workflow.yaml        # Machine-readable workflow specification
```

`workflow.yaml` schema:

```yaml
workflow:
  name: "internal-flow-pressure-loss"
  status: "validated" | "experimental" | "deprecated"
  distribution: ["openfoam.org:10", "openfoam.com:2206"]
  problem_fingerprint:
    flow_regime: [steady, incompressible]
    physics: [single-phase, isothermal]
    geometry_class: [internal, 2d-planar, 2d-axisymmetric, 3d]
    optimisation_family: [shape, density-topology]
    objectives: [pressure-loss]
    constraints: [volume]
  support_level: native
  prerequisites:
    - "adjointOptimisationFoam or adjointShapeOptimizationFoam available"
  steps:
    - { stage: mesh, description: "Generate mesh with blockMesh or snappyHexMesh" }
    - { stage: primal, description: "Run steady incompressible solver to convergence" }
    - { stage: adjoint, description: "Compute adjoint sensitivities" }
    - { stage: update, description: "Update design variables with sensitivity-based step" }
    - { stage: iterate, description: "Loop primal → adjoint → update until convergence" }
    - { stage: validate, description: "Check objective reduction, constraint satisfaction, mesh quality" }
  known_issues: []
  references: []
```

## Regularisation and Filtering

For density-based topology optimisation:

- **Helmholtz filter**: Solves ∇²α̃ = α̃ - α to smooth the design field. Radius controls minimum feature size.
- **Heaviside projection**: Projects filtered field to near-binary (0/1) using tanh or smooth Heaviside. Sharpness parameter controls transition width.
- **Volume constraint**: Typically enforced via augmented Lagrangian or MMA.

These are configured in the adjoint dictionary (`system/adjointDict` or `constant/optimisationDict` depending on version).

## Primal-Adjoint Iteration Pattern

```
1.  Initialize design field α = α₀ (typically all fluid, α=1)
2.  FOR iteration = 1 to max_iterations:
3.    a. Update Darcy penalty from α (Brinkman term)
4.    b. Solve primal (Navier-Stokes + continuity)
5.    c. Check primal convergence
6.    d. Solve adjoint equations
7.    e. Compute volume sensitivity field
8.    f. Apply Helmholtz filter to sensitivities
9.    g. Update design field α (steepest descent or MMA step)
10.   h. Apply Heaviside projection
11.   i. Enforce volume constraint
12.   j. Check design convergence: |α_new - α_old| < tol
13.   k. If converged: break
14. END FOR
15. Final primal evaluation on optimized design
```
