"""
Launch script for the 3D Model Boundary Selector.

Usage:
    python app.py                    # Start server + open browser
    python app.py --port 8888       # Custom port
    python app.py --no-browser      # Don't open browser
    python app.py --share           # Create Gradio public link

Two modes:
    1. Web mode (default): FastAPI server with Three.js 3D viewer
    2. Gradio mode (--gradio): Gradio app alternative (simpler but less interactive)
"""

import argparse
import sys
import threading
import time
import webbrowser
from pathlib import Path

# Add parent dir to path
sys.path.insert(0, str(Path(__file__).parent))

import uvicorn
from server import app


def launch_web_mode(host: str, port: int, no_browser: bool):
    """Launch the full Three.js-based 3D viewer."""
    url = f"http://{host}:{port}"

    if not no_browser:
        def open_browser():
            time.sleep(1.0)
            print(f"  正在打开浏览器: {url}")
            webbrowser.open(url)
        threading.Thread(target=open_browser, daemon=True).start()

    banner = f"""
{'='*60}
  >> 3D Model Boundary Condition Selector (Web Mode)
{'='*60}

  Features:
    1. Upload STP/STEP/STL/OBJ/GLB files
    2. Rotate/zoom/pan the 3D model
    3. Click faces to select (Shift+click for multi-select)
    4. Assign boundary conditions (inlet/outlet/heat/wall...)
    5. Export config JSON

  Usage:
    - Open browser: {url}
    - Drag & drop or click to upload model file
    - Click faces in 3D view, assign boundaries in right panel
    - Export configuration for simulation

  Press Ctrl+C to stop
{'='*60}
"""
    print(banner)
    uvicorn.run(app, host=host, port=port, log_level="warning")


def launch_gradio_mode(host: str, port: int, share: bool):
    """Launch Gradio-based alternative (simpler UI)."""
    import json
    import tempfile

    import gradio as gr
    from step_parser import export_model_glb, parse_file

    tmp_dir = Path(tempfile.gettempdir()) / "model-viewer"

    def process_file(file):
        if file is None:
            return None, "请上传文件", None, gr.update(choices=[])

        try:
            summary = parse_file(file.name)
            model_id = summary["model_id"]
            glb_path = export_model_glb(model_id, str(tmp_dir))

            # Build face info text
            face_info = []
            face_choices = []
            for fg in summary["face_groups"]:
                n = fg["normal"]
                info = (f"面 #{fg['face_id']}: {fg['face_type']}, "
                       f"面积={fg['area']:.4f}m², "
                       f"法向=({n[0]:.2f},{n[1]:.2f},{n[2]:.2f})")
                face_info.append(info)
                face_choices.append((info, fg["face_id"]))

            info_text = "\n".join(face_info[:20])
            if len(face_info) > 20:
                info_text += f"\n... 共 {len(face_info)} 个面"

            return (
                str(glb_path),  # 3D model display
                f"✅ 已加载: {summary['file_name']}\n"
                f"顶点: {summary['vertex_count']:,} | "
                f"面组: {len(summary['face_groups'])} | "
                f"尺寸: {[round(v,3) for v in summary['bounding_box']['extents']]} m\n\n"
                f"{info_text}",
                summary,
                gr.update(choices=face_choices, value=[]),
            )
        except Exception as e:
            return None, f"❌ 错误: {e}", None, gr.update(choices=[])

    def assign_boundaries(file, selected_faces, bnd_type, bnd_label, current_config):
        if not selected_faces:
            return "请先选择面", current_config

        config = current_config or {"boundaries": {}}

        for face_info, face_id in selected_faces:
            config["boundaries"][str(face_id)] = {
                "type": bnd_type or "wall",
                "label": bnd_label or f"{bnd_type}_{face_id}",
            }

        summary_lines = []
        for face_id, bnd in config["boundaries"].items():
            summary_lines.append(f"  面 #{face_id}: {bnd['type']} ({bnd['label']})")

        return (f"已分配 {len(config['boundaries'])} 个边界条件:\n" +
                "\n".join(summary_lines)), config

    def export_config(config):
        if not config or not config.get("boundaries"):
            return "⚠️ 尚未分配边界条件，请先选择面并分配"

        json_str = json.dumps(config, indent=2, ensure_ascii=False, default=str)
        return json_str

    with gr.Blocks(title="3D 模型边界条件选择器") as demo:
        gr.Markdown("""
        # 🔧 3D 模型边界条件选择器 (Gradio)

        上传 STEP/STP 模型文件，选择面并分配边界条件 (入口、出口、热源、壁面等)
        """)

        current_config = gr.State({})
        current_summary = gr.State(None)

        with gr.Row():
            with gr.Column(scale=2):
                file_input = gr.File(
                    label="📁 上传模型文件",
                    file_types=[".stp", ".step", ".stl", ".obj", ".glb", ".gltf", ".ply"],
                )
                model_3d = gr.Model3D(label="3D 预览", height=500)
                status_text = gr.Textbox(
                    label="模型信息",
                    lines=12,
                    placeholder="上传文件后显示模型信息...",
                )

            with gr.Column(scale=1):
                gr.Markdown("### 🎯 选择面 & 分配边界")

                face_selector = gr.Dropdown(
                    label="选择面 (可多选)",
                    choices=[],
                    multiselect=True,
                    interactive=True,
                )

                with gr.Row():
                    bnd_type = gr.Dropdown(
                        label="边界类型",
                        choices=["inlet", "outlet", "wall", "heat_source", "symmetry", "open"],
                        value="wall",
                    )
                    bnd_label = gr.Textbox(label="标签", placeholder="自定义标签")

                assign_btn = gr.Button("✅ 应用边界条件", variant="primary")
                assign_result = gr.Textbox(label="分配结果", lines=8)

                config_output = gr.Textbox(
                    label="📤 导出配置 JSON",
                    lines=10,
                    placeholder="分配边界后点击导出...",
                )
                export_btn = gr.Button("📋 导出 JSON", variant="secondary")

        # Events
        file_input.change(
            process_file,
            inputs=[file_input],
            outputs=[model_3d, status_text, current_summary, face_selector],
        )

        assign_btn.click(
            assign_boundaries,
            inputs=[file_input, face_selector, bnd_type, bnd_label, current_config],
            outputs=[assign_result, current_config],
        )

        export_btn.click(
            export_config,
            inputs=[current_config],
            outputs=[config_output],
        )

    print(f"""
{'='*60}
  >> 3D Model Boundary Condition Selector (Gradio Mode)
{'='*60}
""")

    demo.launch(
        server_name=host,
        server_port=port,
        share=share,
        inbrowser=not share,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="3D Model Boundary Condition Selector")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind")
    parser.add_argument("--port", type=int, default=8765, help="Port")
    parser.add_argument("--no-browser", action="store_true", help="Don't open browser")
    parser.add_argument("--gradio", action="store_true", help="Use Gradio mode (simpler)")
    parser.add_argument("--share", action="store_true", help="Create public Gradio link")
    args = parser.parse_args()

    if args.gradio:
        launch_gradio_mode(args.host, args.port, args.share)
    else:
        launch_web_mode(args.host, args.port, args.no_browser)
