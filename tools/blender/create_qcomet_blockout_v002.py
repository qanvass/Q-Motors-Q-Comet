"""Build the Q Comet v002 proportion blockout and its review contact sheet.

This remains a dimensional blockout. It intentionally excludes detailed
surfacing, production topology, lights, badges, and interior detailing.
"""

import math
import os
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Vector


ENVELOPE = {
    "length": 4.86,
    "width": 1.94,
    "height": 1.44,
    "wheelbase": 3.00,
    "front_track": 1.69,
    "rear_track": 1.68,
    "tire_diameter": 0.78,
    "tire_width": 0.28,
    "ground_clearance": 0.13,
}

CHASSIS_STATIONS = (
    (2.43, 0.52, 0.40, 0.70),
    (2.29, 0.78, 0.35, 0.81),
    (1.90, 0.91, 0.32, 0.92),
    (1.45, 0.97, 0.30, 0.98),
    (0.65, 0.97, 0.29, 0.99),
    (-0.35, 0.96, 0.29, 0.99),
    (-1.25, 0.94, 0.30, 0.96),
    (-1.88, 0.88, 0.33, 0.89),
    (-2.28, 0.74, 0.36, 0.78),
    (-2.43, 0.48, 0.41, 0.69),
)

GREENHOUSE_STATIONS = (
    (1.12, 0.52, 0.92, 1.06),
    (0.78, 0.68, 0.90, 1.32),
    (0.25, 0.77, 0.83, 1.43),
    (-0.55, 0.75, 0.82, 1.44),
    (-1.05, 0.66, 0.85, 1.32),
    (-1.42, 0.50, 0.90, 1.08),
)

WHEEL_LOCATIONS = {
    "wheel_lf": (-0.845, 1.50, 0.39),
    "wheel_rf": (0.845, 1.50, 0.39),
    "wheel_lr": (-0.845, -1.50, 0.39),
    "wheel_rr": (0.845, -1.50, 0.39),
}


def cli_value(name, default=None):
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    if name not in args:
        return default
    index = args.index(name)
    if index + 1 >= len(args):
        raise ValueError(f"{name} requires a value")
    return os.path.abspath(args[index + 1])


def clear_scene():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for collection in list(bpy.data.collections):
        bpy.data.collections.remove(collection)


def make_collection(name):
    collection = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(collection)
    return collection


def material(name, color, metallic=0.0, roughness=0.45):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1.0)
    mat.metallic = metallic
    mat.roughness = roughness
    return mat


def link_object(obj, collection):
    for current in list(obj.users_collection):
        current.objects.unlink(obj)
    collection.objects.link(obj)


def recalculate_normals(mesh):
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()


def loft(
    name,
    stations,
    ring_vertices,
    shape_power,
    mat,
    collection,
    subdivision=True,
):
    vertices = []
    exponent = 2.0 / shape_power

    for y, half_width, bottom_z, upper_z in stations:
        center_z = (bottom_z + upper_z) * 0.5
        half_height = (upper_z - bottom_z) * 0.5
        for index in range(ring_vertices):
            angle = -math.pi * 0.5 + math.tau * index / ring_vertices
            cosine = math.cos(angle)
            sine = math.sin(angle)
            x = half_width * math.copysign(abs(cosine) ** exponent, cosine)
            z = center_z + half_height * math.copysign(abs(sine) ** exponent, sine)
            vertices.append((x, y, z))

    faces = []
    station_count = len(stations)
    for station_index in range(station_count - 1):
        current = station_index * ring_vertices
        following = (station_index + 1) * ring_vertices
        for ring_index in range(ring_vertices):
            next_ring_index = (ring_index + 1) % ring_vertices
            faces.append(
                (
                    current + ring_index,
                    current + next_ring_index,
                    following + next_ring_index,
                    following + ring_index,
                )
            )

    faces.append(tuple(reversed(range(ring_vertices))))
    last_ring = (station_count - 1) * ring_vertices
    faces.append(tuple(last_ring + index for index in range(ring_vertices)))

    mesh = bpy.data.meshes.new(f"{name}_mesh")
    mesh.from_pydata(vertices, [], faces)
    recalculate_normals(mesh)
    for polygon in mesh.polygons:
        polygon.use_smooth = True

    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    obj.data.materials.append(mat)

    if subdivision:
        modifier = obj.modifiers.new(name="BLOCKOUT_SUBDIVISION", type="SUBSURF")
        modifier.subdivision_type = "CATMULL_CLARK"
        modifier.levels = 1
        modifier.render_levels = 1
        modifier.show_only_control_edges = True

    return obj


