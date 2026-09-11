"""Read-only inspection of the live Q Comet scene. Writes scene_report.json."""

from __future__ import annotations

import addon_utils
import json
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(r"C:\Users\Qanva\Desktop\Gaming GTA\Q-Motors-Q-Comet")
OUT = ROOT / "collaboration" / "blender-handoff" / "scene_report.json"


def vec(value):
    return [round(float(value[i]), 5) for i in range(3)]


def classify(obj):
    name = obj.name
    lower = name.lower()
    collections = [col.name for col in obj.users_collection]
    coll_text = " ".join(collections).lower()
    notes = []
    kind = "uncertain"
    if name.startswith(("COL_", "col_")) or "collision" in coll_text:
        kind = "collision"
    elif name.startswith(("exp_", "phys_")):
        kind = "sollumz_export"
    elif name.startswith(("PIVOT_", "qcomet_review_", "QCOMET_REVIEW", "COLLAB_")):
        kind = "guide_or_review"
    elif obj.type == "CAMERA":
        kind = "camera"
    elif obj.type == "LIGHT":
        kind = "light"
    elif obj.type == "ARMATURE" or name == "qcomet":
        kind = "sollumz_rig"
    elif "archive" in coll_text or "authoring_archive" in coll_text or "_authoring_" in lower:
        kind = "archived_authoring"
    elif name.startswith(("REF_", "ref_", "concept_")) or "reference" in coll_text:
        kind = "reference"
    elif obj.type in {"MESH", "FONT", "CURVE", "EMPTY"} and obj.visible_get() and not obj.hide_render:
        kind = "working_car"
    else:
        notes.append("Hidden, collision-like, or unclassified; inspect before editing.")
        kind = "uncertain"
    return {"class": kind, "notes": notes, "collections": collections}


def addon_versions():
    rows = []
    for module in addon_utils.modules():
        name = module.__name__
        info = getattr(module, "bl_info", {})
        interesting = any(
            token in name.lower() or token in str(info).lower()
            for token in ("sollum", "blender_mcp", "mcp", "blendermcp")
        )
        if not interesting:
            continue
        loaded = addon_utils.check(name)
        rows.append(
            {
                "module": name,
                "name": info.get("name"),
                "version": list(info.get("version", [])),
                "enabled": bool(loaded[0] if isinstance(loaded, tuple) else loaded),
                "file": getattr(module, "__file__", None),
            }
        )
    return rows


def image_info(image):
    packed = bool(image.packed_file)
    path = bpy.path.abspath(image.filepath) if image.filepath else ""
    missing = False
    if path and not packed and image.source == "FILE":
        missing = not Path(path).is_file()
    return {
        "name": image.name,
        "filepath": path,
        "packed": packed,
        "source": image.source,
        "size": list(image.size) if image.size else [0, 0],
        "missing_on_disk": missing,
    }


def object_row(obj):
    mesh = {}
    if obj.type == "MESH" and obj.data:
        mesh = {
            "vertices": len(obj.data.vertices),
            "faces": len(obj.data.polygons),
            "uv_layers": [layer.name for layer in obj.data.uv_layers],
        }
        try:
            corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
            mins = Vector((min(p[i] for p in corners) for i in range(3)))
            maxs = Vector((max(p[i] for p in corners) for i in range(3)))
            mesh["world_bbox_min"] = vec(mins)
            mesh["world_bbox_max"] = vec(maxs)
            mesh["world_size_m"] = vec(maxs - mins)
        except Exception as exc:
            mesh["bbox_error"] = str(exc)
    return {
        "name": obj.name,
        "type": obj.type,
        "parent": obj.parent.name if obj.parent else None,
        "location": vec(obj.location),
        "rotation_euler": vec(obj.rotation_euler),
        "scale": vec(obj.scale),
        "hide_viewport": obj.hide_viewport,
        "hide_render": obj.hide_render,
        "visible_in_viewport": bool(obj.visible_get()),
        "sollum_type": str(getattr(obj, "sollum_type", "")),
        "modifiers": [mod.type + ":" + mod.name for mod in obj.modifiers],
        "materials": [slot.material.name for slot in obj.material_slots if slot.material],
        "mesh": mesh,
        "classification": classify(obj),
    }


def collection_tree(collection, depth=0):
    return {
        "name": collection.name,
        "hide_viewport": collection.hide_viewport,
        "hide_render": collection.hide_render,
        "object_count": len(collection.objects),
        "objects": [obj.name for obj in collection.objects],
        "children": [collection_tree(child, depth + 1) for child in collection.children],
    }


def main():
    scene = bpy.context.scene
    unit = scene.unit_settings
    report = {
        "blender": {
            "version": bpy.app.version_string,
            "build": str(bpy.app.build_commit_timestamp),
        },
        "addons": addon_versions(),
        "scene": {
            "name": scene.name,
            "objects": len(scene.objects),
            "materials": len(bpy.data.materials),
            "frame_current": scene.frame_current,
            "render_engine": scene.render.engine,
            "resolution": [scene.render.resolution_x, scene.render.resolution_y],
            "fps": scene.render.fps,
        },
        "units": {
            "system": unit.system,
            "scale_length": unit.scale_length,
            "system_rotation": getattr(unit, "system_rotation", None),
        },
        "axis_conventions": {
            "project": {"front": "+Y", "right": "+X", "up": "+Z"},
            "blender_forward": "+Y",
            "blender_up": "+Z",
        },
        "file": {
            "filepath": bpy.data.filepath,
            "is_dirty": bpy.data.is_dirty,
        },
        "mcp": {
            "port": getattr(scene, "blendermcp_port", None),
            "addon": "C:\\Users\\Qanva\\AppData\\Roaming\\Blender Foundation\\Blender\\5.2\\scripts\\addons\\blender_mcp.py",
            "protocol_version": 5,
        },
        "collections": collection_tree(scene.collection),
        "objects": [object_row(obj) for obj in scene.objects],
        "cameras": [
            {
                "name": obj.name,
                "location": vec(obj.location),
                "lens": obj.data.lens if obj.data else None,
            }
            for obj in scene.objects
            if obj.type == "CAMERA"
        ],
        "lights": [
            {
                "name": obj.name,
                "light_type": obj.data.type,
                "energy": obj.data.energy,
                "location": vec(obj.location),
            }
            for obj in scene.objects
            if obj.type == "LIGHT"
        ],
        "images": [image_info(image) for image in bpy.data.images],
        "libraries": [lib.filepath for lib in bpy.data.libraries],
        "missing_images": [
            image.name
            for image in bpy.data.images
            if image_info(image)["missing_on_disk"]
        ],
    }
    counts = {}
    for row in report["objects"]:
        kind = row["classification"]["class"]
        counts[kind] = counts.get(kind, 0) + 1
    report["classification_counts"] = counts
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({
        "wrote": str(OUT),
        "bytes": OUT.stat().st_size,
        "objects": report["scene"]["objects"],
        "classification_counts": counts,
        "missing_images": report["missing_images"],
        "filepath": report["file"]["filepath"],
        "dirty": report["file"]["is_dirty"],
    }))


if __name__ == "__main__":
    main()
