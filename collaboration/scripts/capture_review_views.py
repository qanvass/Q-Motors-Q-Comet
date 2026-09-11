"""Temporary review cameras/renders. Restores camera, visibility, selection, mode, and render settings.

Does not edit car mesh data.
"""

from __future__ import annotations

import json
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(r"C:\Users\Qanva\Desktop\Gaming GTA\Q-Motors-Q-Comet")
OUT = ROOT / "collaboration" / "blender-handoff" / "review"
PREFIX = "COLLAB_TMP_"

VIEWS = {
    "front": ((0.0, 7.4, 0.85), (1.25, 0.0, 3.1416)),
    "rear": ((0.0, -7.4, 0.85), (1.25, 0.0, 0.0)),
    "left": ((-6.4, 0.0, 0.85), (1.25, 0.0, -1.5708)),
    "right": ((6.4, 0.0, 0.85), (1.25, 0.0, 1.5708)),
    "top": ((0.0, 0.0, 9.2), (0.0, 0.0, 0.0)),
    "front_three_quarter": ((4.6, 5.6, 1.7), (1.2, 0.0, 2.5)),
}


def working_meshes():
    rows = []
    for obj in bpy.context.scene.objects:
        if obj.type != "MESH":
            continue
        if obj.name.startswith(("COL_", "col_", "exp_", "phys_", PREFIX)):
            continue
        collections = " ".join(col.name.lower() for col in obj.users_collection)
        if "archive" in collections:
            continue
        if obj.hide_render:
            continue
        rows.append(obj)
    return rows


