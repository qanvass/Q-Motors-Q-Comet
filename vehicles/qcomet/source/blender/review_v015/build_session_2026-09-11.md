# v015 build session report (2026-09-11, Claude Code / Fable 5.1)

## Outcome

`qcomet_sollumz_v015.blend` was built in the live Blender 5.2.1 session (port 9876, not restarted) from a clean reload of `qcomet_vehicle_v013.blend` and saved once. No `.yft`, `.ytd`, or `.ybn` was written. The on-disk v013 source was not modified (still 00:49, 7,521,306 bytes). No checkpoint copy or `.blend1` side file was created.

| item | value |
|---|---|
| input | qcomet_vehicle_v013.blend (clean on load, checkpoint copy skipped) |
| fragment bones | 24 |
| export models (exp_*) | 234 |
| native collision bounds | 21 |
| shader materials / palette textures | 25 / 28 |
| in-memory Sollumz fragment audit | constructed = True, skeleton bones 24, physics children 21, vehicle windows 6, models per LOD {'0': 1, '1': 1, '2': 1, '3': 1} |
| rest-pose / pivot / wheel-center error (m) | 0.0e+00 / 3.0e-08 / 0.0e+00 |
| blockers | 0 |
| warnings | 92 |
| game_ready | False (unchanged: needs human checklist) |

## What had to change to get a clean run

Four failed attempts preceded the good one (their logs are kept as `*.prev_*` files in this folder). All fixes live in `tools/blender/build_qcomet_sollumz_v015.py`; the user's Sollumz install was not edited.

1. **Stale guard** (00:42 attempt): script demanded `qcomet_cabin_v014.blend`; widened to accept the newer, more complete v013 (see `guard_repair_2026-09-11.md`).
2. **Sollumz 2.9.0 bug, `ydr.shader_materials_v2.get_shader_config`** (01:31 attempt): local `texture` is never initialised, so vehicle shaders with Dirt/Damage samplers raise `UnboundLocalError`. Patched in memory (`_patch_sollumz_shader_config`).
3. **`hull()` duplicate vertices** (01:35 attempt): a vertex can be in both `geom_interior` and `geom_unused` of `bmesh.ops.convex_hull`; `bmesh.ops.delete` rejects duplicates. De-duplicated.
4. **Sollumz 2.9.0 bug, `shared.shader_expr.compiler.Compiler`** (01:37 attempt): its node caches are class-level dicts shared by every instance, so after a file reload the compiler links to dead nodes (`outputs[0] out of range`). Patched in memory to give each compiler fresh caches (`_patch_sollumz_compiler_caches`).
5. **Vertex colour naming** (01:39 attempt saved a file, but its audit failed): Sollumz 2.9 expects `Color 1` / `Color 2` (see `tools.meshhelper.get_color_attr_name`), the script wrote `Colour0` / `Colour1`. That produced 482 'missing color attributes' warnings and crashed vehglass shattermap generation on a missing `Colour0` field. Renamed; the 01:42 rebuild is the one on disk.

Process note: a second agent (Cursor) was editing the same script and driving the same Blender session during this window. Each of my rebuilds therefore started with an explicit reload of the on-disk v013 rather than trusting the live scene. Only one agent should drive port 9876 at a time.

## Remaining warnings (non-blocking)

- 60 x missing UVMap 2
- 28 x missing UVMap 0
- 4 x script-declared provisional gate

The `UVMap 0` warnings are the FONT-derived dash text meshes (dash_speed, dash_battery, dash labels); the `UVMap 2` warnings are the glass meshes, whose vehglass shader samples a third UV set the script does not generate. Both are texture-authoring work, not rig problems.

## Not certified (unchanged gates)

- No in-game spawn, hinge-sweep, damage, or performance test has been run.
- Palette textures and projection UVs are structural proxies, not production bakes.
- LOD meshes are automatic decimation candidates pending silhouette review.
- Dimensions remain provisional pending Quasar's sheet; `game_ready` stays False.

See `rig_validation.json` (full report), `readiness.md` (script summary), `native_export_audit.log` (Sollumz log from the in-memory audit) and `job_status.json`.
