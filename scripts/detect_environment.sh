#!/usr/bin/env bash
# detect_environment.sh — Step 1: Environment Gate
# Outputs JSON describing the host OS, WSL status, and OpenFOAM env status.
# The skill reads this output to determine whether to proceed.

set -euo pipefail

output="detected_environment.json"

echo "{" > "$output"

# --- Host OS ---
echo '  "host_os": "'"$(uname -s)"'",' >> "$output"
echo '  "host_kernel": "'"$(uname -r)"'",' >> "$output"
echo '  "architecture": "'"$(uname -m)"'",' >> "$output"

# --- WSL Detection ---
is_wsl=false
wsl_version="none"
if grep -qi microsoft /proc/version 2>/dev/null; then
    is_wsl=true
    if grep -qi "wsl2" /proc/version 2>/dev/null; then
        wsl_version="2"
    else
        wsl_version="1"
    fi
fi
echo '  "is_wsl": '"$is_wsl"',' >> "$output"
echo '  "wsl_version": "'"$wsl_version"'",' >> "$output"

# --- Shell ---
echo '  "shell": "'"$(basename "$SHELL" 2>/dev/null || echo "unknown")"'",' >> "$output"

# --- MPI ---
mpi_available=false
mpi_flavors="[]"
if command -v mpirun &>/dev/null; then
    mpi_available=true
    mpi_info=$(mpirun --version 2>&1 | head -1 || echo "unknown")
    mpi_flavors="[\"$(echo "$mpi_info" | tr '"' "'")\"]"
fi
echo '  "mpi_available": '"$mpi_available"',' >> "$output"
echo '  "mpi_flavors": '"$mpi_flavors"',' >> "$output"

# --- OpenFOAM Environment ---
of_env_loaded=false
WM_PROJECT_DIR="${WM_PROJECT_DIR:-}"
WM_PROJECT_VERSION="${WM_PROJECT_VERSION:-}"
WM_OPTIONS="${WM_OPTIONS:-}"
FOAM_APPBIN="${FOAM_APPBIN:-}"
FOAM_LIBBIN="${FOAM_LIBBIN:-}"

if [ -n "$WM_PROJECT_DIR" ] && [ -d "$WM_PROJECT_DIR" ]; then
    of_env_loaded=true
fi

echo '  "of_env_loaded": '"$of_env_loaded"',' >> "$output"
echo '  "WM_PROJECT_DIR": "'"$WM_PROJECT_DIR"'",' >> "$output"
echo '  "WM_PROJECT_VERSION": "'"$WM_PROJECT_VERSION"'",' >> "$output"
echo '  "WM_OPTIONS": "'"$WM_OPTIONS"'",' >> "$output"
echo '  "FOAM_APPBIN": "'"$FOAM_APPBIN"'",' >> "$output"
echo '  "FOAM_LIBBIN": "'"$FOAM_LIBBIN"'",' >> "$output"

# --- Python ---
python_version=$(python3 --version 2>&1 || echo "not found")
echo '  "python_version": "'"$python_version"'",' >> "$output"

python_packages="{}"
if command -v python3 &>/dev/null; then
    numpy_ver=$(python3 -c "import numpy; print(numpy.__version__)" 2>/dev/null || echo "missing")
    mpl_ver=$(python3 -c "import matplotlib; print(matplotlib.__version__)" 2>/dev/null || echo "missing")
    python_packages="{\"numpy\": \"$numpy_ver\", \"matplotlib\": \"$mpl_ver\"}"
fi
echo '  "required_python_packages": '"$python_packages"',' >> "$output"

# --- Distribution Detection (Linux distro) ---
distro="unknown"
distro_version="unknown"
if [ -f /etc/os-release ]; then
    distro=$(grep "^ID=" /etc/os-release | cut -d= -f2 | tr -d '"')
    distro_version=$(grep "^VERSION_ID=" /etc/os-release | cut -d= -f2 | tr -d '"')
fi
echo '  "linux_distribution": "'"$distro"'",' >> "$output"
echo '  "linux_distribution_version": "'"$distro_version"'"' >> "$output"

echo "}" >> "$output"

# --- Summary ---
echo ""
echo "=== Environment Detection Summary ==="
echo "Host: $(uname -s) $(uname -r) ($(uname -m))"
echo "WSL: $is_wsl (v$wsl_version)"
echo "Linux: $distro $distro_version"
echo "Shell: $(basename "$SHELL" 2>/dev/null || echo unknown)"
echo "MPI: $mpi_available ($mpi_info 2>/dev/null || echo)"
echo "OpenFOAM env: $of_env_loaded"
if [ "$of_env_loaded" = true ]; then
    echo "  WM_PROJECT_DIR: $WM_PROJECT_DIR"
    echo "  WM_PROJECT_VERSION: $WM_PROJECT_VERSION"
    echo "  WM_OPTIONS: $WM_OPTIONS"
fi
echo "Python: $python_version"
echo "  numpy: $(echo "$python_packages" | grep -o '"numpy": "[^"]*"' | cut -d'"' -f4)"
echo "  matplotlib: $(echo "$python_packages" | grep -o '"matplotlib": "[^"]*"' | cut -d'"' -f4)"
echo ""
echo "Full output: $output"

# Exit with appropriate code
if [ "$of_env_loaded" != true ]; then
    echo "WARNING: OpenFOAM environment not loaded."
    echo "  Source your OpenFOAM bashrc, e.g.:"
    echo "    source /opt/openfoam2312/etc/bashrc"
    echo "    source /usr/lib/openfoam/openfoam2312/etc/bashrc"
    exit 1
fi

exit 0
