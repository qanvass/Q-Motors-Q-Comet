"""Create an editable Q Comet blockout in Blender.

Run from Blender's Scripting workspace. This is a proportion and component
planning tool; it does not generate production topology or GTA binary assets.
"""

import bpy
import math
import os
import sys
from mathutils import Vector


D = {
    "length": 4.86,
    "width": 1.94,
    "height": 1.43,
    "wheelbase": 2.95,
    "track": 1.67,
    "wheel_diameter": 0.76,
    "tire_width": 0.27,
}


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in list(bpy.data.collections):
        if collection.name != "Collection":
            bpy.data.collections.remove(collection)


def make_collection(name):
    collection = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(collection)
    return collection


def move_to_collection(obj, collection):
    for existing in list(obj.users_collection):
        existing.objects.unlink(obj)
    collection.objects.link(obj)


def material(name, color, metallic=0.0, roughness=0.45):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1.0)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)
        bsdf.inputs["Metallic"].default_value = metallic
        bsdf.inputs["Roughness"].default_value = roughness
    return mat


def rounded_box(name, location, scale, bevel, mat, collection):
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    modifier = obj.modifiers.new(name="BLOCKOUT_BEVEL", type="BEVEL")
    modifier.width = bevel
    modifier.segments = 3
    obj.data.materials.append(mat)
    move_to_collection(obj, collection)
    return obj


def wheel(name, location, tire_mat, rim_mat, collection):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=48,
        radius=D["wheel_diameter"] / 2,
        depth=D["tire_width"],
        location=location,
        rotation=(math.radians(90), 0, 0),
    )
    tire = bpy.context.object
    tire.name = name
    tire.data.materials.append(tire_mat)
    move_to_collection(tire, collection)

    bpy.ops.mesh.primitive_cylinder_add(
        vertices=32,
        radius=D["wheel_diameter"] * 0.36,
        depth=D["tire_width"] + 0.012,
        location=location,
        rotation=(math.radians(90), 0, 0),
    )
    rim = bpy.context.object
    rim.name = name.replace("wheel_", "rim_")
    rim.data.materials.append(rim_mat)
    move_to_collection(rim, collection)
    return tire


def empty(name, location, collection, display="PLAIN_AXES", size=0.18):
    obj = bpy.data.objects.new(name, None)
    obj.location = Vector(location)
    obj.empty_display_type = display
    obj.empty_display_size = size
    collection.objects.link(obj)
    return obj


def add_dimension_guides(collection):
    guides = {
        "GUIDE_front_extent": (0, D["length"] / 2, 0),
        "GUIDE_rear_extent": (0, -D["length"] / 2, 0),
        "GUIDE_right_extent": (D["width"] / 2, 0, 0),
        "GUIDE_left_extent": (-D["width"] / 2, 0, 0),
        "GUIDE_roof_extent": (0, 0, D["height"]),
        "GUIDE_ground": (0, 0, 0),
    }
    for name, location in guides.items():
        empty(name, location, collection)


def output_path():
    """Return an explicit path passed after `-- --output`, or a safe default."""
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if "--output" in args:
        index = args.index("--output")
        if index + 1 >= len(args):
            raise ValueError("--output requires a .blend path")
        return os.path.abspath(args[index + 1])
    return os.path.abspath("qcomet_blockout_v001.blend")


