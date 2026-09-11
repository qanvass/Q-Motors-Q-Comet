$ErrorActionPreference = "Stop"
$blender = "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
$script = "C:\Users\Qanva\Desktop\Gaming GTA\Q-Motors-Q-Comet\tools\blender\build_qcomet_body_v007.py"
$out = "C:\Users\Qanva\Desktop\Gaming GTA\Q-Motors-Q-Comet\vehicles\qcomet\source\blender\qcomet_body_v007.blend"
$review = "C:\Users\Qanva\Desktop\Gaming GTA\Q-Motors-Q-Comet\vehicles\qcomet\source\blender\review_v007"
New-Item -ItemType Directory -Force -Path $review | Out-Null
& $blender --background --python $script -- --output $out --review-dir $review
exit $LASTEXITCODE
