#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
blockMesh 2>&1 | tee log.blockMesh
checkMesh 2>&1 | tee log.checkMesh
foamRun 2>&1 | tee log.foamRun
python3 "${SKILL_ROOT:?SKILL_ROOT is required}/scripts/create_run_manifest.py" . \
    --command blockMesh --command checkMesh --command foamRun
