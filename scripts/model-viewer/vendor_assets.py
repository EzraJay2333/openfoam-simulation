#!/usr/bin/env python3
"""Copy pinned Three.js browser modules from node_modules into static/vendor."""

import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "node_modules" / "three"
DEST = HERE / "static" / "vendor"
FILES = {
    "LICENSE": "THREE_LICENSE.txt",
    "build/three.module.min.js": "three.module.min.js",
    "examples/jsm/controls/OrbitControls.js": "OrbitControls.runtime.js",
    "examples/jsm/loaders/GLTFLoader.js": "GLTFLoader.runtime.js",
    "examples/jsm/utils/BufferGeometryUtils.js": "BufferGeometryUtils.js",
}

if not SOURCE.is_dir():
    raise SystemExit("node_modules/three is missing; run npm install in scripts/model-viewer")
for source, target in FILES.items():
    shutil.copy2(SOURCE / source, DEST / target)
loader = DEST / "GLTFLoader.runtime.js"
loader.write_text(
    loader.read_text(encoding="utf-8").replace("../utils/BufferGeometryUtils.js", "./BufferGeometryUtils.js"),
    encoding="utf-8",
    newline="\n",
)
print(f"Vendored {len(FILES)} Three.js files into {DEST}")