def box_from_extents(name, x_min, x_max, y_min, y_max, z_min, z_max, mat, collection, bevel=0.02):
    bpy.ops.mesh.primitive_cube_add(
        location=(
            (x_min + x_max) * 0.5,
            (y_min + y_max) * 0.5,
            (z_min + z_max) * 0.5,
        )
    )
    obj = bpy.context.object
    obj.name = name
    obj.scale = (
        (x_max - x_min) * 0.5,
        (y_max - y_min) * 0.5,
        (z_max - z_min) * 0.5,
    )
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    link_object(obj, collection)
    if bevel:
        modifier = obj.modifiers.new(name="BLOCKOUT_BEVEL", type="BEVEL")
        modifier.width = bevel
        modifier.segments = 2
    return obj


def thin_panel(name, x, y_min, y_max, z_min, z_max, thickness, mat, collection):
    half_thickness = thickness * 0.5
    half_y = (y_max - y_min) * 0.5
    half_z = (z_max - z_min) * 0.5
    vertices = [
        (-half_thickness, -half_y, -half_z),
        (-half_thickness, half_y, -half_z),
        (-half_thickness, half_y, half_z),
        (-half_thickness, -half_y, half_z),
        (half_thickness, -half_y, -half_z),
        (half_thickness, half_y, -half_z),
        (half_thickness, half_y, half_z),
        (half_thickness, -half_y, half_z),
    ]
    faces = (
        (0, 1, 2, 3),
        (4, 7, 6, 5),
        (0, 4, 5, 1),
        (1, 5, 6, 2),
        (2, 6, 7, 3),
        (4, 0, 3, 7),
    )
    mesh = bpy.data.meshes.new(f"{name}_mesh")
    mesh.from_pydata(vertices, [], faces)
    recalculate_normals(mesh)
    obj = bpy.data.objects.new(name, mesh)
    obj.location = (x, (y_min + y_max) * 0.5, (z_min + z_max) * 0.5)
    collection.objects.link(obj)
    obj.data.materials.append(mat)
    modifier = obj.modifiers.new(name="PANEL_EDGE_SOFTENING", type="BEVEL")
    modifier.width = min(0.006, thickness * 0.35)
    modifier.segments = 2
    return obj


def quad_panel(name, corners, thickness, mat, collection):
    upper = [Vector(corner) for corner in corners]
    lower = [Vector((corner[0], corner[1], corner[2] - thickness)) for corner in corners]
    vertices = [tuple(vertex) for vertex in upper + lower]
    faces = (
        (0, 1, 2, 3),
        (7, 6, 5, 4),
        (0, 4, 5, 1),
        (1, 5, 6, 2),
        (2, 6, 7, 3),
        (3, 7, 4, 0),
    )
    mesh = bpy.data.meshes.new(f"{name}_mesh")
    mesh.from_pydata(vertices, [], faces)
    recalculate_normals(mesh)
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    obj.data.materials.append(mat)
    modifier = obj.modifiers.new(name="PANEL_EDGE_SOFTENING", type="BEVEL")
    modifier.width = 0.006
    modifier.segments = 2
    return obj


