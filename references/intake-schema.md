# Structured Intake Schema

## Purpose

This schema defines every field in a normalized simulation specification. During Step 3 (Structured Intake), collect one section at a time. Only ask about fields the user has not already supplied. When a field cannot be determined, record it as an explicit assumption with the label `[ASSUMED]`.

## Schema

### 1. Environment and Execution Target

```yaml
environment:
  target: "wsl2" | "native-linux"
  distribution: "ubuntu-22.04" | "ubuntu-24.04" | "rhel-9" | ...
  of_identity: {}  # populated by Step 2
  work_directory: "/path/to/project/root"
  parallelism:
    mpi: "openmpi" | "intel-mpi" | "none"
    np: 4
    method: "simple" | "hierarchical" | "scotch" | "ptscotch"
    oversubscribe: false
  resources:
    walltime_hours: 24
    ram_gb: 32
    storage_gb: 50
```

### 2. Geometry and Coordinate System

```yaml
geometry:
  description: "2D axisymmetric pipe with 90° bend"
  coordinate_system:
    origin: [0.0, 0.0, 0.0]
    units: "m"
    gravity_vector: [0.0, -9.81, 0.0]  # optional
  dimensions:
    type: "2d-planar" | "2d-axisymmetric" | "3d"
    bounding_box: [xmin, ymin, zmin, xmax, ymax, zmax]
  characteristic_lengths:
    hydraulic_diameter: 0.01    # m
    total_length: 0.5           # m
  features:
    - { type: "inlet", location: [0, 0, 0], normal: [1, 0, 0], area: 7.854e-5 }
    - { type: "outlet", location: [0.5, 0, 0], normal: [1, 0, 0], area: 7.854e-5 }
    - { type: "wall", description: "pipe walls" }
  stl_files:  # if using snappyHexMesh or external CAD
    - { path: "/path/to/geometry.stl", description: "outer surface" }
```

### 3. Fluid and Solid Properties

```yaml
materials:
  fluids:
    - name: "water"
      phase: "liquid"
      rho: 998.2           # kg/m3
      nu: 1.004e-6          # m2/s, kinematic viscosity
      mu: 0.001002          # Pa·s, dynamic viscosity (alternative to nu)
      cp: 4182.0            # J/(kg·K), optional
      kappa: 0.598          # W/(m·K), thermal conductivity, optional
      beta: 2.07e-4         # 1/K, thermal expansion, optional
      pr: 7.01              # Prandtl number, optional (alternative to cp/kappa)
      temperature_dependence: "constant" | "polynomial" | "table"
  solids:
    - name: "aluminum"
      rho: 2710.0           # kg/m3
      cp: 900.0             # J/(kg·K)
      kappa: 205.0          # W/(m·K)
```

### 4. Flow Regime Estimates

```yaml
flow_regime:
  reference_velocity: 1.0     # m/s
  reference_length: 0.01      # m (hydraulic diameter)
  Re: 9960                    # computed or estimated
  Ma: null                    # for compressible
  flow_type: "laminar" | "transitional" | "turbulent"
  regime_notes: "Re ~ 10,000, transitional regime expected"
```

### 5. Boundary and Initial Conditions

```yaml
boundary_conditions:
  - patch: "inlet"
    type: "patch" | "wall" | "symmetry" | "empty" | "cyclic" | "wedge"
    velocity:
      type: "fixedValue" | "flowRateInletVelocity" | "pressureInletVelocity"
      value: [1.0, 0.0, 0.0]  # m/s
      volumetric_flow_rate: 7.854e-5  # m3/s (alternative)
    pressure:
      type: "zeroGradient" | "fixedValue" | "totalPressure"
      value: null
    temperature:              # optional
      type: "fixedValue"
      value: 300.0            # K
    turbulence:               # optional
      k: { type: "fixedValue" | "turbulentIntensityKineticEnergyInlet", value: ... }
      omega: { type: "fixedValue" | "...", value: ... }
      nut: { type: "calculated" | "...", value: ... }

  - patch: "outlet"
    type: "patch"
    velocity:
      type: "zeroGradient" | "inletOutlet" | "pressureInletOutletVelocity"
    pressure:
      type: "fixedValue" | "fixedMean" | "prghPressure"
      value: 0.0              # Pa (gauge)
    temperature:
      type: "zeroGradient" | "inletOutlet"
    turbulence:
      k: { type: "zeroGradient" }
      omega: { type: "zeroGradient" }
      nut: { type: "zeroGradient" }

  - patch: "walls"
    type: "wall"
    velocity:
      type: "noSlip"
    pressure:
      type: "zeroGradient" | "fixedFluxPressure"
    temperature:
      type: "zeroGradient" | "fixedValue"
      value: null             # if fixedValue
    roughness:
      type: "uniform"
      value: 0.0              # m

initial_conditions:
  velocity: [0.0, 0.0, 0.0]
  pressure: 0.0
  temperature: 300.0          # optional
  turbulence:                 # optional
    k: 0.001
    omega: 100.0
    nut: 0.0
```

