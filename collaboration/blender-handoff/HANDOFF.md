# ChatGPT / Astra handoff — Q Motors Q Comet

Date: 2026-09-11  
Role split: **ChatGPT/Astra reviews and writes scripts. The local Cursor agent executes them** on the live Blender MCP socket and returns verified results.  
Repo: https://github.com/qanvass/Q-Motors-Q-Comet  
Product: `qcomet` (public name **Q Comet**, manufacturer **Q Motors**)

Read `AGENTS.md` and `vehicles/qcomet/project.json` before proposing geometry.

---

## Verified live session (this handoff)

| Field | Value |
|---|---|
| Connection | **OK** — `ping` → `{"pong": true}` on `127.0.0.1:9876` |
| Add-on | MCP for Blender **1.6**, protocol **5** (`blender_mcp.py`) |
| Blender | **5.2.1 LTS** |
| Sollumz | **2.9.0** (`bl_ext.sollumz_org.sollumz`) |
| Active scene | `Scene` |
| Active file | `vehicles/qcomet/source/blender/qcomet_rear_v017.blend` |
| Unsaved changes | **Yes** (`bpy.data.is_dirty == true`) |
| Object count | **940** |
| Units | metric, `scale_length` 1.0 |
| Axes | **+Y front, +X right, +Z up** (project contract) |
| Checkpoint of this in-memory scene | `collaboration/local/checkpoints/qcomet_live_checkpoint_20260911_161521.blend` (25,463,523 bytes, verified on disk). **Not in git.** |

The checkpoint was written with `wm.save_as_mainfile(..., copy=True)`. The active path stayed `qcomet_rear_v017.blend`. The original file on disk was **not** overwritten. The live scene was **not** replaced with an older blend.

Do **not** open an older milestone (`v013`–`v016`) over this session.

---

## Machine-readable reports

- Full object dump: [`scene_report.json`](./scene_report.json)
- Compact summary: [`scene_summary.json`](./scene_summary.json)
- Review image list: [`review/manifest.json`](./review/manifest.json)

Classification counts from the live dump (heuristic — treat `uncertain` as unmarked):

| class | count |
|---|---|
| working_car | 267 |
| archived_authoring | 282 |
| sollumz_export (`exp_` / `phys_`) | 289 |
| collision | 33 |
| reference | 19 |
| guide_or_review | 15 |
| uncertain | 33 |
| camera | 1 (`get_scene_info` sample; full dump lists more cameras) |
| sollumz_rig | 1 (`qcomet` fragment) |

Working-car collections include `QCOMET_BODY_PANELS`, `QCOMET_GLASS`, `QCOMET_LIGHTS`, `QCOMET_INTERIOR`, `QCOMET_RUNNING_GEAR`. Archives include `QCOMET_AUTHORING_ARCHIVE`, `QCOMET_V010_SURFACING_ARCHIVE`, `QCOMET_V011_*`, `QCOMET_V013_CABIN_ARCHIVE`, `QCOMET_V016_REAR_ARCHIVE`. Export/collision: `QCOMET_SOLLUMZ_EXPORT`, `QCOMET_COLLISION`, `QCOMET_RIG`.

No missing external image files were reported. No linked libraries.

---

## Review images (generated this session)

All shaded views are **EEVEE still renders** (1280×720). Topology views are **Workbench wire renders**. Temporary cameras and `display_type` overrides were removed; engine/camera/visibility/selection/mode/render settings restored. **Mesh datablocks were not edited.**

