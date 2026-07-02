#!/usr/bin/env bash
exec bash "$(dirname "$0")/../../_common-case/run-optimisation.sh" "${1:-adjointOptimisationFoam}"
