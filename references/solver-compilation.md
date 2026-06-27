# Solver Compilation

## Purpose

After Step 6 identifies the required solver capabilities, this reference guides the decision: use an existing binary, compile from provided source, modify and compile, or integrate a third-party solver.

## When to Enter This Module

Enter when any of these conditions is true:
- The capability-matched solver is not found in `$FOAM_APPBIN/`
- Solver source exists in `$FOAM_SOLVERS/` or `$WM_PROJECT_DIR/applications/solvers/` but is not compiled
- The problem requires physics beyond the solver's documented capabilities (needs source modification)
- The solver is marked as `custom` or `external` support level
- User explicitly requests a custom solver

## Decision Tree

Present the user with a clear choice after analysis. Never compile without user confirmation.

```
1. DETECT what exists
   ├── Binary in $FOAM_APPBIN/ → Step A: Use as-is (fastest, verified)
   ├── Source in $FOAM_SOLVERS/ → Step B: Compile from official source
   ├── Source needs modification → Step C: Patch and compile
   └── No matching source exists → Step D: Third-party or custom development
```

### Step A: Use Existing Binary

If a compiled binary already provides the required capabilities:

```bash
# Verify binary exists and check capabilities
ls -la $FOAM_APPBIN/<solverName>
$FOAM_APPBIN/<solverName> -help 2>&1 | head -50
```

**User presentation:**
```
✅ Found: <solverName> (pre-compiled, ready to use)
   Location: $FOAM_APPBIN/<solverName>
   Capabilities: [list from -help]
   No compilation needed.

Proceed with this solver? [Y/n]
```

### Step B: Compile from Official Source

When solver source exists but is not compiled (common with modular solvers, contributed applications, or legacy solvers):

**Detection:**

```bash
# Find solver source
find $FOAM_SOLVERS -name "<solverName>.C" 2>/dev/null
find $WM_PROJECT_DIR/applications -name "<solverName>.C" 2>/dev/null

# Check for Make/ files
ls -la <solver-source-dir>/Make/
```

**Compilation procedure (Foundation / openfoam.org):**

```bash
# OpenFOAM-13 and later use the modular build system
cd <solver-source-dir>
wmake          # Compile single application
wmake -j 4    # Parallel compile (4 cores)
```

```bash
# Older Foundation versions and some contributed solvers
cd <solver-source-dir>
wmake
```

**Compilation procedure (OpenCFD / openfoam.com):**

```bash
cd <solver-source-dir>
wmake          # Standard compile
wmake -j 8    # Parallel compile
```

**Check compilation success:**

```bash
# Verify binary was created
ls -la $FOAM_APPBIN/<solverName>
$FOAM_APPBIN/<solverName> -help 2>&1 | head -20
```

**User presentation:**
```
⚙️  Source found: <solverName>.C
   Source location: <path>
   This solver's source is included with your OpenFOAM installation but needs compilation.

Compilation options:
  A) I'll compile it myself — here are the exact commands
  B) Guide me through the compilation step by step
  C) Skip compilation, use an alternative solver

Estimated compilation time: <1-5 minutes>
Disk space: ~5-20 MB
Requires sudo: no (compiles to user-writable $FOAM_USER_APPBIN)
```

### Step C: Patch and Compile

When the existing solver needs modification (e.g., adding an energy equation for CHT, custom boundary condition, new objective function):

**Procedure:**

1. Copy the solver source to user directory:
   ```bash
   # Foundation (OpenFOAM-13)
   cp -r $FOAM_SOLVERS/<category>/<originalSolver> $WM_PROJECT_USER_DIR/applications/solvers/<newSolverName>
   # OpenCFD
   cp -r $FOAM_SOLVERS/<category>/<originalSolver> $WM_PROJECT_USER_DIR/applications/solvers/<newSolverName>
   ```

2. Rename files and update references:
   ```bash
   cd $WM_PROJECT_USER_DIR/applications/solvers/<newSolverName>
   mv <originalSolver>.C <newSolverName>.C
   # Update Make/files to reflect the new name
   ```

3. Apply patches/changes to the source code. Common patterns:

   | Modification | Where | What to add |
   |-------------|-------|------------|
   | Add energy equation | `createFields.H` | `#include "createTeqn.H"` |
   | Add passive scalar | `createFields.H` | `#include "createScalarEqn.H"` |
   | Custom boundary condition | Source `.C` file | New BC lookup and application |
   | Additional objective | Adjoint dict / cost function | New cost term computation |
   | Brinkman penalty term | `UEqn.H` | `-fvm::Sp(alpha, U)` |

4. Compile:
   ```bash
   wmake
   ```

5. Verify:
   ```bash
   $FOAM_USER_APPBIN/<newSolverName> -help 2>&1 | head -30
   ```

**User presentation:**
```
🔧 Solver modification required: <solverName>
   Reason: <capability gap description>
   Changes needed: [list of source file modifications]

Options:
  A) Apply the modifications and compile now (I'll write the patch)
  B) Show me the diff first, then I'll decide
  C) I'll modify the code myself — just tell me which files to change
  D) Use an alternative approach (external optimizer, different solver)

Changes: ~10-50 lines across 1-3 files
Compilation time: ~2-10 minutes
Risk: modifications may introduce bugs — smoke-run validation mandatory
```

### Step D: Third-Party Solver Integration

When no OpenFOAM source provides the required capability and external code is needed:

```
📦 External solver required: <solverName>
   Capability gap: <description>

Options:
  A) Install <external-package> and compile — I'll provide the full guide
  B) Download and apply a published OpenFOAM extension
     URL: <link to repository/paper supplementary material>
  C) Skip — use a different optimization strategy (parameter sweep, external optimizer)

External packages may require: git, cmake, additional dependencies
Installation time: ~15-60 minutes
```

## Compilation Troubleshooting

### Common Issues

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `wmake: command not found` | OpenFOAM env not sourced | `source $WM_PROJECT_DIR/etc/bashrc` |
| `fatal error: <header>.H not found` | Missing include path | Check `Make/options`, add `-I$(LIB_SRC)/...` |
| `undefined reference to ...` | Missing linked library | Add `-l<libraryName>` to `Make/options` |
| `error: no match for 'operator='` | API change between versions | Check version-specific API docs |
| `Make/linux64GccDPInt32Opt/...permission denied` | Wrong ownership of FOAM_USER_APPBIN | `mkdir -p $FOAM_USER_APPBIN && chmod 755 $FOAM_USER_APPBIN` |

### Environment Verification Before Compilation

```bash
# All of these must be set
echo "WM_PROJECT_DIR=$WM_PROJECT_DIR"
echo "WM_OPTIONS=$WM_OPTIONS"
echo "FOAM_APPBIN=$FOAM_APPBIN"
echo "FOAM_USER_APPBIN=$FOAM_USER_APPBIN"
which wmake
gcc --version | head -1
```

## Safety Rules for Compilation

- **Never** compile or install to system directories (no `sudo wmake`, no writing to `/opt/`)
- **Always** compile to user directories (`$FOAM_USER_APPBIN`, `$WM_PROJECT_USER_DIR`)
- **Always** preserve the original source — copy, don't modify in place
- **Always** record the git commit or diff of any source changes for reproducibility
- **Always** verify the compiled binary with `-help` before using it in a case
- **Always** run the smoke test (Step 9c) with the compiled solver before a full run