### 6. Physical Models

```yaml
physical_models:
  turbulence:
    model: "none" | "laminar" | "kEpsilon" | "kOmega" | "kOmegaSST" | "SpalartAllmaras" | "kOmegaSSTLM"
    wall_functions: "none" | "standard" | "lowRe"
  thermal:
    enabled: false | true
    type: "conjugate" | "buoyancy" | "radiation"
    boussinesq: false | true
    radiation_model: "none" | "P1" | "fvDOM"
  multiphase:
    enabled: false | true
    model: "VOF" | "Eulerian" | "other"
  species_transport: false | true
  combustion: false | true
  moving_mesh: false | true
  dynamic_mesh_type: "none" | "AMI" | "morphing" | "overset"
```

### 7. Mesh Strategy

```yaml
mesh:
  generator: "blockMesh" | "snappyHexMesh" | "cfMesh" | "external"
  cell_count_target: 100000
  refinement:
    near_wall: { layers: 5, expansion_ratio: 1.2, first_cell_height: 0.0001 }
    in_region: [{ box: [xmin, ymin, zmin, xmax, ymax, zmax], level: 2 }]
  quality_thresholds:
    max_non_orthogonality: 65
    max_skewness: 4
    max_aspect_ratio: 100
    min_cell_volume: 1e-15
  mesh_independence:
    required: true | false
    refinement_levels: [0.5, 1.0, 2.0]
    monitored_quantity: "pressure_drop"
```

### 8. Primal Solver Requirements

```yaml
primal_solver:
  application: "simpleFoam"
  steady: true
  schemes:
    convection: "upwind" | "linearUpwind" | "limitedLinear"
    gradient: "Gauss linear"
    laplacian: "Gauss linear corrected"
  solution:
    solvers:
      p: { solver: "GAMG", tolerance: 1e-8, relTol: 0.01 }
      U: { solver: "smoothSolver", tolerance: 1e-8, relTol: 0.01 }
      k: { solver: "smoothSolver", tolerance: 1e-8, relTol: 0.1 }
      omega: { solver: "smoothSolver", tolerance: 1e-8, relTol: 0.1 }
    simple:
      nNonOrthogonalCorrectors: 1
      consistent: true | false
    relaxation:
      p: 0.3
      U: 0.7
      k: 0.7
      omega: 0.7
```

### 9. Optimisation Specification

```yaml
optimisation:
  type: "shape" | "density-topology" | "level-set" | "parameter-sweep" | "external"
  support_level: "native" | "custom" | "external"
  design_variables:
    - name: "alpha" | "porosity" | "boundary_points"
      type: "scalar_field" | "vector_field" | "parametric"
      bounds: [0.0, 1.0]
      initial_value: 1.0
      regularisation:
        type: "Helmholtz" | "Laplace" | "none"
        filter_radius: 0.002
  objectives:
    - name: "pressure_loss"
      weight: 1.0
      type: "minimize"
      target: null
    - name: "flow_uniformity"
      weight: 0.5
      type: "minimize"
      target: null
  constraints:
    - name: "volume_fraction"
      type: "inequality"
      operator: "<="
      value: 0.4
    - name: "max_temperature"
      type: "inequality"
      operator: "<="
      value: 350.0
  multi_objective:
    method: "weighted_sum" | "epsilon_constraint" | "NSGA-II"
    pareto_points: 20
  adjoint:
    solver: "adjointOptimisationFoam" | "adjointShapeOptimizationFoam"
    cost_function: "pressureDrop" | "drag" | "uniformity"
    sensitivity_method: "surface" | "volume"
    step_size: 0.001
    max_iterations: 100
  external_optimizer: null | "DAKOTA" | "pyOpt" | "scipy"
```

