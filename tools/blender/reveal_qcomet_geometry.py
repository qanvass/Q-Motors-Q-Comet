"""Reveal existing Q Comet meshes for review. Does not save the .blend."""

from __future__ import annotations

import os
import sys

import bpy
from mathutils import Vector


REVIEW_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "vehicles",
        "qcomet",
        "source",
        "blender",
        "review_reveal",
    )
)


def log(msg):
    print(msg, flush=True)


def is_cutter(obj):
    name = obj.name.lower()
    return "cutter" in name or "guide" in name or name.startswith("ref_")


def is_reference_object(obj):
    if obj.name.startswith("REFIMG") or obj.name.startswith("REF_"):
        return True
    if "CONCEPT_REFERENCES" in {c.name for c in obj.users_collection}:
        return True
    if obj.type == "EMPTY" and getattr(obj, "empty_display_type", "") == "IMAGE":
        return True
    if obj.type == "MESH":
        for slot in obj.material_slots:
            mat = slot.material
            if mat is None:
                continue
            if getattr(mat, "use_nodes", False) and mat.node_tree:
                for node in mat.node_tree.nodes:
                    if node.type == "TEX_IMAGE" and node.image:
                        image_name = (node.image.name or "").lower()
                        image_path = (node.image.filepath or "").lower()
                        if "concept" in image_path or "ref" in image_name or "orthos" in image_path:
                            return True
        if obj.data.materials:
            for mat in obj.data.materials:
                if mat and mat.name.lower().startswith("ref"):
                    return True
    return False


def shading_has(name):
    return name in bpy.types.View3DShading.bl_rna.properties.keys()


def set_workbench(solid=True):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    if scene.render.engine != "BLENDER_WORKBENCH":
        raise RuntimeError(f"Could not use Workbench, engine is {scene.render.engine}")
    shading = scene.display.shading
    if solid:
        if shading_has("type"):
            shading.type = "SOLID"
        if shading_has("light"):
            shading.light = "STUDIO"
        if shading_has("color_type"):
            shading.color_type = "SINGLE"
        if shading_has("single_color"):
            shading.single_color = (0.55, 0.55, 0.55)
        if shading_has("show_xray"):
            shading.show_xray = False
        if shading_has("show_shadows"):
            shading.show_shadows = False
        if shading_has("show_cavity"):
            shading.show_cavity = False
        if shading_has("use_dof"):
            shading.use_dof = False
    else:
        # Workbench F12 ignores shading.type=WIREFRAME (blank world).
        # Keep Solid shading; the caller adds a temporary Wireframe cage.
        if shading_has("type"):
            shading.type = "SOLID"
        if shading_has("light"):
            shading.light = "FLAT"
        if shading_has("color_type"):
            shading.color_type = "SINGLE"
        if shading_has("single_color"):
            shading.single_color = (0.12, 0.12, 0.13)
        if shading_has("show_xray"):
            shading.show_xray = False
        if shading_has("show_shadows"):
            shading.show_shadows = False
        if shading_has("show_cavity"):
            shading.show_cavity = False
        if shading_has("use_dof"):
            shading.use_dof = False
    scene.render.resolution_x = 960
    scene.render.resolution_y = 540
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.use_stamp = False
    world = scene.world
    if world is None:
        world = bpy.data.worlds.new("QCOMET_REVEAL_WORLD")
        scene.world = world
    if hasattr(world, "color"):
        world.color = (0.45, 0.45, 0.47) if solid else (0.78, 0.78, 0.80)
    log(f"MILESTONE shading solid={solid}")


def vehicle_objects():
    skip_types = {"CAMERA", "LIGHT", "SPEAKER"}
    kept = []
    for obj in bpy.data.objects:
        if obj.type in skip_types:
            continue
        if is_reference_object(obj) or is_cutter(obj):
            continue
        if obj.hide_get() and obj.type != "MESH":
            continue
        if obj.type in {"MESH", "CURVE", "SURFACE", "META", "FONT"}:
            kept.append(obj)
        elif obj.type == "EMPTY" and obj.name == "steeringwheel":
            kept.append(obj)
    return kept


def evaluated_bounds(objects):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    mins = Vector((1e9, 1e9, 1e9))
    maxs = Vector((-1e9, -1e9, -1e9))
    count = 0
    for obj in objects:
        evaluated = obj.evaluated_get(depsgraph)
        if evaluated.type != "MESH":
            continue
        mesh = evaluated.to_mesh()
        try:
            matrix = evaluated.matrix_world
            for vertex in mesh.vertices:
                world = matrix @ vertex.co
                mins.x = min(mins.x, world.x)
                mins.y = min(mins.y, world.y)
                mins.z = min(mins.z, world.z)
                maxs.x = max(maxs.x, world.x)
                maxs.y = max(maxs.y, world.y)
                maxs.z = max(maxs.z, world.z)
                count += 1
        finally:
            evaluated.to_mesh_clear()
    if count == 0:
        raise RuntimeError("No evaluated mesh vertices for bounds")
    return mins, maxs


