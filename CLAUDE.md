# Q Comet — Claude Code / Fable

Work in this repo is the original **Q Motors Q Comet** FiveM vehicle. Follow `AGENTS.md` exactly.

## Models

- Claude Code: start with `claude --model claude-fable-5-1` (alias `/model fable`).
- Cursor: Fable 5.1 is `claude-fable-5-1-thinking-high`.
- Do not drive the live Blender file from two agents at once. If port `9876` is already being mutated, inspect only.

## Live Blender

- MCP: `blender-mcp` on `127.0.0.1:9876` (Blender 5.2.1 LTS, Sollumz 2.9).
- Claude Code launches it with `C:\Users\Qanva\.local\bin\uv.exe tool run blender-mcp` (`uvx` is not on PATH). Do not restart Blender if port 9876 already answers.
- Health check first: scene info, then a tiny `execute_python` ping. No viewport screenshot spam.
- Prefer one `bpy` script over many tiny MCP calls. Headless CLI for exports only.

## Current source

Latest authored files (do not overwrite older milestones):

- `vehicles/qcomet/source/blender/qcomet_rear_v017.blend` — latest working file (v017 rear rebuild matching concept photo, Sollumz fragment rig + UVs retained)
- `vehicles/qcomet/source/blender/qcomet_sollumz_v016.blend` — Sollumz fragment + UV pass milestone
- `vehicles/qcomet/source/blender/qcomet_sollumz_v015.blend` — native Sollumz fragment milestone
- `vehicles/qcomet/source/blender/qcomet_vehicle_v013.blend` — vehicle rig baseline
- Evidence: `vehicles/qcomet/source/blender/review_v017/` (ortho rear render, three-quarter, detail, rear_validation.json)

## Next milestone (v018+)

1. Human check on v017 rear render evidence against target concept photo.
2. Production body UVs and textured materials pass (replacing metre-projection proxies).
3. Hinge sweep certification for boot, bonnet, and doors.
4. Handling tuning and vehicle meta files (`vehicles.meta`, `handling.meta`, `carcols.meta`).
5. FiveM test server spawn verification. No binary assets (.yft/.ytd/.ybn) fabricated; game_ready remains false until human checklist passes.

## Identity and delivery

- Original fictional car only. No real-vehicle or other-game geometry, badges, textures, sounds, handling, or code.
- Dimensions in `vehicles/qcomet/project.json` stay provisional until Quasar approves a sheet.
- Four usable seats, clean first-person visibility, game-oriented cabin (not the cinematic dash).
- No NoPixel claims. No publish/sell until a human finishes the test checklist.
