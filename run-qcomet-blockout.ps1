$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$blenderExe = "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
$scriptPath = Join-Path $projectRoot "tools\blender\create_qcomet_blockout.py"
$outputPath = Join-Path $projectRoot "vehicles\qcomet\source\blender\qcomet_blockout_v001.blend"

if (-not (Test-Path $blenderExe)) {
    throw "Blender was not found at: $blenderExe"
}

if (-not (Test-Path $scriptPath)) {
    throw "Q Comet blockout script was not found at: $scriptPath"
}

Write-Host "Creating the Q Comet blockout..."
& $blenderExe --background --python $scriptPath -- --output $outputPath

if ($LASTEXITCODE -ne 0) {
    throw "Blender returned exit code $LASTEXITCODE"
}

if (-not (Test-Path $outputPath)) {
    throw "Blender finished without creating: $outputPath"
}

Write-Host "Q Comet blockout created successfully:"
Write-Host $outputPath
Write-Host "Open this .blend file in Blender for visual inspection."