def create_wheel(name, location, tire_mat, rim_mat, collection):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=64,
        radius=ENVELOPE["tire_diameter"] * 0.5,
        depth=ENVELOPE["tire_width"],
        location=location,
        rotation=(0.0, math.radians(90.0), 0.0),
    )
    tire = bpy.context.object
    tire.name = name
    tire.data.materials.append(tire_mat)
    link_object(tire, collection)
    tire_bevel = tire.modifiers.new(name="TIRE_EDGE_ROUNDING", type="BEVEL")
    tire_bevel.width = 0.045
    tire_bevel.segments = 3

    bpy.ops.mesh.primitive_cylinder_add(
        vertices=48,
        radius=0.285,
        depth=ENVELOPE["tire_width"] + 0.012,
        location=location,
        rotation=(0.0, math.radians(90.0), 0.0),
    )
    rim = bpy.context.object
    rim.name = name.replace("wheel_", "rim_")
    rim.data.materials.append(rim_mat)
    link_object(rim, collection)
    rim_bevel = rim.modifiers.new(name="RIM_EDGE_ROUNDING", type="BEVEL")
    rim_bevel.width = 0.018
    rim_bevel.segments = 2


def create_wheel_arch_cutters(chassis, locations, collection):
    subdivision = chassis.modifiers.get("BLOCKOUT_SUBDIVISION")
    if subdivision:
        chassis.modifiers.remove(subdivision)

    for wheel_name, location in locations.items():
        cutter_name = wheel_name.replace("wheel_", "wheel_arch_cutter_")
        bpy.ops.mesh.primitive_cylinder_add(
            vertices=64,
            radius=0.42,
            depth=0.34,
            location=location,
            rotation=(0.0, math.radians(90.0), 0.0),
        )
        cutter = bpy.context.object
        cutter.name = cutter_name
        link_object(cutter, collection)

        modifier = chassis.modifiers.new(name=f"CUT_{wheel_name.upper()}", type="BOOLEAN")
        modifier.operation = "DIFFERENCE"
        modifier.solver = "EXACT"
        modifier.object = cutter
        bpy.context.view_layer.objects.active = chassis
        chassis.select_set(True)
        bpy.ops.object.modifier_apply(modifier=modifier.name)
        chassis.select_set(False)

        cutter.display_type = "WIRE"
        cutter.hide_render = True
        cutter.hide_set(True)

    subdivision = chassis.modifiers.new(name="BLOCKOUT_SUBDIVISION", type="SUBSURF")
    subdivision.subdivision_type = "CATMULL_CLARK"
    subdivision.levels = 1
    subdivision.render_levels = 1
    subdivision.show_only_control_edges = True


def empty(name, location, collection, display="PLAIN_AXES", size=0.14):
    obj = bpy.data.objects.new(name, None)
    obj.location = location
    obj.empty_display_type = display
    obj.empty_display_size = size
    collection.objects.link(obj)
    return obj


def configure_scene(scene):
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "METERS"
    scene.unit_settings.scale_length = 1.0
    scene["qcomet_status"] = "PROVISIONAL_BLOCKOUT_V002"
    scene["qcomet_dimensions_note"] = "Awaiting proportion approval; detailed surfacing prohibited"
    scene["qcomet_front_axis"] = "+Y"
    scene["qcomet_passenger_axis"] = "+X"
    for key, value in ENVELOPE.items():
        scene[f"qcomet_{key}"] = value


