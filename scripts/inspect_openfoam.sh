#!/usr/bin/env bash
# Step 2: inspect a sourced OpenFOAM installation without jq.
set -u

output="${1:-inspect_openfoam.json}"
if [ -z "${WM_PROJECT_DIR:-}" ] || [ ! -d "${WM_PROJECT_DIR}" ]; then
    printf '%s\n' '{"error":"WM_PROJECT_DIR not set. Source OpenFOAM bashrc first."}' >&2
    exit 1
fi

dist_family="unknown"
if [ -d "$WM_PROJECT_DIR/applications/legacy" ] || grep -qi 'OpenFOAM Foundation' "$WM_PROJECT_DIR/etc/bashrc" 2>/dev/null; then
    dist_family="openfoam_org"
elif grep -Eqi 'OpenCFD|openfoam.com' "$WM_PROJECT_DIR/etc/bashrc" 2>/dev/null; then
    dist_family="openfoam_com"
fi

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

if [ -n "${FOAM_APPBIN:-}" ] && [ -d "$FOAM_APPBIN" ]; then
    find "$FOAM_APPBIN" -maxdepth 1 -type f -printf '%f\n' 2>/dev/null | sort > "$tmp/binaries"
else
    : > "$tmp/binaries"
fi
find "$WM_PROJECT_DIR/applications" -type d \( -iname '*adjoint*' -o -iname '*optimisation*' -o -iname '*optimization*' \) 2>/dev/null | sort > "$tmp/sources"
if [ -n "${FOAM_TUTORIALS:-}" ] && [ -d "$FOAM_TUTORIALS" ]; then
    find "$FOAM_TUTORIALS" -type d \( -iname '*adjoint*' -o -iname '*optimisation*' -o -iname '*optimization*' \) 2>/dev/null | sort > "$tmp/tutorials"
else
    : > "$tmp/tutorials"
fi

export OF_INSPECT_DIST="$dist_family"
python3 - "$output" "$tmp/binaries" "$tmp/sources" "$tmp/tutorials" <<'PY'
import json
import os
import pathlib
import sys

def lines(path):
    return [line for line in pathlib.Path(path).read_text(encoding="utf-8").splitlines() if line]

binaries = lines(sys.argv[2])
sources = lines(sys.argv[3])
tutorials = lines(sys.argv[4])
aliases = (
    "adjointShapeOptimisationFoam", "adjointShapeOptimizationFoam",
    "adjointOptimisationFoam", "adjointOptimizationFoam",
)
apps = {}
for name in aliases:
    binary = next((item for item in binaries if item == name), None)
    source = next((item for item in sources if pathlib.Path(item).name == name), None)
    apps[name] = {
        "availability": "binary" if binary else "source_only" if source else "missing",
        "binary": binary,
        "source": source,
    }
data = {
    "schema_version": "2.0",
    "distribution_family": os.environ["OF_INSPECT_DIST"],
    "version": os.environ.get("WM_PROJECT_VERSION", "unknown"),
    "compiler": os.environ.get("WM_COMPILER", "unknown"),
    "precision": os.environ.get("WM_PRECISION_OPTION", "DP"),
    "label_size": os.environ.get("WM_LABEL_SIZE", "32"),
    "install_root": os.environ["WM_PROJECT_DIR"],
    "available_applications": binaries,
    "optimisation_applications": apps,
    "optimisation_source_dirs": sources,
    "optimisation_tutorial_dirs": tutorials,
}
with open(sys.argv[1], "w", encoding="utf-8", newline="\n") as handle:
    json.dump(data, handle, indent=2, ensure_ascii=False)
    handle.write("\n")
print(json.dumps(data, indent=2, ensure_ascii=False))
PY

if [ "$dist_family" = unknown ]; then
    exit 2
fi
