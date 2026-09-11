# Q Motors — Q Comet

Production starter for an original, lore-safe FiveM vehicle.

## Current state

This package contains the approved concept sheets, a locked art brief, a project manifest, a reference validator, and a Blender automation script that creates an editable first-pass blockout.

It is **not yet a sellable FiveM vehicle**. The final `.yft`, `.ytd`, collision, LODs, rigging, materials, metadata, handling, and in-game testing still require Blender + Sollumz and a private FiveM development server.

## First run

1. Install a Blender version supported by the current Sollumz release.
2. Open Blender's **Scripting** workspace.
3. Open `tools/blender/create_qcomet_blockout.py`.
4. Press **Run Script**.
5. Save the result as `vehicles/qcomet/source/blender/qcomet_blockout_v001.blend`.
6. Review the provisional dimensions in `vehicles/qcomet/project.json` before detailed modeling.

Run the local reference check with:

```bash
pnpm validate
```

## Orientation

- `+Y`: vehicle front
- `+X`: vehicle right/passenger side
- `+Z`: up
- Origin: vehicle center at ground level

## Commercial boundary

Sell only after the vehicle has been rebuilt as original 3D geometry, tested, and delivered through the current Cfx/Tebex process. Do not advertise NoPixel approval or compatibility. Players cannot install this vehicle into NoPixel themselves.
