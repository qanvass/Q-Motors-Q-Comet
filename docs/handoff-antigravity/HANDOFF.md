# Antigravity handoff — Q Motors Q Comet

Date: 2026-09-11  
Owner: Quasar  
Repo: `C:\Users\Qanva\Desktop\Gaming GTA\Q-Motors-Q-Comet`  
Product: `qcomet` (public name **Q Comet**, manufacturer **Q Motors**)  
This is an original fictional FiveM / GTA V vehicle. Read `AGENTS.md` first.

You are taking over the **live Blender car**. One writer only. Do not drive port `9876` if another agent (Claude Code / Fable, Cursor) is already mutating the scene.

---

## Immediate job

**Rebuild the rear so it reads like the Q Comet concept photo, not the current simplified rear.**

| | path |
|---|---|
| Current Blender rear (wrong) | `docs/handoff-antigravity/current_rear_blender.png` |
| Target concept rear (match this) | `docs/handoff-antigravity/target_rear_concept.png` |
| Official rear ortho | `vehicles/qcomet/source/concepts/orthos/qcomet_ref_rear.png` |
| Four-side sheet | `vehicles/qcomet/source/concepts/q comet all four sides.png` |
| Front/rear/top sheet | `vehicles/qcomet/source/concepts/q comet front rear top.png` |

Quasar compared those two images in chat and said: the rear needs to be updated to look like the real rear of the photo Q Comet.

### What the current rear is missing (vs the photo)

1. **Light bar** — photo: thicker, more 3D, slightly pinched at center, wider at the outer hooks, wraps into the haunches. Current: a thin flat red line with a small hook.
2. **Q+ badge** — photo: bronze/gold **Q+** (Q with a plus), refined, in a shallow recess. Current: a thin orange ring only. Object to replace: `badge_rear`.
3. **Deck / ducktail** — photo: a real trailing lip above the lamp channel, more shoulder, darker glass roof contrast. Current: almost no ducktail, slabby lid.
4. **Bumper sculpture** — photo: deep horizontal crease, bronze edge line, corner intakes, lower red side markers. Current: a smooth olive box.
5. **Diffuser** — photo: carbon weave, gold/bronze rim, more lobed / vented, not four skinny fins hanging in space. Objects: `rear_diffuser`, `rear_diffuser_bronze`, `diffuser_strake_*`.
6. **Materials** — photo: metallic olive paint, carbon, bronze trim, stronger lamp glow. Current: matte clay + a weak emission line.

Keep it original Q Comet. Do not import a real car or another game’s rear.

---

## Start from this file

**Live / latest authoring file:** `vehicles/qcomet/source/blender/qcomet_sollumz_v016.blend`  
Saved 2026-09-11 10:41. Sollumz fragment + UV pass. `game_ready` is still **false**.

Do **not** overwrite:

- `qcomet_sollumz_v015.blend`
- `qcomet_vehicle_v013.blend`
- `qcomet_cabin_v014.blend`
- any `qcomet_body_v0*.blend`

**Save the rear pass as:** `vehicles/qcomet/source/blender/qcomet_rear_v017.blend`  
Evidence: `vehicles/qcomet/source/blender/review_v017/`  
Recipe: `tools/blender/refine_qcomet_rear_v017.py` (new; do not silently rewrite v012/v015/v016 recipes unless you must).

If the live Blender session is not on v016, open v016. Health-check first.

---

## Machine / Blender

- Windows 11, Blender **5.2.1 LTS**, Sollumz **2.9** (`bl_ext.sollumz_org.sollumz`)
- blender-mcp addon on **127.0.0.1:9876**
- Claude Code MCP launcher (if you use that stack): `C:\Users\Qanva\.local\bin\uv.exe tool run blender-mcp`  
  `uvx` is **not** on PATH. Do not restart Blender if 9876 already answers.
- Orientation: **+Y front, +X right, +Z up**. Origin at ground center.
- Dimensions in `vehicles/qcomet/project.json` are **provisional**. Do not treat them as approved.

Socket ping (Cursor-style; blender-mcp tools also work):

```python
{"type": "execute_code", "params": {"code": "import bpy; print(bpy.data.filepath, len(bpy.context.scene.objects))"}}
```

Prefer one `bpy` script over many tiny MCP calls. No screenshot spam. Headless CLI only for exports.

