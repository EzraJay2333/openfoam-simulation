# OpenFOAM Error Diagnostics

Use this reference only after preserving the failing case, dictionaries, mesh report and complete log.

## Failure routing

| Signal | Required checks | Stop condition |
|---|---|---|
| Dictionary or lookup error | Run `foamDictionary -expand`; verify version-specific object and keyword names | Any parse or lookup failure |
| Floating point exception | Check dimensions, zero/negative properties, initial fields, mesh volume and turbulence variables | Repeats in a bounded smoke run |
| Diverging residuals | Check BC compatibility, relaxation, mesh quality, initialisation and reverse flow | Residuals grow for five consecutive iterations |
| Conservation failure | Compare all inlet/outlet fluxes and inspect unassigned/internal patches | Relative imbalance exceeds the approved tolerance |
| Parallel-only failure | Re-run serially; inspect decomposition, processor boundaries and MPI version | Serial succeeds but parallel remains non-reproducible |

Never delete failed logs. Write the diagnosis, attempted recovery and result to `run_manifest.json` and the validation report.
