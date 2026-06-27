#!/usr/bin/env bash
# validate_case.sh — Step 8: Case Structure and Dictionary Validation
# Usage: validate_case.sh <case_directory>
# Validates that an OpenFOAM case has correct structure, parsable dictionaries,
# and consistent boundary conditions.

set -euo pipefail

CASE_DIR="${1:-.}"

if [ ! -d "$CASE_DIR" ]; then
    echo '{"error": "Case directory not found: '"$CASE_DIR"'"}'
    exit 1
fi

cd "$CASE_DIR"

output="case_validation.json"
echo "{" > "$output"
echo '  "case_directory": "'"$(realpath "$CASE_DIR")"'",' >> "$output"

# --- Required directories ---
checks="{}"

has_0=false
has_constant=false
has_system=false

[ -d "0" ] && has_0=true
[ -d "constant" ] && has_constant=true
[ -d "system" ] && has_system=true

echo '  "directories": {' >> "$output"
echo '    "0": '"$has_0"',' >> "$output"
echo '    "constant": '"$has_constant"',' >> "$output"
echo '    "system": '"$has_system"'' >> "$output"
echo '  },' >> "$output"

all_dirs_ok=true
if [ "$has_0" != true ] || [ "$has_constant" != true ] || [ "$has_system" != true ]; then
    all_dirs_ok=false
fi

# --- PolyMesh ---
has_polymesh=false
if [ -d "constant/polyMesh" ] && [ -f "constant/polyMesh/boundary" ]; then
    has_polymesh=true
fi
echo '  "polymesh": '"$has_polymesh"',' >> "$output"

# --- Dictionary syntax check ---
dict_errors="[]"
for d in system/* 0/* constant/*; do
    if [ -f "$d" ]; then
        if ! foamDictionary -expand "$d" > /dev/null 2>&1; then
            err=$(foamDictionary -expand "$d" 2>&1 | head -5)
            dict_errors=$(echo "$dict_errors" | jq -c '. + [{"file": "'"$d"'", "error": "'"$(echo "$err" | tr '\n' ' ' | sed 's/"/\\"/g")"'"}]')
        fi
    fi
done 2>/dev/null || true
echo '  "dictionary_errors": '"$dict_errors"',' >> "$output"

# --- Required files check ---
required_files="[]"
if [ -f "system/controlDict" ]; then
    required_files=$(echo "$required_files" | jq -c '. + ["controlDict: found"]')
else
    required_files=$(echo "$required_files" | jq -c '. + ["controlDict: MISSING"]')
fi
if [ -f "system/fvSchemes" ]; then
    required_files=$(echo "$required_files" | jq -c '. + ["fvSchemes: found"]')
else
    required_files=$(echo "$required_files" | jq -c '. + ["fvSchemes: MISSING"]')
fi
if [ -f "system/fvSolution" ]; then
    required_files=$(echo "$required_files" | jq -c '. + ["fvSolution: found"]')
else
    required_files=$(echo "$required_files" | jq -c '. + ["fvSolution: MISSING"]')
fi
if [ -f "constant/transportProperties" ] || [ -f "constant/physicalProperties" ]; then
    required_files=$(echo "$required_files" | jq -c '. + ["transportProperties: found"]')
else
    required_files=$(echo "$required_files" | jq -c '. + ["transportProperties: MISSING"]')
fi

echo '  "required_files": '"$required_files"',' >> "$output"

# --- Boundary condition presence check ---
bc_check="{}"
if [ -f "0/U" ]; then
    patches=$(foamDictionary -entry boundaryField -value 0/U 2>/dev/null | grep -oP '^\s*\K\w+' || echo "")
    bc_check=$(echo "$bc_check" | jq -c '. + {"U": {"patches": "'"$(echo "$patches" | tr '\n' ' ')"'"}}')
fi
if [ -f "0/p" ] || [ -f "0/p_rgh" ]; then
    p_file="0/p"
    [ -f "0/p_rgh" ] && p_file="0/p_rgh"
    patches=$(foamDictionary -entry boundaryField -value "$p_file" 2>/dev/null | grep -oP '^\s*\K\w+' || echo "")
    bc_check=$(echo "$bc_check" | jq -c '. + {"p": {"patches": "'"$(echo "$patches" | tr '\n' ' ')"'"}}')
fi
echo '  "boundary_conditions_summary": '"$bc_check"',' >> "$output"

# --- Overall result ---
dict_ok=false
if [ "$dict_errors" = "[]" ]; then
    dict_ok=true
fi

all_ok=false
if [ "$all_dirs_ok" = true ] && [ "$dict_ok" = true ]; then
    all_ok=true
fi

echo '  "all_dirs_present": '"$all_dirs_ok"',' >> "$output"
echo '  "all_dicts_valid": '"$dict_ok"',' >> "$output"
echo '  "overall_valid": '"$all_ok"'' >> "$output"

echo "}" >> "$output"

# --- Summary ---
echo ""
echo "=== Case Validation: $(basename "$(realpath "$CASE_DIR")") ==="
echo "Directories: 0/=$has_0 constant/=$has_constant system/=$has_system"
echo "polyMesh: $has_polymesh"
echo "Dictionary errors: $(echo "$dict_errors" | jq 'length')"
if [ "$dict_errors" != "[]" ]; then
    echo "  $(echo "$dict_errors" | jq -r '.[] | "\(.file): \(.error)"')"
fi
echo "Required files: $(echo "$required_files" | jq -r '.[]')"
echo "Overall valid: $all_ok"
echo ""
echo "Full output: $output"

if [ "$all_ok" != true ]; then
    exit 1
fi
exit 0
