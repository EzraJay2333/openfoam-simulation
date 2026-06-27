@echo off
cd /d "%~dp0"
echo.
echo ============================================================
echo   ^>^> 3D 模型边界条件选择器
echo ============================================================
echo.
echo   启动模式:
echo     [1] Web 模式 (推荐 - 完整 3D 交互查看器)
echo     [2] Gradio 模式 (简化版)
echo.
set /p choice="  请选择 (1/2): "

if "%choice%"=="2" (
    python app.py --gradio
) else (
    python app.py
)
pause
