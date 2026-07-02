#!/usr/bin/env bash
set -euo pipefail
common="$(cd "$(dirname "$0")/../../_common-case" && pwd)"
export SKILL_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
run_dir="${TMPDIR:-/tmp}/openfoam-skill-external-flow-$$"
rm -rf "$run_dir"; mkdir -p "$run_dir"; cp -R "$common/." "$run_dir/"
exec bash "$run_dir/run-baseline.sh"
