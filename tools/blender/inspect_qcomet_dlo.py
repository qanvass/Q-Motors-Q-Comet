"""Read-only DLO measurement dump. Does not save the .blend."""

from __future__ import annotations

import json
import os
import sys

import bpy
from mathutils import Vector


NAMES = [
    "chassis",
    "panoramic_glass_greenhouse",
    "glass_windshield",
    "glass_rear",
    "glass_side_dside",
    "glass_side_pside",
    "pillar_a_dside",
    "pillar_a_pside",
    "pillar_b_dside",
    "pillar_b_pside",
    "pillar_c_dside",
    "pillar_c_pside",
    "drip_trim_dside",
    "drip_trim_pside",
]


def world_bounds(obj):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        matrix = evaluated.matrix_world
        points = [matrix @ v.co for v in mesh.vertices]
        if not points:
            return None
        xs = [p.x for p in points]
        ys = [p.y for p in points]
        zs = [p.z for p in points]
        n = len(points)
        return {
            "verts": n,
            "faces": len(mesh.polygons),
            "min": [min(xs), min(ys), min(zs)],
            "max": [max(xs), max(ys), max(zs)],
            "size": [max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)],
            "center": [
                (min(xs) + max(xs)) * 0.5,
                (min(ys) + max(ys)) * 0.5,
                (min(zs) + max(zs)) * 0.5,
            ],
        }
    finally:
        evaluated.to_mesh_clear()


def endpoint_clusters(obj, fraction=0.18):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        matrix = evaluated.matrix_world
        points = [(i, matrix @ v.co) for i, v in enumerate(mesh.vertices)]
        if not points:
            return {}
        zs = [p.z for _, p in points]
        zmin, zmax = min(zs), max(zs)
        height = max(zmax - zmin, 1e-6)
        belt = [p for _, p in points if p.z <= zmin + height * fraction]
        roof = [p for _, p in points if p.z >= zmax - height * fraction]
        def stats(group):
            if not group:
                return None
            return {
                "count": len(group),
                "min": [min(p.x for p in group), min(p.y for p in group), min(p.z for p in group)],
                "max": [max(p.x for p in group), max(p.y for p in group), max(p.z for p in group)],
                "center": [
                    sum(p.x for p in group) / len(group),
                    sum(p.y for p in group) / len(group),
                    sum(p.z for p in group) / len(group),
                ],
            }
        loc, rot, sca = obj.matrix_world.decompose()
        eul = rot.to_euler("XYZ")
        return {
            "location": list(obj.location),
            "world_location": list(loc),
            "rotation_euler": [eul.x, eul.y, eul.z],
            "scale": list(obj.scale),
            "delta_rotation": list(obj.delta_rotation_euler),
            "parent": obj.parent.name if obj.parent else None,
            "belt": stats(belt),
            "roof": stats(roof),
        }
    finally:
        evaluated.to_mesh_clear()


def main():
    print(f"FILE {bpy.data.filepath}", flush=True)
    print(f"BACKGROUND {bpy.app.background}", flush=True)
    dump = {"file": bpy.data.filepath, "objects": {}}
    for name in NAMES:
        obj = bpy.data.objects.get(name)
        if obj is None:
            print(f"MISSING {name}", flush=True)
            dump["objects"][name] = None
            continue
        bounds = world_bounds(obj)
        ends = endpoint_clusters(obj)
        dump["objects"][name] = {"bounds": bounds, "transform": ends}
        print(
            f"OBJ {name} type={obj.type} hide={obj.hide_get()} "
            f"size={bounds['size'] if bounds else None} "
            f"min={bounds['min'] if bounds else None} "
            f"max={bounds['max'] if bounds else None}",
            flush=True,
        )
        if ends.get("belt") and ends.get("roof"):
            print(
                f"  BELT c={ends['belt']['center']} ROOF c={ends['roof']['center']} "
                f"rot={ends['rotation_euler']} scale={ends['scale']}",
                flush=True,
            )
    out = os.path.join(
        os.path.dirname(bpy.data.filepath) or ".",
        "review_interactive",
        "inspect_saved_v004.json",
    )
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(dump, handle, indent=2)
    print(f"WROTE {out}", flush=True)


if __name__ == "__main__":
    main()
    sys.exit(0)
