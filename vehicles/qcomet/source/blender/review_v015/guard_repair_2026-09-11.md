# v015 guard repair — session report (2026-09-11)

## Health check: blocked

The `blender-mcp` server at `127.0.0.1:9876` failed to connect this session
(`CONNECTION_CLOSED`). The required first step — confirm filepath, object
count, and that Sollumz is loaded in the live scene — could not be run.
Per `CLAUDE.md` ("inspect only" if a port is already being mutated, and no
screenshot spam), and because building `qcomet_sollumz_v015.blend` requires
mutating the live file, **no build was attempted and no `.blend` was
written**. Everything below is static analysis of files already on disk.

## Why the guard was wrong

`tools/blender/build_qcomet_sollumz_v015.py` refused to run unless the active
file was `qcomet_cabin_v014.blend`. File timestamps and the two milestone
reports show that guard was pointing at a stale target:

| file | saved | what its own report says |
|---|---|---|
| `qcomet_cabin_v014.blend` | 00:22 | `review_v014/cabin_validation.json` — cabin-only geometry/sightline checks, no hinging/lights/collision claim |
| v015 build attempt | 00:42 | failed: active file was `qcomet_vehicle_v013.blend`, guard required v014 |
| `qcomet_vehicle_v013.blend` | 00:49 (newest) | `review_v013/milestone123_completion_report.json` — `"status": "VEHICLE_V013_RIG_COMPLETE"`, M1 (cabin) + M2 (hinging) + M3 (sollumz prep: lights, collision, hierarchy) all present |

`vehicle_v013.blend` was saved *after* both `cabin_v014.blend` and the failed
v015 run, and it is the only one of the two whose own report claims the full
M1–M3 rig. It is the newer, more complete file.

## Why "just widen the guard" was not enough

Cross-checking `build_qcomet_sollumz_v015.py`'s literal `bpy.data.objects[...]`
lookups against `vehicle_v013.blend`'s own object-hierarchy dump (in its
completion report) found two real mismatches that would have crashed the
script mid-rebuild, after it had already started mutating the file:

- The script expects pre-rename window objects `glass_dside_f`, `glass_pside_f`,
  `glass_dside_r`, `glass_pside_r`, `glass_rear`. v013's report shows these are
  **already** named `window_lf`, `window_rf`, `window_lr`, `window_rr` (and
  `glass_rear` already exists under that name, so only that one rename was
  ever going to work).
- The script indexes `tail_bar_running` directly to anchor the rear indicator
  strip geometry. v013's full object-tree dump has no such object — only
  `tail_bar_brake`, which is a different mesh at a different position and is
  not a safe stand-in.

These are inferred from the JSON completion reports only, not from the live
scene (unreachable this session) — they should be re-confirmed once
`blender-mcp` is back up, but they are a strong enough signal that running the
old script unmodified against `vehicle_v013.blend` was not safe.

## What changed in `build_qcomet_sollumz_v015.py`

1. **Guard widened**: accepts `qcomet_vehicle_v013.blend` or
   `qcomet_cabin_v014.blend` (prefers v013 as the more complete milestone;
   still refuses anything else, by name, with both accepted names in the
   error).
2. **Window rename made idempotent**: renames `glass_*` → `window_*`/
   `windscreen_r` only if the old name is present; if the target name already
   exists, leaves it alone instead of raising `KeyError`.
3. **New `preflight()` pass**: checks every object this script indexes by
   literal name (windows, both headlight blade-2 lamps, both mirrors,
   `tail_bar_running`, all four doors and door cards, bonnet, boot, all four
   wheels, windscreen) *before any mutation*, and raises one aggregated,
   itemized `RuntimeError` if anything is missing — instead of an opaque
   `KeyError` after the file has already been partially rewritten. It
   explicitly refuses to substitute `tail_bar_brake` for the missing
   `tail_bar_running` rather than guessing.
4. **De-hardcoded `v014`-specific naming**: the authoring-archive collection
   name, the legacy-root/authoring object rename prefixes, the checkpoint
   filename, and the `readiness.md` note now all derive from whichever input
   file is actually active, instead of assuming v014.

Verified with `python -m py_compile` (syntax only — `bpy`/`bmesh` are not
importable outside Blender, so this cannot confirm the script runs
correctly, only that it parses).

## Not done, and why

- **No `qcomet_sollumz_v015.blend` was created.** Producing one requires
  actually running this script inside Blender against real geometry;
  synthesizing one any other way (e.g. copying/renaming an existing file)
  would be a fabricated authoring file, which this project's rules forbid in
  spirit as much as they forbid fabricating `.yft`/`.ytd`/`.ybn`.
- **No `.yft`/`.ytd`/`.ybn` was fabricated** — none was ever at risk this
  session; the script only produces those via a real Sollumz export, which
  still has not happened.
- **The two naming mismatches above are not resolved**, only detected and
  gated. Whether `vehicle_v013.blend` truly lacks a `tail_bar_running` mesh
  (or it exists under yet another name) needs a live look, not another guess.

## Next steps once `blender-mcp` reconnects

1. Confirm with the health check (filepath, object count, Sollumz loaded)
   that `qcomet_vehicle_v013.blend` is the intended, currently-loaded file.
2. Run `build_qcomet_sollumz_v015.py`. If `preflight()` reports missing
   objects, resolve each by name in the live scene (rename, locate, or add
   the mesh) rather than patching the script to skip the check.
3. Only after a clean run should `vehicles/qcomet/source/blender/qcomet_sollumz_v015.blend`
   and the script's own `rig_validation.json` / `readiness.md` /
   `native_export_audit.log` be written under `review_v015/`.
