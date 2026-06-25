# Compute Optimization

## Purpose

Guide the user through compute resource configuration: MPI parallel decomposition, GPU acceleration options, and performance estimation. Present options with trade-offs; let the user decide.

## When to Enter This Module

- Step 3 (Structured Intake): Collect compute preferences
- Step 9 (Staged Execution): Apply chosen parallelization strategy
- Anytime the user asks about performance, speedup, or GPU

## Decision Flow

```
1. PROFILE the case
   ├── Mesh cell count → determines decomposition strategy
   ├── Solver type → determines GPU compatibility
   ├── Transient vs steady → determines parallel efficiency
   └── Available hardware → determines ceiling

2. PRESENT options
   ├── Serial (baseline, always available)
   ├── MPI parallel (multi-core CPU)
   ├── GPU acceleration (if solver supports it)
   └── Hybrid MPI+GPU (large cases)

3. USER CHOOSES → apply configuration
```

## Option A: MPI Parallel (CPU Multi-Core)

### When to Use

- **Always recommended** for cases with >50,000 cells
- Required for transient cases with >100 timesteps
- Scalable up to ~10,000-50,000 cells per core (sweet spot)

### Decomposition Methods

| Method | Best For | Efficiency |
|--------|----------|-----------|
| `simple` | Uniform meshes, any size | Good baseline, moderate communication overhead |
| `hierarchical` | Structured/blockMesh meshes | Better for anisotropic meshes |
| `scotch` | Unstructured meshes, complex geometry | Best load balancing, lower communication |
| `ptscotch` | Large clusters (>16 cores) | Parallel decomposition creation |

### Configuration

```bash
# system/decomposeParDict
FoamFile { version 2.0; format ascii; class dictionary; object decomposeParDict; }

numberOfSubdomains  <np>;  // = number of physical cores (not hyperthreads)

method  <scotch|hierarchical|simple>;

// For simple/hierarchical:
simpleCoeffs { n (<nx> <ny> <nz>); }
hierarchicalCoeffs { n (<nx> <ny> <nz>); order xyz; }
```

### Execution Commands

```bash
# Decompose the mesh and fields (once)
decomposePar 2>&1 | tee log.decomposePar

# Run solver in parallel
mpirun -np <np> <solver> -parallel 2>&1 | tee log.<solver>

# Reconstruct results for post-processing
reconstructPar 2>&1 | tee log.reconstructPar
# Or reconstruct only latest time:
reconstructPar -latestTime
```

### CPU Core Count Recommendation

| Mesh Size | Recommended Cores | Why |
|-----------|------------------|-----|
| <10,000 cells | 1 (serial) | Overhead > benefit |
| 10K-100K cells | 2-4 | Modest speedup |
| 100K-1M cells | 4-16 | Sweet spot |
| 1M-10M cells | 16-64 | Good scaling |
| >10M cells | 32-128+ | Requires cluster; check interconnect |

### Performance Estimation

```
Estimated speedup:
  S = N / (1 + α(N-1))
  where N = number of cores, α ≈ 0.05-0.15 (serial fraction)

  Example: 100K cells on 8 cores → ~5-6× speedup
           1M cells on 32 cores → ~12-18× speedup
```

**User presentation:**
```
🖥️  MPI Parallel Configuration
   Case: <n> cells, <steady/transient>
   Recommended: <min> - <max> cores
   Available: <detected-cores> logical cores on this system

Options:
  A) <recommended-np> cores (recommended — ~<speedup>× speedup)
  B) Custom core count: ___
  C) Serial (no parallelization)

Decomposition method: scotch (default for best load balancing)
```

## Option B: GPU Acceleration

### When GPU Helps

GPU acceleration in OpenFOAM is available but limited:

| What GPU Accelerates | Supported? | Solvers |
|---------------------|-----------|---------|
| Linear solver (AMG, CG) | ✅ Partial | `simpleFoam`, `pimpleFoam` (OpenCFD v2312+ with PETSc) |
| Full solver assembly | ❌ Not yet | — |
| Post-processing | ✅ | ParaView Volume Rendering |
| Adjoint equations | ❌ Not natively | — |

### GPU Configuration (OpenCFD v2312+)

```bash
# Requires PETSc compiled with CUDA/HIP support
# In system/fvSolution:
solvers {
    p {
        solver          petsc;
        petsc {
            options {
                "-ksp_type cg"
                "-pc_type gamg"
                "-mat_type aijcusparse"  # GPU sparse matrix
                "-vec_type cuda"          # GPU vectors
            }
        }
    }
}
```

### GPU Availability Check

```bash
# Check for CUDA
nvidia-smi 2>/dev/null && echo "CUDA GPU available" || echo "No CUDA GPU detected"
nvcc --version 2>/dev/null || echo "CUDA toolkit not installed"

# Check for ROCm (AMD)
rocm-smi 2>/dev/null && echo "ROCm GPU available" || echo "No ROCm GPU detected"

# Check PETSc with GPU
petsc-config --has-cuda 2>/dev/null && echo "PETSc has CUDA support" || echo "PETSc without CUDA"

# Check OpenFOAM GPU awareness
foamHasLibrary libcgpu 2>/dev/null && echo "GPU library available" || echo "No GPU library"
```

**User presentation:**
```
🎮 GPU Acceleration
   GPU detected: <yes/no, model, VRAM>
   
GPU acceleration is currently limited in OpenFOAM:
  ✅ Linear solver acceleration (PETSc+CUDA) — OpenCFD v2312+
  ❌ Full GPU solver — not available yet
  ✅ ParaView volume rendering — always available

Options:
  A) Enable GPU for linear solvers (requires PETSc+CUDA setup)
  B) Skip GPU — use CPU only (recommended for most cases)
  C) Use GPU for post-processing only (ParaView)
```

## Option C: Hybrid MPI + GPU

For large cases (>5M cells) with GPU hardware:

```
MPI handles: domain decomposition, inter-process communication, I/O
GPU handles: per-rank linear solver acceleration

Required: PETSc with CUDA + MPI, OpenCFD v2312+
```

## Compute Budget Integration

Before launching a full run, present the cost estimate:

```
📊 Compute Estimate
   Case: <name>, <n> cells, <steady/transient>
   
   Option 1: Serial
      Wall time: ~<estimate>
      Core-hours: ~<estimate>
   
   Option 2: MPI (<np> cores)
      Wall time: ~<estimate>
      Core-hours: ~<estimate>
   
   Option 3: MPI + GPU (<np> cores + GPU)
      Wall time: ~<estimate>
      Core-hours: ~<estimate>

Choose option [1/2/3] or enter custom configuration.
```

## Performance Monitoring During Run

```bash
# Monitor parallel efficiency
tail -f log.<solver> | grep "ExecutionTime"

# Check load balance
foamLog log.<solver>
grep "Execution" logs/executionTime_0

# GPU utilization (if applicable)
nvidia-smi dmon -s u -d 2  # every 2 seconds
```

## Parallel I/O Optimization

For large cases on network filesystems:

```bash
# system/controlDict
writeFormat     binary;      // Binary is faster than ASCII
writePrecision   8;           // 8 is sufficient for most cases
writeCompression off;         // Off during run; compress after
runTimeModifiable no;         // Slight perf gain

// For large transient cases:
writeInterval    100;         // Don't write every timestep
purgeWrite       2;           // Keep only 2 most recent time dirs
```