def build_model():
    clear_scene()
    scene = bpy.context.scene
    configure_scene(scene)

    body_collection = make_collection("QCOMET_BODY_PANELS")
    glass_collection = make_collection("QCOMET_GLASS")
    running_collection = make_collection("QCOMET_RUNNING_GEAR")
    interior_collection = make_collection("QCOMET_INTERIOR_GUIDES")
    dimension_collection = make_collection("QCOMET_DIMENSION_GUIDES")
    construction_collection = make_collection("QCOMET_CONSTRUCTION_GUIDES")

    olive = material("M_QCOMET_OLIVE_BLOCKOUT", (0.25, 0.27, 0.16), metallic=0.32, roughness=0.40)
    bronze = material("M_QCOMET_BRONZE_BLOCKOUT", (0.38, 0.20, 0.07), metallic=0.72, roughness=0.28)
    carbon = material("M_QCOMET_CARBON_BLOCKOUT", (0.015, 0.018, 0.016), metallic=0.15, roughness=0.30)
    glass = material("M_QCOMET_GLASS_BLOCKOUT", (0.012, 0.024, 0.030), metallic=0.12, roughness=0.10)
    rubber = material("M_QCOMET_TIRE_BLOCKOUT", (0.010, 0.010, 0.010), roughness=0.82)

    chassis = loft(
        "chassis",
        CHASSIS_STATIONS,
        ring_vertices=24,
        shape_power=4.0,
        mat=olive,
        collection=body_collection,
    )
    loft(
        "panoramic_glass_greenhouse",
        GREENHOUSE_STATIONS,
        ring_vertices=24,
        shape_power=2.5,
        mat=glass,
        collection=glass_collection,
    )

    for wheel_name, location in WHEEL_LOCATIONS.items():
        create_wheel(wheel_name, location, rubber, bronze, running_collection)
    create_wheel_arch_cutters(chassis, WHEEL_LOCATIONS, construction_collection)

    thin_panel("door_dside_f", -0.966, -0.18, 0.92, 0.38, 0.96, 0.014, olive, body_collection)
    thin_panel("door_pside_f", 0.966, -0.18, 0.92, 0.38, 0.96, 0.014, olive, body_collection)
    thin_panel("door_dside_r", -0.958, -1.28, -0.20, 0.39, 0.94, 0.014, olive, body_collection)
    thin_panel("door_pside_r", 0.958, -1.28, -0.20, 0.39, 0.94, 0.014, olive, body_collection)

    quad_panel(
        "bonnet",
        (
            (-0.72, 2.24, 0.75),
            (0.72, 2.24, 0.75),
            (0.79, 1.10, 0.95),
            (-0.79, 1.10, 0.95),
        ),
        0.014,
        olive,
        body_collection,
    )
    quad_panel(
        "boot",
        (
            (-0.69, -2.23, 0.77),
            (-0.80, -1.42, 0.94),
            (0.80, -1.42, 0.94),
            (0.69, -2.23, 0.77),
        ),
        0.014,
        olive,
        body_collection,
    )

    box_from_extents("front_splitter", -0.91, 0.91, 2.18, 2.43, 0.19, 0.31, carbon, body_collection, 0.025)
    box_from_extents("rear_diffuser", -0.88, 0.88, -2.43, -2.16, 0.19, 0.32, carbon, body_collection, 0.025)
    box_from_extents("side_skirt_l", -0.97, -0.90, -1.67, 1.58, 0.20, 0.31, carbon, body_collection, 0.015)
    box_from_extents("side_skirt_r", 0.90, 0.97, -1.67, 1.58, 0.20, 0.31, carbon, body_collection, 0.015)

    empty("PIVOT_door_dside_f", (-0.966, 0.92, 0.67), dimension_collection)
    empty("PIVOT_door_pside_f", (0.966, 0.92, 0.67), dimension_collection)
    empty("PIVOT_door_dside_r", (-0.958, -0.20, 0.67), dimension_collection)
    empty("PIVOT_door_pside_r", (0.958, -0.20, 0.67), dimension_collection)
    empty("PIVOT_bonnet", (0.0, 1.10, 0.95), dimension_collection)
    empty("PIVOT_boot", (0.0, -1.42, 0.94), dimension_collection)
    empty("steeringwheel", (-0.38, 0.42, 1.02), interior_collection, display="CIRCLE", size=0.22)

    guides = {
        "GUIDE_front_extent": (0.0, 2.43, 0.0),
        "GUIDE_rear_extent": (0.0, -2.43, 0.0),
        "GUIDE_passenger_extent": (0.97, 0.0, 0.0),
        "GUIDE_driver_extent": (-0.97, 0.0, 0.0),
        "GUIDE_roof_extent": (0.0, 0.0, 1.44),
        "GUIDE_ground_clearance": (0.0, 0.0, 0.13),
    }
    for name, location in guides.items():
        empty(name, location, dimension_collection)

    bpy.context.view_layer.objects.active = chassis
    chassis.select_set(True)
    return scene


def point_camera(camera, location, target):
    camera.location = Vector(location)
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()


