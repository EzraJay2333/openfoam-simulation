"""
Agent-callable face picker tool.
Parses a model file, opens a pick-mode browser window,
waits for user to select ONE face, returns structured face data.

Usage by agent:
    from pick_face import pick_face
    result = pick_face("path/to/model.stp", label="请选择入口面")
    # result = {"face_id": 3, "area": 0.5, "centroid": [...], ...}

Usage standalone:
    python pick_face.py <model_file> [--label "选择入口面"]
"""

import json
import os
import shutil
import sys
import threading
import time
import urllib.parse
import urllib.request
import uuid
import webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import uvicorn
from server import STATIC_DIR, TEMP_DIR, parse_model_safely, register_model_paths
from server import app as fastapi_app
from step_parser import export_model_glb

SERVER_URL = "http://127.0.0.1:8765"


def _http_post(url: str, data: dict) -> dict:
    """Simple HTTP POST helper (no external deps)."""
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


def _http_get(url: str) -> dict:
    """Simple HTTP GET helper."""
    with urllib.request.urlopen(url) as resp:
        return json.loads(resp.read().decode())


def pick_face(model_path: str, label: str = "请点击选择一个面", port: int = 8765) -> dict:
    """
    Parse a model file, open a browser window for the user to pick ONE face,
    and return the selected face's data. Blocks until user picks or timeout.

    Args:
        model_path: Path to model file (.stp, .step, .stl, .obj, .glb, etc.)
        label: Prompt text shown to the user
        port: Server port (default 8765)

    Returns:
        dict with face_id, area, centroid, normal, face_type, triangle_count
    """
    global SERVER_URL
    SERVER_URL = f"http://127.0.0.1:{port}"

    model_path = os.path.abspath(model_path)
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"模型文件不存在: {model_path}")

    print(f"\n{'='*60}")
    print("  智能体面选择工具")
    print(f"  模型: {Path(model_path).name}")
    print(f"  提示: {label}")
    print(f"{'='*60}\n")

    # 1. Parse the model
    summary = parse_model_safely(model_path)
    model_id = summary["model_id"]
    print(f"  解析完成: {len(summary['face_groups'])} 个面组, "
          f"尺寸: {[round(v,3) for v in summary['bounding_box']['extents']]} m")

    # 2. Export GLB and copy to static
    glb_path = export_model_glb(model_id, str(TEMP_DIR))
    static_glb = STATIC_DIR / f"{model_id}.glb"
    shutil.copy2(glb_path, static_glb)
    # Also copy face group map JSON
    fgmap_path = glb_path.replace(".glb", "_fgmap.json")
    if os.path.exists(fgmap_path):
        shutil.copy2(fgmap_path, STATIC_DIR / f"{model_id}_fgmap.json")
    register_model_paths(
        model_id,
        [Path(glb_path), static_glb, STATIC_DIR / f"{model_id}_fgmap.json"],
        summary["file_name"],
    )

    # 3. Generate pick session ID
    pick_id = uuid.uuid4().hex[:12]

    # 4. Ensure server is running
    _ensure_server_running(port)

    # 5. Open browser in pick mode
    encoded_label = urllib.parse.quote(label)
    pick_url = f"{SERVER_URL}/pick?pick_id={pick_id}&model_id={model_id}&label={encoded_label}"
    print(f"  打开选择窗口: {pick_url}")
    webbrowser.open(pick_url)

    # 6. Poll for result via HTTP (server runs in different process)
    print("  等待用户选择面...")
    timeout = 300  # 5 minutes
    poll_interval = 0.5  # seconds
    elapsed = 0

    while elapsed < timeout:
        try:
            resp = _http_get(f"{SERVER_URL}/api/pick-result/{pick_id}")
            if resp.get("ready"):
                result = resp["result"]
                faces = result.get("faces", [])
                count = result.get("count", len(faces))

                print(f"\n  >>> 用户选择了 {count} 个面")

                out = {
                    "model_id": model_id,
                    "file_name": summary["file_name"],
                    "count": count,
                    "faces": [],
                }

                for f in faces:
                    fd = f.get("face_data", {})
                    fid = f.get("face_id", -1)
                    print(f"     面 #{fid}: area={fd.get('area','?'):.4f} m², "
                          f"normal=({fd.get('normal',[0,0,0])[0]:.2f},{fd.get('normal',[0,0,0])[1]:.2f},{fd.get('normal',[0,0,0])[2]:.2f})")
                    out["faces"].append({
                        "face_id": fid,
                        **fd,
                    })

                return out
        except Exception:
            # Server might not be ready yet
            pass

        time.sleep(poll_interval)
        elapsed += poll_interval

    raise TimeoutError(f"面选择超时 ({timeout}秒)")


_server_thread = None


def _ensure_server_running(port: int = 8765) -> None:
    """Start the FastAPI server in a background thread if not already running."""
    global _server_thread
    import socket

    # Check if port is already in use
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    port_in_use = sock.connect_ex(('127.0.0.1', port)) == 0
    sock.close()

    if port_in_use:
        return  # Already running

    def run_server():
        uvicorn.run(fastapi_app, host="127.0.0.1", port=port, log_level="warning")

    _server_thread = threading.Thread(target=run_server, daemon=True)
    _server_thread.start()
    time.sleep(2)  # Wait for startup
    print(f"  服务器已启动: http://127.0.0.1:{port}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Agent Face Picker")
    parser.add_argument("model_file", help="Path to model file")
    parser.add_argument("--label", "-l", default="请点击选择一个面", help="Prompt shown to user")
    parser.add_argument("--port", type=int, default=8765, help="Server port")
    args = parser.parse_args()

    try:
        result = pick_face(args.model_file, args.label, port=args.port)
        print("\n--- RESULT (JSON) ---")
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    except Exception as e:
        print(f"\n选择失败: {e}")
        sys.exit(1)
