# Q Comet v016 readiness note (2026-09-11)

## What v016 is

`qcomet_sollumz_v016.blend` = v015 rig + a production UV pass. Built in the live Blender 5.2.1 / Sollumz 2.9 session from a fresh reload of `qcomet_sollumz_v015.blend`; recipe `tools/blender/build_qcomet_uvs_v016.py` (also stored as a text block inside the file). v013, v014 and v015 are untouched. No `.yft` / `.ytd` / `.ybn` exists or was fabricated.

## In-memory Sollumz fragment audit

| check | result |
|---|---|
| fragment asset constructed | True |
| skeleton bones / physics children / vehicle windows | 24 / 21 / 6 |
| models per LOD (high, med, low, vlow) | 1, 1, 1, 1 |
| Sollumz warnings / errors | 0 / 0 (v015 had 88 UV warnings) |
| game_ready | False |

## Dash text (7 FONT-derived meshes)

The text-to-mesh conversion had named the UV layer `UVMap`, so Sollumz saw no `UVMap 0`. Each text slab now has an aspect-preserving planar unwrap in its own dash plane (thin axis = normal facing the cabin, u = +X = driver's right, v = +Z), 2 % padding, written to `UVMap 0` and `UVMap 1` on the authoring mesh, the `exp_` model and its three LODs. All seven share `qcomet_export_022` (vehicle_lightsemissive); a single emissive text atlas can be painted against these 0..1 islands later, or each can be given its own texture.

| text | plane size | UVMap 0 bounds |
|---|---|---|
| dash_battery | 29 x 12 mm | [0.02, 0.2966, 0.98, 0.7034] |
| dash_speed | 16 x 25 mm | [0.1917, 0.02, 0.8083, 0.98] |
| dash_speed_units | 23 x 8 mm | [0.02, 0.3268, 0.98, 0.6732] |
| dash_touch_label_1 | 21 x 7 mm | [0.02, 0.343, 0.98, 0.657] |
| dash_touch_label_2 | 29 x 7 mm | [0.02, 0.3871, 0.98, 0.6129] |
| dash_touch_label_3 | 22 x 7 mm | [0.02, 0.3476, 0.98, 0.6524] |
| dash_touch_label_4 | 26 x 7 mm | [0.02, 0.3728, 0.98, 0.6272] |

## Glass (15 vehglass meshes: 9 visual + 6 physics twins)

`vehicle_vehglass` samples TexCoord0..2; the third set was missing. `UVMap 2` is now a per-pane 0..1 planar projection in the pane's own plane (plane fitted by principal components because the panes are solidified slabs; normal pointed away from the cabin; u = horizontal tangent, v = up the pane; roof glass uses +X / +Y). Physics twins take the frame from their visual mesh through the bone matrix, so `exp_`/`phys_` pairs carry identical UVs. `UVMap 0` and `UVMap 1` on glass are unchanged.

| pane | outward normal | in-plane size (m) |
|---|---|---|
| windscreen | (-0.00, +0.47, +0.88) | 1.85 x 0.82 |
| windscreen_r | (+0.00, -0.45, +0.89) | 1.90 x 0.79 |
| window_lf | (-0.90, +0.02, +0.44) | 1.00 x 0.40 |
| window_rf | (+0.90, +0.02, +0.44) | 1.00 x 0.40 |
| window_lr | (-0.91, -0.00, +0.42) | 0.86 x 0.39 |
| window_rr | (+0.91, -0.00, +0.42) | 0.86 x 0.39 |
| glass_quarter_dside | (-0.83, -0.04, +0.55) | 0.72 x 0.40 |
| glass_quarter_pside | (+0.83, -0.04, +0.55) | 0.72 x 0.40 |
| panoramic_glass_greenhouse | (-0.00, -0.02, +1.00) | 1.47 x 1.04 |

## Still proxies (not blocking export, but not production)

- `UVMap 0` / `UVMap 1` on every body, interior, light and glass mesh are the v015 axis-aligned projections in raw metres, not authored unwraps. The 8x8 palette images are placeholders.
- LOD meshes are automatic decimation candidates.
- Hinge sweeps, entry clearance, damage, handling/meta, in-game spawn and performance are uncertified.
- Dimensions remain provisional pending Quasar's sheet.

## Next

1. Real Sollumz export of Fragment `qcomet` from this file into a scratch resource, then a clean-server spawn test (human).
2. Author `UVMap 0` unwraps and textures for paint, glass and interior; replace palette proxies.
3. Human test checklist before any publish or sale.

Evidence: `uv_validation.json` (per-mesh layers, frames, UV bounds), `native_export_audit.log` (empty = no Sollumz messages), `job_status.json`.