def build():
    clear_scene()
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "METERS"
    scene.unit_settings.scale_length = 1.0

    body_collection = make_collection("QCOMET_BODY_PANELS")
    glass_collection = make_collection("QCOMET_GLASS")
    running_collection = make_collection("QCOMET_RUNNING_GEAR")
    interior_collection = make_collection("QCOMET_INTERIOR_GUIDES")
    guide_collection = make_collection("QCOMET_DIMENSION_GUIDES")

    olive = material("M_QCOMET_OLIVE_BLOCKOUT", (0.25, 0.27, 0.16), metallic=0.35, roughness=0.42)
    bronze = material("M_QCOMET_BRONZE_BLOCKOUT", (0.38, 0.20, 0.07), metallic=0.75, roughness=0.28)
    carbon = material("M_QCOMET_CARBON_BLOCKOUT", (0.015, 0.018, 0.016), metallic=0.15, roughness=0.3)
    glass = material("M_QCOMET_GLASS_BLOCKOUT", (0.015, 0.025, 0.03), metallic=0.1, roughness=0.12)
    tan = material("M_QCOMET_TAN_BLOCKOUT", (0.48, 0.33, 0.20), metallic=0.0, roughness=0.62)
    rubber = material("M_QCOMET_TIRE_BLOCKOUT", (0.012, 0.012, 0.012), metallic=0.0, roughness=0.82)

    # Primary volumes. These are intentionally simple and fully editable.
    rounded_box("chassis", (0, 0, 0.67), (0.94, 2.39, 0.36), 0.22, olive, body_collection)
    rounded_box("cabin", (0, -0.16, 1.09), (0.79, 1.38, 0.34), 0.28, glass, glass_collection)
    rounded_box("bonnet", (0, 1.64, 0.86), (0.87, 0.73, 0.085), 0.08, olive, body_collection)
    rounded_box("boot", (0, -1.83, 0.84), (0.87, 0.46, 0.10), 0.08, olive, body_collection)

    # Separate doors with visible blockout panel gaps.
    panel_x = D["width"] / 2 + 0.004
    for side, x, prefix in (("left", -panel_x, "dside"), ("right", panel_x, "pside")):
        rounded_box(f"door_{prefix}_f", (x, 0.40, 0.78), (0.025, 0.68, 0.45), 0.025, olive, body_collection)
        rounded_box(f"door_{prefix}_r", (x, -0.90, 0.78), (0.025, 0.58, 0.45), 0.025, olive, body_collection)
        empty(f"PIVOT_door_{prefix}_f", (x, 1.07, 0.83), guide_collection)
        empty(f"PIVOT_door_{prefix}_r", (x, -0.33, 0.83), guide_collection)

    rounded_box("front_bumper_guide", (0, 2.39, 0.49), (0.92, 0.09, 0.25), 0.06, carbon, body_collection)
    rounded_box("rear_bumper_guide", (0, -2.39, 0.50), (0.92, 0.09, 0.24), 0.06, carbon, body_collection)
    rounded_box("dash_guide", (0, 0.58, 1.04), (0.72, 0.18, 0.12), 0.05, carbon, interior_collection)
    rounded_box("console_guide", (0, -0.05, 0.57), (0.22, 0.65, 0.16), 0.08, tan, interior_collection)

    wheel_z = D["wheel_diameter"] / 2
    half_track = D["track"] / 2
    half_wheelbase = D["wheelbase"] / 2
    positions = {
        "wheel_lf": (-half_track, half_wheelbase, wheel_z),
        "wheel_rf": (half_track, half_wheelbase, wheel_z),
        "wheel_lr": (-half_track, -half_wheelbase, wheel_z),
        "wheel_rr": (half_track, -half_wheelbase, wheel_z),
    }
    for name, location in positions.items():
        wheel(name, location, rubber, bronze, running_collection)

    empty("PIVOT_bonnet", (0, 0.92, 0.91), guide_collection)
    empty("PIVOT_boot", (0, -1.38, 0.91), guide_collection)
    empty("steeringwheel", (-0.38, 0.46, 1.02), interior_collection, display="CIRCLE", size=0.22)
    add_dimension_guides(guide_collection)

    scene["qcomet_status"] = "PROVISIONAL_BLOCKOUT"
    scene["qcomet_dimensions_note"] = "Requires Quasar approval before detailed modeling"
    scene["qcomet_front_axis"] = "+Y"

    # Make the chassis active and frame the full model.
    chassis = bpy.data.objects.get("chassis")
    if chassis:
        bpy.context.view_layer.objects.active = chassis
        chassis.select_set(True)
    destination = output_path()
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=destination)
    print(f"Q Comet provisional blockout created: {destination}")


if __name__ == "__main__":
    build()
