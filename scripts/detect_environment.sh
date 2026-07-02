#!/usr/bin/env bash
# Step 1: detect Linux/WSL, MPI, Python and sourced OpenFOAM state.
set -u

output="${1:-detected_environment.json}"
is_wsl=false
wsl_version="none"
if grep -qi microsoft /proc/version 2>/dev/null; then
    is_wsl=true
    wsl_version="2"
fi

mpi_available=false
mpi_info=""
if command -v mpirun >/dev/null 2>&1; then
    mpi_available=true
    mpi_info="$(mpirun --version 2>&1 | head -n 1)"
fi

of_env_loaded=false
if [ -n "${WM_PROJECT_DIR:-}" ] && [ -d "${WM_PROJECT_DIR}" ]; then
    of_env_loaded=true
fi

distro="unknown"
distro_version="unknown"
if [ -r /etc/os-release ]; then
    distro="$(. /etc/os-release; printf '%s' "${ID:-unknown}")"
    distro_version="$(. /etc/os-release; printf '%s' "${VERSION_ID:-unknown}")"
fi

export OF_DETECT_HOST_OS="$(uname -s)"
export OF_DETECT_HOST_KERNEL="$(uname -r)"
export OF_DETECT_ARCH="$(uname -m)"
export OF_DETECT_IS_WSL="$is_wsl"
export OF_DETECT_WSL_VERSION="$wsl_version"
export OF_DETECT_SHELL="$(basename "${SHELL:-unknown}")"
export OF_DETECT_MPI="$mpi_available"
export OF_DETECT_MPI_INFO="$mpi_info"
export OF_DETECT_LOADED="$of_env_loaded"
export OF_DETECT_DISTRO="$distro"
export OF_DETECT_DISTRO_VERSION="$distro_version"

python3 - "$output" <<'PY'
import importlib.metadata
import json
import os
import platform
import sys

def package_version(name):
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "missing"

data = {
    "schema_version": "2.0",
    "host_os": os.environ["OF_DETECT_HOST_OS"],
    "host_kernel": os.environ["OF_DETECT_HOST_KERNEL"],
    "architecture": os.environ["OF_DETECT_ARCH"],
    "is_wsl": os.environ["OF_DETECT_IS_WSL"] == "true",
    "wsl_version": os.environ["OF_DETECT_WSL_VERSION"],
    "shell": os.environ["OF_DETECT_SHELL"],
    "mpi_available": os.environ["OF_DETECT_MPI"] == "true",
    "mpi_flavors": [os.environ["OF_DETECT_MPI_INFO"]] if os.environ["OF_DETECT_MPI_INFO"] else [],
    "of_env_loaded": os.environ["OF_DETECT_LOADED"] == "true",
    "WM_PROJECT_DIR": os.environ.get("WM_PROJECT_DIR", ""),
    "WM_PROJECT_VERSION": os.environ.get("WM_PROJECT_VERSION", ""),
    "WM_OPTIONS": os.environ.get("WM_OPTIONS", ""),
    "FOAM_APPBIN": os.environ.get("FOAM_APPBIN", ""),
    "FOAM_LIBBIN": os.environ.get("FOAM_LIBBIN", ""),
    "python_version": platform.python_version(),
    "required_python_packages": {"numpy": package_version("numpy"), "matplotlib": package_version("matplotlib")},
    "linux_distribution": os.environ["OF_DETECT_DISTRO"],
    "linux_distribution_version": os.environ["OF_DETECT_DISTRO_VERSION"],
}
with open(sys.argv[1], "w", encoding="utf-8", newline="\n") as handle:
    json.dump(data, handle, indent=2, ensure_ascii=False)
    handle.write("\n")
print(json.dumps(data, indent=2, ensure_ascii=False))
PY

if [ "$of_env_loaded" != true ]; then
    printf '%s\n' "WARNING: OpenFOAM environment not loaded." >&2
    exit 1
fi