### 10. Convergence and Validation Criteria

```yaml
convergence:
  primal:
    residuals:
      p: 1e-6
      U: 1e-6
      k: 1e-6
      omega: 1e-6
      h: 1e-6
    conservation:
      mass_imbalance_tolerance: 1e-6     # relative
      momentum_imbalance_tolerance: 1e-6
    monitor_points: []                   # optional: [x,y,z] points where p, U are tracked
    min_iterations: 500
    max_iterations: 5000
  optimisation:
    objective_change_tolerance: 1e-4
    design_change_tolerance: 1e-3
    max_design_iterations: 100
    constraint_violation_tolerance: 1e-6
```

### 11. Compute Budget and Hardware Configuration

```yaml
compute:
  # Parallelism
  parallelism:
    enabled: true | false
    method: "MPI" | "none"
    np: 4                           # number of MPI ranks (physical cores, not hyperthreads)
    mpi_flavor: "openmpi" | "intel-mpi" | "mpich"
    decomposition_method: "scotch" | "hierarchical" | "simple" | "ptscotch"
    oversubscribe: false            # allow more ranks than physical cores

  # GPU Acceleration
  gpu:
    enabled: true | false
    device: "cuda" | "rocm" | "none"
    purpose: "linear_solver" | "post_processing" | "none"
    requires_petsc_gpu: true | false
    gpu_count: 1

  # Execution Policy
  restart: "none" | "latestTime" | "latestIteration"
  checkpoints: { interval_iterations: 10, keep_last: 3 }
  cleanup_policy: "keep_all" | "keep_reports_only" | "keep_last_checkpoint"
  notification: "none"

  # Performance Estimation (computed, not user-input)
  estimated:
    wall_time_serial_hours: null
    wall_time_parallel_hours: null
    speedup_factor: null
    core_hours_total: null
    storage_required_gb: null
```

When collecting compute preferences from the user, ask only what they haven't specified. Present options using the framework in `references/compute-optimization.md`:

- **For MPI**: Recommend core count based on mesh size (e.g., 10K-50K cells per core). Show estimated speedup.
- **For GPU**: Only offer if hardware and solver support it (check `nvidia-smi`, PETSc CUDA support).
- **For storage**: Estimate based on cell count × timesteps × fields.

### 12. Requested Outputs

```yaml
outputs:
  formats: ["vtk", "csv", "pdf"]
  plots:
    - "convergence_history.png"
    - "velocity_field.png"
    - "pressure_field.png"
    - "design_field_evolution.png"
    - "pareto_front.png"
  reports:
    - "validation_report.md"
    - "simulation_spec.json"
  exports:
    - { type: "cut_plane", location: [0.0, 0.0, 0.0], normal: [0.0, 0.0, 1.0], field: "U" }
    - { type: "streamline", seed: "inlet", field: "U" }
```

### 13. Assumptions and Risk Register

```yaml
assumptions:
  - { field: "flow_regime.Re", value: 9960, basis: "computed from U=1.0, D=0.01, nu=1e-6" }
  - { field: "geometry.pipe_roughness", value: 0.0, basis: "[ASSUMED] smooth walls" }

risks:
  - { description: "mesh quality near bend", severity: "medium", mitigation: "add refinement region" }
  - { description: "transitional Re regime may require low-Re turbulence model", severity: "low", mitigation: "use kOmegaSST" }
```

## Collection Order

When interacting with the user, collect sections in this order, but skip any the user has already provided:

1. Environment target (WSL vs Linux) — usually detected automatically
2. Geometry — the user nearly always knows what they want to simulate
3. Flow conditions — velocity/flow rate, Reynolds number estimate
4. Materials — fluid properties
5. Physical models — turbulence, thermal, multiphase decisions
6. Objectives and constraints — what to optimize
7. Mesh preferences — resolution, quality targets
8. Compute budget — how long, how many cores
9. Output preferences — what results to save

## Units Convention

- All internal storage is SI: meters, seconds, kg, K, Pa, m/s, W
- User may input in any unit system; convert to SI and record the conversion
- Display results in user-friendly units when presenting to the user
- When a value has no explicit unit, ask — never assume