def bounds(objects):
    points = []
    for obj in objects:
        for corner in obj.bound_box:
            points.append(obj.matrix_world @ Vector(corner))
    mins = Vector((min(p[i] for p in points) for i in range(3)))
    maxs = Vector((max(p[i] for p in points) for i in range(3)))
    return mins, maxs, (mins + maxs) / 2


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    view_layer = bpy.context.view_layer
    window = bpy.context.window_manager.windows[0]

    saved = {
        "camera": scene.camera.name if scene.camera else None,
        "engine": scene.render.engine,
        "filepath": scene.render.filepath,
        "res": (scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage),
        "film_transparent": scene.render.film_transparent,
        "mode": bpy.context.object.mode if bpy.context.object else "OBJECT",
        "active": view_layer.objects.active.name if view_layer.objects.active else None,
        "selected": [obj.name for obj in bpy.context.selected_objects],
        "hide_viewport": {obj.name: obj.hide_viewport for obj in scene.objects},
        "hide_render": {obj.name: obj.hide_render for obj in scene.objects},
    }

    images = []
    created = []
    try:
        if bpy.context.object and bpy.context.object.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")

        car = working_meshes()
        if not car:
            raise RuntimeError("No working-car meshes found for review framing.")
        mins, maxs, center = bounds(car)

        scene.render.engine = "BLENDER_EEVEE"
        scene.render.resolution_x = 1280
        scene.render.resolution_y = 720
        scene.render.resolution_percentage = 100
        scene.render.film_transparent = False
        if hasattr(scene.eevee, "taa_render_samples"):
            scene.eevee.taa_render_samples = 16

        cam_data = bpy.data.cameras.new(PREFIX + "lens")
        cam_data.lens = 50
        created.append(cam_data)
        cam = bpy.data.objects.new(PREFIX + "camera", cam_data)
        scene.collection.objects.link(cam)
        created.append(cam)
        scene.camera = cam

        for name, (location, rotation) in VIEWS.items():
            cam.location = location
            cam.rotation_euler = rotation
            if name == "top":
                cam.rotation_euler = (0, 0, 0)
                cam.location = (center.x, center.y, maxs.z + 6.5)
                cam_data.type = "ORTHO"
                cam_data.ortho_scale = max(maxs.x - mins.x, maxs.y - mins.y) * 1.25
            else:
                cam_data.type = "PERSP"
                cam_data.lens = 50
            dest = OUT / f"qcomet_{name}.png"
            scene.render.filepath = str(dest)
            with bpy.context.temp_override(window=window):
                bpy.ops.render.render(write_still=True)
            images.append({
                "name": name,
                "path": str(dest.relative_to(ROOT)).replace("\\", "/"),
                "kind": "eevee_render",
                "exists": dest.is_file(),
                "bytes": dest.stat().st_size if dest.is_file() else 0,
            })

        # Cabin / dash from existing cameras if present.
        for cam_name, label in (
            ("qcomet_v018_cabin_cam", "cabin"),
            ("QCOMET_REVIEW_CAMERA", "dashboard_or_existing_review"),
        ):
            existing = bpy.data.objects.get(cam_name)
            if existing is None or existing.type != "CAMERA":
                images.append({
                    "name": label,
                    "path": None,
                    "kind": "not_generated",
                    "reason": f"Camera {cam_name!r} not in the live scene.",
                })
                continue
            scene.camera = existing
            dest = OUT / f"qcomet_{label}.png"
            scene.render.filepath = str(dest)
            with bpy.context.temp_override(window=window):
                bpy.ops.render.render(write_still=True)
            images.append({
                "name": label,
                "path": str(dest.relative_to(ROOT)).replace("\\", "/"),
                "kind": "eevee_render",
                "camera": cam_name,
                "exists": dest.is_file(),
                "bytes": dest.stat().st_size if dest.is_file() else 0,
            })

        # Wireframe viewport captures via offscreen-friendly display override.
        scene.camera = cam
        cam_data.type = "PERSP"
        cam.location = VIEWS["front_three_quarter"][0]
        cam.rotation_euler = VIEWS["front_three_quarter"][1]
        overlay_changed = []
        for obj in car:
            overlay_changed.append((obj, obj.display_type))
            obj.display_type = "WIRE"
        dest = OUT / "qcomet_wireframe_front_three_quarter.png"
        scene.render.filepath = str(dest)
        with bpy.context.temp_override(window=window):
            bpy.ops.render.render(write_still=True)
        images.append({
            "name": "wireframe_front_three_quarter",
            "path": str(dest.relative_to(ROOT)).replace("\\", "/"),
            "kind": "eevee_render_display_wire",
            "exists": dest.is_file(),
            "bytes": dest.stat().st_size if dest.is_file() else 0,
            "note": "Temporary object display_type=WIRE; mesh data unchanged.",
        })
        cam.location = VIEWS["front"][0]
        cam.rotation_euler = VIEWS["front"][1]
        dest = OUT / "qcomet_wireframe_front.png"
        scene.render.filepath = str(dest)
        with bpy.context.temp_override(window=window):
            bpy.ops.render.render(write_still=True)
        images.append({
            "name": "wireframe_front",
            "path": str(dest.relative_to(ROOT)).replace("\\", "/"),
            "kind": "eevee_render_display_wire",
            "exists": dest.is_file(),
            "bytes": dest.stat().st_size if dest.is_file() else 0,
        })
        for obj, display in overlay_changed:
            obj.display_type = display
    finally:
        scene.render.engine = saved["engine"]
        scene.render.filepath = saved["filepath"]
        scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = saved["res"]
        scene.render.film_transparent = saved["film_transparent"]
        if saved["camera"] and saved["camera"] in bpy.data.objects:
            scene.camera = bpy.data.objects[saved["camera"]]
        for obj in scene.objects:
            if obj.name in saved["hide_viewport"]:
                obj.hide_viewport = saved["hide_viewport"][obj.name]
            if obj.name in saved["hide_render"]:
                obj.hide_render = saved["hide_render"][obj.name]
        bpy.ops.object.select_all(action="DESELECT")
        for name in saved["selected"]:
            if name in bpy.data.objects:
                bpy.data.objects[name].select_set(True)
        if saved["active"] and saved["active"] in bpy.data.objects:
            view_layer.objects.active = bpy.data.objects[saved["active"]]
        if bpy.context.object and saved["mode"] != bpy.context.object.mode:
            try:
                bpy.ops.object.mode_set(mode=saved["mode"])
            except Exception:
                pass
        for item in created:
            if isinstance(item, bpy.types.Object):
                bpy.data.objects.remove(item, do_unlink=True)
            elif isinstance(item, bpy.types.Camera):
                if item.users == 0:
                    bpy.data.cameras.remove(item)

    manifest = {
        "source_file": bpy.data.filepath,
        "images": images,
        "restored": True,
        "geometry_modified": False,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"wrote": str(OUT / "manifest.json"), "images": len(images), "ok": all(item.get("exists", True) or item.get("kind") == "not_generated" for item in images)}))


if __name__ == "__main__":
    main()