---

## What is already done

| milestone | file | notes |
|---|---|---|
| v012 exterior | `qcomet_body_v012.blend` | Pill grille, swept LEDs, wavy tail bars, 6-strake carbon diffuser, bronze edges. See `docs/qcomet-v012-review.md`. **Not** a certified match to the rear photo. |
| v013 vehicle rig | `qcomet_vehicle_v013.blend` | M1 cabin + M2 hinges + M3 hierarchy. Doors, hood, trunk, 4 wheels, 4 seats, steering. |
| v014 cabin | `qcomet_cabin_v014.blend` | Cabin geometry / sightlines. Older than v013 vehicle. |
| v015 Sollumz | `qcomet_sollumz_v015.blend` | Native fragment `qcomet`, 24 bones, 21 collision bounds, 6 vehicle windows. In-memory export audit passed. **No .yft/.ytd/.ybn written.** Recipe: `tools/blender/build_qcomet_sollumz_v015.py`. Report: `review_v015/`. |
| v016 UVs | `qcomet_sollumz_v016.blend` | Dash text UVMap 0/1; glass UVMap 2. Sollumz UV warnings 0. Recipe: `tools/blender/build_qcomet_uvs_v016.py`. Report: `review_v016/`. Body UVs are still metre-projection **proxies**. |

`CLAUDE.md` in the repo root is **stale** (still describes v015 as next). After you save v017, update `CLAUDE.md` and `docs/build-status.md`.

---

## Rear object names to expect

From the v012 recipe (`tools/blender/refine_qcomet_body_v012.py`). Names may have been archived/renamed by v015 (`exp_`, `phys_`, `*_authoring_*`). Inspect the live v016 scene before editing.

- `tail_bar_running`, `tail_bar_brake` (emission was 25.0 in v012)
- `boot`, `boot_ducktail`
- `bumper_r` (or equivalent rear bumper)
- `rear_diffuser`, `rear_diffuser_bronze`
- `diffuser_strake_0` … `diffuser_strake_5` plus bronze edges
- `badge_rear` (should become a real **Q+**, not a ring)
- reverse lenses, corner markers if present

Keep body, glass, lights, wheels, interior, collision **separable**. If you change boot/bumper shape, update collision hulls that were built from those meshes in v015.

---

## Sollumz 2.9 landmines (already hit)

Do **not** edit the installed Sollumz addon. Keep shims in project scripts, as v015 did:

1. `get_shader_config` never inits `texture` → `UnboundLocalError` on vehicle shaders. In-memory patch.
2. Shader compiler class-level node caches go stale after file reload. Fresh caches per instance.
3. Vertex colors must be **`Color 1` / `Color 2`**, not `Colour0` / `Colour1`.
4. Convex hull helper can hand the same vertex to bmesh twice; de-dupe before delete.
5. Long builds: schedule with `bpy.app.timers` so MCP does not time out. Reload the **on-disk** start file if the live scene is dirty or half-mutated.

---

## Hard rules

- Original fictional identity only. No real-vehicle or other-game geometry, badges, textures, sounds, handling, or code.
- Do **not** fabricate `.yft` / `.ytd` / `.ybn`.
- Four usable seats, clean first-person visibility, game cabin (`q comet cabin dash.png`). Cinematic dash is inspiration only.
- No NoPixel claims. No publish/sell until a human finishes the test checklist.
- One agent on port 9876. If unsure, inspect only.

Skills that apply: `AGENTS.md`, `.agents/skills/blender-mcp`, `blender-modeling`, `reference-to-3d`, `reference-look-calibration`, `blender-skill-harmonizer`. Reference-locked order beats generic pro-workflow.

---

## Done when

- Ortho rear camera render sits next to `target_rear_concept.png` and `orthos/qcomet_ref_rear.png`.
- Light bar, Q+ badge, ducktail, bumper crease/bronze, carbon diffuser, and side markers are all present and separable.
- `qcomet_rear_v017.blend` saved; v016 and older files untouched.
- Short `review_v017/` note: objects changed, what still does not match, no binaries written.
- `game_ready` stays false until human spawn + checklist.

After the rear is accepted, later work (not this handoff): production body UVs/textures, hinge sweep certification, handling/meta, clean-server spawn, listing media.
