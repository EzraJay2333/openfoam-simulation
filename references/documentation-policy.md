# Documentation Policy

## Evidence Hierarchy

When making any consequential solver, scheme, boundary condition, or dictionary decision, consult sources in this exact order. Record the source for every decision.

### Level 1: Installed Executable Help

The highest-authority source is the binary installed on the user's system.

```bash
# Primary commands (in order of preference)
<application> -help
foamInfo <application>
foamSearch <keyword>
```

Record the exact output and the command used. If `-help` describes a parameter differently from online documentation, the `-help` output takes precedence — it reflects the installed version.

### Level 2: Installed Local Resources

Within the OpenFOAM installation directory (`$WM_PROJECT_DIR`):

| Resource | Path | When to Consult |
|----------|------|----------------|
| Tutorials | `$WM_PROJECT_DIR/tutorials/` | Verify that a capability exists for the installed version |
| Source code | `$WM_PROJECT_DIR/src/` | Resolve dictionary parameter meaning, defaults, constraints |
| API documentation | `$WM_PROJECT_DIR/doc/` | Understand class hierarchy and options |
| etc directory | `$WM_PROJECT_DIR/etc/` | Default dictionaries, controlDict templates, case templates |
| applications | `$WM_PROJECT_DIR/applications/` | Solver source and options |

```bash
# Search patterns
find $WM_PROJECT_DIR/tutorials -name "*adjoint*" -type d
find $WM_PROJECT_DIR/tutorials -name "*topology*" -type d
find $WM_PROJECT_DIR/src -path "*optimisation*" -name "*.H"
foamDictionary -entry <entry> -expand <dict-file>
```

### Level 3: Official Online Documentation

Only after local sources are exhausted. Use the version-matched URL:

| Distribution | Documentation URL |
|-------------|-------------------|
| Foundation (org) | `https://cpp.openfoam.org/v<major>/` or `https://openfoam.org/documentation/` |
| OpenCFD (com) | `https://www.openfoam.com/documentation/guides/v<version>/` |

When fetching online documentation:
1. Pin the search to the specific version detected in Step 2
2. Prefer the API guide and user guide over forum posts
3. For dictionary entries, cross-reference with `foamDictionary -expand` on the installed version

### Level 4: Peer-Reviewed Literature

For numerical methods, validation benchmarks, and optimisation algorithm references. Cite the DOI or title. Literature provides context but does not override version-specific solver behavior.

### Level 5: Community Sources

CFD Online, cfd-online.com forums, GitHub issues. Mark these clearly as `[COMMUNITY]` sources. May be used for troubleshooting specific error messages but never as the sole authority for solver selection or boundary condition specification.

## Distribution Safety Rules

### Never Mix Foundation and OpenCFD Instructions

Foundation (`openfoam.org`) and OpenCFD (`openfoam.com`) distributions have diverged significantly since OpenFOAM v3.0+. They differ in:

- Solver and utility names (e.g., `adjointShapeOptimizationFoam` vs `adjointOptimisationFoam`)
- Dictionary keyword naming and structure
- Boundary condition implementations and options
- Turbulence model interfaces
- Function object syntax

**Rule:** If the user's installation is Foundation, use only Foundation documentation. If OpenCFD, use only OpenCFD documentation. The one exception: when a peer-reviewed paper explicitly maps and verifies the difference on the same version range, and you verify the mapping against the installed `-help` output.

### Version Qualification

Prefix every solver or dictionary recommendation with the distribution and version it was verified against:

```
Verified: simpleFoam on OpenCFD v2312
Source: local -help output, $FOAM_TUTORIALS/incompressible/simpleFoam/pitzDaily
```

## Documentation Audit Trail

For every Step 4 invocation, produce a short audit record:

```yaml
documentation_audit:
  - decision: "Use adjointOptimisationFoam for pressure-loss topology optimisation"
    distribution: "openfoam.com"
    version: "2312"
    sources:
      - { level: 1, command: "adjointOptimisationFoam -help", result: "supports porous drag objectives" }
      - { level: 2, path: "$WM_PROJECT_DIR/tutorials/incompressible/adjointOptimisationFoam", matches: ["pitzDaily", "bend"] }
      - { level: 3, url: "https://www.openfoam.com/documentation/guides/v2312/...", note: "confirms objective function syntax" }
    rejected_alternatives:
      - { solver: "adjointShapeOptimizationFoam", reason: "Foundation-only solver, not present in OpenCFD v2312" }
      - { solver: "simpleFoam + custom porosity", reason: "lacks native adjoint; would require external optimizer" }
```

If no documentation exists for a specific combination, record that fact explicitly:

```yaml
- decision: "Use kOmegaSST for transitional bend flow"
  sources:
    - { level: 1, note: "no version-specific documentation found in -help" }
    - { level: 5, note: "[COMMUNITY] Recommended in cfd-online.com thread #xxx for similar Re range" }
  caveat: "Standard practice, not validated for this specific geometry"
```

## Using foamHelp and Related Tools

Some OpenFOAM installations include `foamHelp`, `foamInfo`, or `foamSearch`. Check availability and use them:

```bash
# Check which help tools exist
which foamHelp 2>/dev/null || echo "foamHelp not available"
which foamInfo 2>/dev/null || echo "foamInfo not available"

# Use if available
foamHelp -help                    # list available help types
foamHelp boundaryConditions       # list boundary condition types
foamHelp schemes                  # list discretisation schemes
foamInfo <boundary-condition>     # describe a specific bc
foamSearch <keyword>              # search documentation
```