def render_review_views(scene, review_dir):
    os.makedirs(review_dir, exist_ok=True)
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = 1000
    scene.render.resolution_y = 760
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False

    shading = scene.display.shading
    shading.light = "STUDIO"
    shading.color_type = "MATERIAL"
    shading.background_type = "VIEWPORT"
    shading.background_color = (0.025, 0.030, 0.035)
    shading.show_shadows = True
    shading.show_cavity = True
    shading.cavity_type = "WORLD"
    shading.show_object_outline = True
    shading.object_outline_color = (0.008, 0.008, 0.008)

    scene.render.use_stamp = True
    scene.render.use_stamp_note = True
    scene.render.use_stamp_date = False
    scene.render.use_stamp_time = False
    scene.render.use_stamp_render_time = False
    scene.render.use_stamp_frame = False
    scene.render.use_stamp_frame_range = False
    scene.render.use_stamp_memory = False
    scene.render.use_stamp_hostname = False
    scene.render.use_stamp_camera = False
    scene.render.use_stamp_lens = False
    scene.render.use_stamp_scene = False
    scene.render.use_stamp_marker = False
    scene.render.use_stamp_filename = False
    scene.render.use_stamp_sequencer_strip = False
    scene.render.stamp_font_size = 28
    scene.render.stamp_foreground = (1.0, 1.0, 1.0, 1.0)
    scene.render.stamp_background = (0.0, 0.0, 0.0, 0.65)

    camera_data = bpy.data.cameras.new("QCOMET_REVIEW_CAMERA")
    camera = bpy.data.objects.new("QCOMET_REVIEW_CAMERA", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera

    target = (0.0, 0.0, 0.70)
    views = (
        ("front", "FRONT", (0.0, 8.0, 0.70), "ORTHO", 1.90),
        ("side", "SIDE", (8.0, 0.0, 0.70), "ORTHO", 4.25),
        ("top", "TOP", (0.0, 0.0, 8.0), "ORTHO", 5.45),
        (
            "front_three_quarter",
            "FRONT THREE-QUARTER",
            (5.8, 7.8, 4.2),
            "PERSP",
            None,
        ),
    )

    paths = []
    for filename, label, location, camera_type, ortho_scale in views:
        camera.data.type = camera_type
        if camera_type == "ORTHO":
            camera.data.ortho_scale = ortho_scale
        else:
            camera.data.lens = 55
        point_camera(camera, location, target)
        scene.render.stamp_note_text = label
        path = os.path.join(review_dir, f"qcomet_blockout_v002_{filename}.png")
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        paths.append(path)
        print(f"Rendered review view: {path}")

    loaded = [bpy.data.images.load(path, check_existing=False) for path in paths]
    width, height = loaded[0].size
    canvas = np.zeros((height * 2, width * 2, 4), dtype=np.float32)
    canvas[:, :, 3] = 1.0

    arrays = []
    for image in loaded:
        pixels = np.empty(width * height * 4, dtype=np.float32)
        image.pixels.foreach_get(pixels)
        arrays.append(pixels.reshape((height, width, 4)))

    canvas[height : height * 2, 0:width] = arrays[0]
    canvas[height : height * 2, width : width * 2] = arrays[1]
    canvas[0:height, 0:width] = arrays[2]
    canvas[0:height, width : width * 2] = arrays[3]

    contact_sheet = bpy.data.images.new(
        "QCOMET_V002_CONTACT_SHEET",
        width=width * 2,
        height=height * 2,
        alpha=True,
    )
    contact_sheet.pixels.foreach_set(canvas.ravel())
    contact_sheet.file_format = "PNG"
    contact_sheet.filepath_raw = os.path.join(review_dir, "qcomet_blockout_v002_contact_sheet.png")
    contact_sheet.save()
    print(f"Rendered contact sheet: {contact_sheet.filepath_raw}")


def main():
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    default_output = os.path.join(
        project_root,
        "vehicles",
        "qcomet",
        "source",
        "blender",
        "qcomet_blockout_v002.blend",
    )
    output_path = cli_value("--output", default_output)
    review_dir = cli_value(
        "--review-dir",
        os.path.join(project_root, "vehicles", "qcomet", "source", "blender", "review_v002"),
    )

    scene = build_model()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=output_path)
    print(f"Saved Q Comet v002 blockout: {output_path}")
    render_review_views(scene, review_dir)


if __name__ == "__main__":
    main()
