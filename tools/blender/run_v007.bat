@echo off
"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" --background --python "%~dp0build_qcomet_body_v007.py" -- --output "%~dp0..\..\vehicles\qcomet\source\blender\qcomet_body_v007.blend" --review-dir "%~dp0..\..\vehicles\qcomet\source\blender\review_v007" > "%~dp0v007_run.log" 2>&1
echo EXITCODE=%ERRORLEVEL% >> "%~dp0v007_run.log"