| View | File | Kind |
|---|---|---|
| Front | [review/qcomet_front.png](./review/qcomet_front.png) | EEVEE render |
| Rear | [review/qcomet_rear.png](./review/qcomet_rear.png) | EEVEE render |
| Left | [review/qcomet_left.png](./review/qcomet_left.png) | EEVEE render |
| Right | [review/qcomet_right.png](./review/qcomet_right.png) | EEVEE render |
| Top | [review/qcomet_top.png](./review/qcomet_top.png) | EEVEE render |
| Front 3/4 | [review/qcomet_front_three_quarter.png](./review/qcomet_front_three_quarter.png) | EEVEE render |
| Cabin | [review/qcomet_cabin.png](./review/qcomet_cabin.png) | EEVEE render via `qcomet_v018_cabin_cam` |
| Existing review cam | [review/qcomet_dashboard_or_existing_review.png](./review/qcomet_dashboard_or_existing_review.png) | EEVEE render via `QCOMET_REVIEW_CAMERA` |
| Front wire | [review/qcomet_workbench_wire_front.png](./review/qcomet_workbench_wire_front.png) | Workbench render |
| 3/4 wire | [review/qcomet_workbench_wire_front_three_quarter.png](./review/qcomet_workbench_wire_front_three_quarter.png) | Workbench render |
| Contact sheet | [review/qcomet_contact_sheet.png](./review/qcomet_contact_sheet.png) | Composed from the above |

EEVEE ignores `display_type=WIRE`, so those failed stills were deleted rather than labeled as wireframes.

---

## Socket protocol (do not invent another one)

Installed add-on: `C:\Users\Qanva\AppData\Roaming\Blender Foundation\Blender\5.2\scripts\addons\blender_mcp.py`  
Local client: `collaboration/scripts/blender_mcp_client.py`

One JSON command per TCP connection to `127.0.0.1:9876`:

```json
{"type": "execute_code", "params": {"code": "import bpy\nprint(bpy.data.filepath)"}}
```

Always-available `type` values (protocol 5): `ping`, `get_scene_info`, `get_addon_info`, `get_object_info`, `get_viewport_screenshot`, `execute_code`, `get_world_state_snapshot`, `drain_human_activity`, `get_telemetry_consent`, `set_telemetry_consent`.

Reply: `{"status":"success","result":...}` or `{"status":"error","message":"..."}`.  
`execute_code` result is `{"executed": true, "result": "<stdout>"}`.

**Local procedure to run an Astra script**

1. Astra commits or pastes a `.py` that uses `bpy` only. State required objects and that the live file must stay `qcomet_rear_v017.blend` (or a later versioned file the executor names).
2. Local agent reviews scope. If it would overwrite an older milestone or write `.yft`/`.ytd`/`.ybn`, reject it.
3. `python collaboration/scripts/run_astra_task.py --task-id T00N --script path/to/script.py`
4. That runner: pings MCP → records filepath/dirty/count → saves a new unique checkpoint (`copy=True`) → `runpy.run_path` inside Blender → appends `collaboration/local/task_log.jsonl`.
5. After success, save a new versioned blend (`qcomet_<stage>_vNNN.blend`). Do not overwrite v017 or the checkpoint.
6. Generate before/after views and an updated report.
7. **Do not blindly rerun after a timeout.** First inspect whether the scene already changed (`is_dirty`, object count, names).

Machine paths live in `collaboration/local/` (gitignored). Template: `collaboration/local.example.json`. Never commit tokens.

---

## Known modeling / export issues

- v1 is **not** game-ready. No clean-server spawn, no fabricated `.yft`/`.ytd`/`.ybn`.
- Dimensions in `project.json` are provisional.
- Bugbot on `tools/blender/refine_qcomet_rear_v017.py`: collision names `col_boot` vs `COL_boot`; `exp_*` sync drops Sollumz shaders; new tail meshes not exported; readiness `PASSED` without a fragment audit.
- Body UVs on v016 were still metre-projection proxies except dash text and glass UVMap 2.
- Cabin: use `q comet cabin dash.png`. Cinematic dash is inspiration only.
- One writer on port 9876.

Required moving parts: `door_dside_f`, `door_pside_f`, `door_dside_r`, `door_pside_r`, `bonnet`, `boot`, `wheel_lf`, `wheel_rf`, `wheel_lr`, `wheel_rr`, `steeringwheel`.

---

## What Astra should do next

1. Read this file, `scene_summary.json`, and the review images.
2. Use `scene_report.json` for exact names/parents before writing `bpy`.
3. Propose one scoped script (rear export/collision fix, or the next approved visual pass).
4. The local agent will execute it through the existing socket and return hashes, checkpoint path, and new views.

Do not import real cars or other-game assets. Keep panels, glass, lights, wheels, interior, and collision separable.
