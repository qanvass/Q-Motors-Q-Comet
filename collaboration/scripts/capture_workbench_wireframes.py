"""Two Workbench wireframe stills. Restores engine, camera, display_type, and filepath."""

from __future__ import annotations

import json
from pathlib import Path

import bpy

ROOT = Path(r"C:\Users\Qanva\Desktop\Gaming GTA\Q-Motors-Q-Comet")
OUT = ROOT / "collaboration" / "blender-handoff" / "review"
PREFIX = "COLLAB_TMP_WIRE_"


def main():
    scene = bpy.context.scene
    window = bpy.context.window_manager.windows[0]
    saved = {
        "engine": scene.render.engine,
        "camera": scene.camera.name if scene.camera else None,
        "filepath": scene.render.filepath,
        "res": (scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage),
        "display": {obj.name: obj.display_type for obj in scene.objects if obj.type == "MESH"},
    }
    created = []
    images = []
    try:
        scene.render.engine = "BLENDER_WORKBENCH"
        scene.render.resolution_x = 1280
        scene.render.resolution_y = 720
        if hasattr(scene.display.shading, "light"):
            scene.display.shading.light = "FLAT"
        for obj in scene.objects:
            if obj.type == "MESH" and not obj.name.startswith(("COL_", "exp_", "phys_")):
                obj.display_type = "WIRE"
        cam_data = bpy.data.cameras.new(PREFIX + "lens")
        cam = bpy.data.objects.new(PREFIX + "camera", cam_data)
        scene.collection.objects.link(cam)
        created.extend([cam, cam_data])
        scene.camera = cam
        shots = {
            "workbench_wire_front": ((0.0, 7.4, 0.85), (1.25, 0.0, 3.1416)),
            "workbench_wire_front_three_quarter": ((4.6, 5.6, 1.7), (1.2, 0.0, 2.5)),
        }
        for name, (location, rotation) in shots.items():
            cam.location = location
            cam.rotation_euler = rotation
            dest = OUT / f"qcomet_{name}.png"
            scene.render.filepath = str(dest)
            with bpy.context.temp_override(window=window):
                bpy.ops.render.render(write_still=True)
            images.append({
                "name": name,
                "path": str(dest.relative_to(ROOT)).replace("\\", "/"),
                "kind": "workbench_render_wire",
                "exists": dest.is_file(),
                "bytes": dest.stat().st_size if dest.is_file() else 0,
            })
    finally:
        scene.render.engine = saved["engine"]
        scene.render.filepath = saved["filepath"]
        scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = saved["res"]
        if saved["camera"] and saved["camera"] in bpy.data.objects:
            scene.camera = bpy.data.objects[saved["camera"]]
        for name, display in saved["display"].items():
            if name in bpy.data.objects:
                bpy.data.objects[name].display_type = display
        for item in created:
            if isinstance(item, bpy.types.Object):
                bpy.data.objects.remove(item, do_unlink=True)
            elif isinstance(item, bpy.types.Camera) and item.users == 0:
                bpy.data.cameras.remove(item)

    manifest_path = OUT / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else {"images": []}
    # Replace failed EEVEE-as-wire entries with honest Workbench wires.
    kept = [item for item in manifest.get("images", []) if not str(item.get("name", "")).startswith("wireframe_")]
    kept.extend(images)
    manifest["images"] = kept
    manifest["wireframe_note"] = "EEVEE ignores display_type=WIRE; topology views are Workbench renders."
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"images": images, "restored_engine": scene.render.engine}))


if __name__ == "__main__":
    main()
