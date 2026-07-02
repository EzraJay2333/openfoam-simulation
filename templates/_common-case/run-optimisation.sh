#!/usr/bin/env bash
set -euo pipefail
solver="${1:-}"
if [ -z "$solver" ] || ! command -v "$solver" >/dev/null 2>&1; then
    printf '%s\n' "STOP: requested optimisation solver is not compiled. Verify source and obtain explicit compilation approval." >&2
    exit 3
fi
printf '%s\n' "Solver available: $solver. Full optimisation still requires an approved simulation_spec.json." >&2
exit 4
