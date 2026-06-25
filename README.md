# OpenFOAM Simulation Skill

[![English](https://img.shields.io/badge/lang-English-blue)](README.md)
[![简体中文](https://img.shields.io/badge/lang-简体中文-red)](README_CN.md)

12-step OpenFOAM fluid simulation skill for Claude Code — plan, build, run, validate, and document CFD simulations on Linux/WSL. Specializes in fluid topology/shape optimization with a self-learning knowledge base.

## Quick Install

### Option A: Download .skill File

1. Download [`openfoam-simulation.skill`](https://github.com/EzraJay2333/openfoam-simulation/releases/latest/download/openfoam-simulation.skill) from Releases
2. In Claude Code, drag the file into the chat or run:
   ```
   /install-skill openfoam-simulation.skill
   ```

### Option B: Git Clone

```bash
git clone https://github.com/EzraJay2333/openfoam-simulation.git ~/.claude/skills/openfoam-simulation
```

The skill activates on next Claude Code restart. No additional setup required.

## Requirements

- **OS**: Linux (native) or WSL2 (Windows 11)
- **OpenFOAM**: Foundation (openfoam.org) v10+ or OpenCFD (openfoam.com) v2206+
- **Python**: 3.x with numpy, matplotlib
- **ParaView**: Optional, for post-processing visualization

The skill **never** installs OpenFOAM or system software — it only detects what exists.

## What It Does

| Step | What Happens |
|------|-------------|
| 1 | Detects environment (WSL/Linux, MPI, OpenFOAM paths) |
| 2 | Identifies OpenFOAM distribution, version, available solvers |
| 3 | Collects structured simulation parameters (13 categories) |
| 4 | Consults local docs before online sources (5-level evidence hierarchy) |
| 5 | Classifies problem (flow regime, physics, geometry, optimization type) |
| 6 | Matches solver capabilities to problem fingerprint |
| 7 | **Decides solver source**: use binary / compile / modify+compile / third-party |
| 8 | Matches or creates workflow from learned knowledge base |
| 9 | Constructs reproducible case directory |
| 10 | **Staged execution**: syntax → mesh → smoke → primal → adjoint → compute config → full run |
| 11 | Validates convergence, conservation, mesh quality, physical plausibility |
| 12 | **Records learning candidate** for future reuse |

### Pre-loaded Classic Templates

| Template | Problem | Optimization |
|----------|---------|-------------|
| `internal-flow-pressure-loss` | Duct/bend/manifold pressure drop | Shape + Topology |
| `external-flow-drag` | Aerodynamic drag reduction | Shape |
| `duct-shape-optimization` | Bend/diffuser/nozzle contour | Shape + Multi-objective |
| `porous-density-topology` | Heat sink / fluid network | Density Topology + CHT |

### Compute Optimization

- **MPI parallel**: Recommended core counts, Amdahl's Law speedup estimates, decomposition method selection
- **GPU**: Availability check, CUDA/ROCm support, PETSc integration guidance

### Learning System

Each successful simulation type is recorded as a `learned-workflow`. New problem types start as `experimental`, promote to `validated` after clean rerun + user approval, and deprecate when OpenFOAM versions break compatibility.

## File Structure

```
openfoam-simulation/
├── SKILL.md                        # Core skill (300 lines, 12-step state machine)
├── README.md                       # This file
├── references/
│   ├── intake-schema.md            # 13-section parameter specification
│   ├── documentation-policy.md     # 5-level evidence hierarchy
│   ├── solver-selection.md         # Capability-based solver matching
│   ├── solver-compilation.md       # Compile/modify/third-party decision tree
│   ├── topology-optimization.md    # Shape vs topology vs level-set taxonomy
│   ├── compute-optimization.md     # MPI/GPU configuration and estimation
│   └── validation-and-convergence.md  # 7-stage validation gates + ParaView
├── registry/
│   ├── solvers.yaml                # 16 solver capabilities + 3 external tools
│   ├── problem-types.yaml          # 13-dimension classification system
│   └── learned-workflows/          # Auto-populated learning records
├── templates/                      # 4 pre-loaded classic workflow templates
├── scripts/
│   ├── detect_environment.sh       # Step 1: WSL/Linux/OpenFOAM detection
│   ├── inspect_openfoam.sh         # Step 2: distribution/version/solver identity
│   ├── validate_case.sh            # Step 9: case structure validation
│   └── scaffold_learning_record.py # Step 12: learning candidate generation
└── evals/
    └── evals.json                  # 6 test scenarios with assertions
```

## Trigger Phrases

The skill activates when you mention any of:
- OpenFOAM, foam, blockMesh, snappyHexMesh
- simpleFoam, pimpleFoam, adjointOptimisationFoam, adjointShapeOptimizationFoam
- CFD simulation, flow simulation, fluid simulation
- Topology optimization, shape optimization, adjoint optimization
- Pressure loss optimization, drag minimization, heat transfer simulation
- Mesh generation, parametric CFD sweeps
- "simulate flow", "optimize a duct/pipe/channel/wing/heat-sink"

## Version

v1.0 — June 2026

## License

MIT
