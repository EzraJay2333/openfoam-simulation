#!/usr/bin/env bash
# Step 9: validate case structure, dictionaries and patch coverage.
set -u

case_dir="${1:-.}"
output="${2:-case_validation.json}"
if [ ! -d "$case_dir" ]; then
    printf '{"error":"Case directory not found: %s"}\n' "$case_dir" >&2
    exit 1
fi
if ! command -v foamDictionary >/dev/null 2>&1; then
    printf '%s\n' '{"error":"foamDictionary not found; source OpenFOAM bashrc first."}' >&2
    exit 2
fi

case_dir="$(realpath "$case_dir")"
errors_file="$(mktemp)"
patches_file="$(mktemp)"
trap 'rm -f "$errors_file" "$patches_file"' EXIT

while IFS= read -r -d '' dictionary; do
    if ! message="$(foamDictionary -expand "$dictionary" 2>&1 >/dev/null)"; then
        printf '%s\t%s\n' "${dictionary#$case_dir/}" "${message//$'\n'/ }" >> "$errors_file"
    fi
done < <(find "$case_dir/0" "$case_dir/constant" "$case_dir/system" -maxdepth 1 -type f -print0 2>/dev/null)

if [ -d "$case_dir/0" ]; then
    for field in "$case_dir"/0/*; do
        if [ -f "$field" ]; then
            patch_list="$(foamDictionary -entry boundaryField -keywords "$field" 2>/dev/null | paste -sd, -)"
            printf '%s\t%s\n' "$(basename "$field")" "$patch_list" >> "$patches_file"
        fi
    done
fi

python3 - "$case_dir" "$errors_file" "$patches_file" "$output" <<'PY'
import json
import pathlib
import re
import sys

case = pathlib.Path(sys.argv[1])
errors = []
for line in pathlib.Path(sys.argv[2]).read_text(encoding="utf-8").splitlines():
    name, _, message = line.partition("\t")
    errors.append({"file": name, "error": message})

directories = {name: (case / name).is_dir() for name in ("0", "constant", "system")}
required_names = ("system/controlDict", "system/fvSchemes", "system/fvSolution")
required = {name: (case / name).is_file() for name in required_names}
required["constant/physicalProperties_or_transportProperties"] = (
    (case / "constant/physicalProperties").is_file() or (case / "constant/transportProperties").is_file()
)
boundary_file = case / "constant/polyMesh/boundary"
mesh_patches = set()
if boundary_file.is_file():
    text = boundary_file.read_text(encoding="utf-8", errors="replace")
    mesh_patches = set(re.findall(r"(?m)^\s{4}([A-Za-z_][\w.-]*)\s*$", text))

field_patches = {}
for line in pathlib.Path(sys.argv[3]).read_text(encoding="utf-8").splitlines():
    field, _, raw_patches = line.partition("\t")
    field_patches[field] = sorted(item for item in raw_patches.split(",") if item)

mismatches = {}
if mesh_patches:
    for field, patches in field_patches.items():
        missing = sorted(mesh_patches - set(patches))
        extra = sorted(set(patches) - mesh_patches)
        if missing or extra:
            mismatches[field] = {"missing": missing, "extra": extra}

ok = all(directories.values()) and all(required.values()) and not errors and not mismatches
data = {
    "schema_version": "2.0",
    "case_directory": str(case),
    "directories": directories,
    "polymesh": boundary_file.is_file(),
    "required_files": required,
    "dictionary_errors": errors,
    "mesh_patches": sorted(mesh_patches),
    "field_patches": field_patches,
    "boundary_mismatches": mismatches,
    "overall_valid": ok,
}
output = pathlib.Path(sys.argv[4])
if not output.is_absolute():
    output = case / output
output.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
print(json.dumps(data, indent=2, ensure_ascii=False))
raise SystemExit(0 if ok else 1)
PY
