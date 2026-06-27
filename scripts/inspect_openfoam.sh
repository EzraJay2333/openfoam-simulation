#!/usr/bin/env bash
# inspect_openfoam.sh — Step 2: OpenFOAM Identity Gate
# Deep-inspects the installed OpenFOAM to determine distribution family,
# version, available solvers, libraries, and tutorials.
# Outputs JSON to stdout and saves to inspect_openfoam.json

set -euo pipefail

output="inspect_openfoam.json"

# --- Pre-check ---
if [ -z "${WM_PROJECT_DIR:-}" ]; then
    echo '{"error": "WM_PROJECT_DIR not set. Source OpenFOAM bashrc first."}'
    exit 1
fi

echo "{" > "$output"

# --- Distribution Family ---
dist_family="unknown"
if [ -d "$WM_PROJECT_DIR/.git" ]; then
    remote=$(cd "$WM_PROJECT_DIR" && git remote get-url origin 2>/dev/null || echo "")
    if echo "$remote" | grep -qi "openfoam.org\|openfoam\.com\|OpenFOAM-dev\|OpenFOAM-[0-9]"; then
        if echo "$remote" | grep -qi "openfoam\.org\|OpenFOAM-[0-9]\|OpenFOAM-dev"; then
            # openfoam.org repos use tags like OpenFOAM-10, OpenFOAM-11, etc.
            dist_family="openfoam.org"
        fi
    fi
    if echo "$remote" | grep -qi "develop.openfoam.com\|openfoam\.com"; then
        dist_family="openfoam.com"
    fi
fi

# Fallback: check etc/bashrc or etc/config.sh for distribution markers
if [ "$dist_family" = "unknown" ]; then
    if [ -f "$WM_PROJECT_DIR/etc/bashrc" ]; then
        if grep -qi "OpenFOAM Foundation\|openfoam.org" "$WM_PROJECT_DIR/etc/bashrc" 2>/dev/null; then
            dist_family="openfoam.org"
        elif grep -qi "OpenCFD\|ESI\|openfoam.com" "$WM_PROJECT_DIR/etc/bashrc" 2>/dev/null; then
            dist_family="openfoam.com"
        fi
    fi
fi

# Fallback: check for distribution-specific directory structures
if [ "$dist_family" = "unknown" ]; then
    if [ -d "$WM_PROJECT_DIR/applications/solvers/incompressible/adjointShapeOptimizationFoam" ]; then
        # Foundation distribution has this older solver name
        dist_family="openfoam.org"
    elif [ -d "$WM_PROJECT_DIR/src/optimisation/adjointOptimisation" ]; then
        # OpenCFD v2206+ has this module
        dist_family="openfoam.com"
    fi
fi

echo '  "distribution_family": "'"$dist_family"'",' >> "$output"

# --- Version ---
echo '  "version": "'"${WM_PROJECT_VERSION:-unknown}"'",' >> "$output"
echo '  "build": "'"${WM_PROJECT_VERSION:-unknown}-${WM_COMPILER:-unknown}"'",' >> "$output"
echo '  "compiler": "'"${WM_COMPILER:-unknown}"'",' >> "$output"
echo '  "precision": "'"${WM_PRECISION_OPTION:-DP}"'",' >> "$output"
echo '  "label_size": "'"${WM_LABEL_SIZE:-32}"'",' >> "$output"

# --- Installation paths ---
echo '  "install_root": "'"$WM_PROJECT_DIR"'",' >> "$output"
echo '  "etc_dir": "'"$WM_PROJECT_DIR/etc"'",' >> "$output"
echo '  "tutorials_dir": "'"${FOAM_TUTORIALS:-$WM_PROJECT_DIR/tutorials}"'",' >> "$output"
echo '  "src_dir": "'"$WM_PROJECT_DIR/src"'",' >> "$output"
echo '  "app_dir": "'"$WM_PROJECT_DIR/applications"'",' >> "$output"

# --- Available solver applications ---
solver_list="[]"
if [ -n "${FOAM_APPBIN:-}" ] && [ -d "$FOAM_APPBIN" ]; then
    solver_list=$(ls "$FOAM_APPBIN"/ 2>/dev/null | grep -i "foam$" | sort | jq -R -s -c 'split("\n") | map(select(length > 0))')
fi
echo '  ,"available_solvers": '"$solver_list"'' >> "$output"

# --- Adjoint/Optimisation capabilities ---
adjoint_solvers=$(echo "$solver_list" | jq -r '.[]' | grep -i "adjoint\|optim" 2>/dev/null || echo "")
echo '  ,"adjoint_solvers_found": '"$(echo "$adjoint_solvers" | jq -R -s -c 'split("\n") | map(select(length > 0))' 2>/dev/null || echo '[]')"'' >> "$output"

# --- Available tutorials ---
adjoint_tutorials="[]"
if [ -n "${FOAM_TUTORIALS:-}" ] && [ -d "$FOAM_TUTORIALS" ]; then
    adjoint_tutorials=$(find "$FOAM_TUTORIALS" -maxdepth 4 -type d \( -iname "*adjoint*" -o -iname "*optim*" -o -iname "*topology*" \) 2>/dev/null | jq -R -s -c 'split("\n") | map(select(length > 0))' || echo "[]")
fi
echo '  ,"adjoint_tutorial_dirs": '"$adjoint_tutorials"'' >> "$output"

# --- Function objects ---
function_objects="[]"
if [ -n "${FOAM_LIBBIN:-}" ]; then
    function_objects=$(find "$FOAM_LIBBIN" -name "lib*functionObjects*" -o -name "lib*forces*" 2>/dev/null | xargs -I{} basename {} 2>/dev/null | sort -u | jq -R -s -c 'split("\n") | map(select(length > 0))' || echo "[]")
fi
echo '  ,"function_object_libraries": '"$function_objects"'' >> "$output"

# --- bashrc/environment script path ---
bashrc_path="unknown"
for candidate in "$WM_PROJECT_DIR/etc/bashrc" "/opt/openfoam"*"/etc/bashrc" "/usr/lib/openfoam/openfoam"*"/etc/bashrc"; do
    if [ -f "$candidate" ]; then
        bashrc_path="$candidate"
        break
    fi
done
echo '  ,"bashrc_path": "'"$bashrc_path"'"' >> "$output"

echo "}" >> "$output"

# --- Summary ---
echo ""
echo "=== OpenFOAM Identity ==="
echo "Distribution: $dist_family"
echo "Version: ${WM_PROJECT_VERSION:-unknown}"
echo "Precision: ${WM_PRECISION_OPTION:-DP}"
echo "Label size: ${WM_LABEL_SIZE:-32}-bit"
echo "Solver count: $(echo "$solver_list" | jq 'length')"
echo "Adjoint solvers: $(echo "$adjoint_solvers" | tr '\n' ' ')"
echo ""
echo "Full output: $output"

exit 0