def point_camera(camera, location, target):
    camera.location = Vector(location)
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()


def add_temp_wireframe_cages(objects, thickness=0.018):
    added = 0
    for obj in objects:
        if obj.type != "MESH" or obj.data is None:
            continue
        if any(mod.type == "WIREFRAME" and mod.name.startswith("QCOMET_REVEAL") for mod in obj.modifiers):
            continue
        mod = obj.modifiers.new("QCOMET_REVEAL_WIRE", "WIREFRAME")
        mod.thickness = thickness
        mod.use_replace = True
        mod.use_boundary = True
        added += 1
    log(f"MILESTONE temp_wireframe_cages {added}")
    return added


def render_view(scene, camera, filename, location, target, ortho_scale, wire=False, vehicles=None):
    set_workbench(solid=not wire)
    if wire:
        add_temp_wireframe_cages(vehicles or [])
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = ortho_scale
    point_camera(camera, location, target)
    path = os.path.join(REVIEW_DIR, filename)
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    log(f"MILESTONE rendered {path} exists={os.path.isfile(path)} wire={wire}")
    return path


def main():
    log(f"MILESTONE loaded {bpy.data.filepath}")
    os.makedirs(REVIEW_DIR, exist_ok=True)

    refs = [obj for obj in bpy.data.objects if is_reference_object(obj)]
    log("MILESTONE references")
    for obj in refs:
        log(f"  REF {obj.name} type={obj.type} display={getattr(obj, 'empty_display_type', '')}")
        obj.hide_set(True)
        obj.hide_viewport = True
        obj.hide_render = True
    log(f"MILESTONE refs_hidden {len(refs)}")

    vehicles = vehicle_objects()
    bpy.ops.object.select_all(action="DESELECT")
    for obj in vehicles:
        obj.hide_set(False)
        obj.hide_viewport = False
        if obj.type == "MESH":
            obj.select_set(True)
    chassis = bpy.data.objects.get("chassis")
    if chassis:
        bpy.context.view_layer.objects.active = chassis
        chassis.select_set(True)
    log(f"MILESTONE vehicle_meshes {len(vehicles)}")

    depsgraph = bpy.context.evaluated_depsgraph_get()
    if chassis is None:
        raise RuntimeError("chassis object missing")
    chassis_eval = chassis.evaluated_get(depsgraph)
    chassis_mesh = chassis_eval.to_mesh()
    try:
        verts = len(chassis_mesh.vertices)
        faces = len(chassis_mesh.polygons)
    finally:
        chassis_eval.to_mesh_clear()
    log(f"CHASSIS_VERTS={verts}")
    log(f"CHASSIS_FACES={faces}")

    mins, maxs = evaluated_bounds(vehicles)
    size = maxs - mins
    center = (mins + maxs) * 0.5
    log(
        "VEHICLE_BOUNDS_M "
        f"x={size.x:.4f} y={size.y:.4f} z={size.z:.4f} "
        f"min=({mins.x:.4f},{mins.y:.4f},{mins.z:.4f}) "
        f"max=({maxs.x:.4f},{maxs.y:.4f},{maxs.z:.4f})"
    )

    scene = bpy.context.scene
    cam_data = bpy.data.cameras.new("QCOMET_REVEAL_CAMERA")
    camera = bpy.data.objects.new("QCOMET_REVEAL_CAMERA", cam_data)
    scene.collection.objects.link(camera)
    scene.camera = camera

    pad = 1.12
    front_scale = max(size.x, size.z) * pad
    side_scale = max(size.y, size.z) * pad
    top_scale = max(size.x, size.y) * pad
    target = (center.x, center.y, center.z)
    dist = max(size) * 3.0

    render_view(scene, camera, "qcomet_reveal_front.png", (center.x, center.y + dist, center.z), target, front_scale)
    render_view(scene, camera, "qcomet_reveal_side.png", (center.x + dist, center.y, center.z), target, side_scale)
    render_view(scene, camera, "qcomet_reveal_top.png", (center.x, center.y, center.z + dist), target, top_scale)
    render_view(
        scene,
        camera,
        "qcomet_reveal_three_quarter.png",
        (center.x + dist * 0.72, center.y + dist * 0.85, center.z + dist * 0.42),
        target,
        max(front_scale, side_scale),
    )
    render_view(
        scene,
        camera,
        "qcomet_reveal_three_quarter_wireframe.png",
        (center.x + dist * 0.72, center.y + dist * 0.85, center.z + dist * 0.42),
        target,
        max(front_scale, side_scale),
        wire=True,
        vehicles=vehicles,
    )
    log("MILESTONE complete_no_save")
    log("REVEAL_OK")


if __name__ == "__main__":
    main()
    sys.exit(0)
