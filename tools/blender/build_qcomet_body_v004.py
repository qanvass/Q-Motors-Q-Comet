"""Q Comet v004 greenhouse and fastback pass from the v002 blockout.

Loads qcomet_blockout_v002.blend, does not overwrite v001/v002/v003, and
writes qcomet_body_v004.blend. Rebuilds the window graphic against the
four-side concept sheet: body shell stops at the belt, glass is a separate
fastback DLO, studio lighting is bright enough to read olive.
"""

from __future__ import annotations

import math
import os
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Vector


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
V002_PATH = os.path.join(
    PROJECT_ROOT,
    "vehicles",
    "qcomet",
    "source",
    "blender",
    "qcomet_blockout_v002.blend",
)
DEFAULT_OUTPUT = os.path.join(
    PROJECT_ROOT,
    "vehicles",
    "qcomet",
    "source",
    "blender",
    "qcomet_body_v004.blend",
)
DEFAULT_REVIEW = os.path.join(
    PROJECT_ROOT,
    "vehicles",
    "qcomet",
    "source",
    "blender",
    "review_v004",
)

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

# y, shoulder half-width, rocker half-width, roof half-width,
# underbody z, rocker z, belt z, shoulder z, roof z
STATIONS = (
    {"y": 2.43, "hw": 0.40, "hw_rk": 0.37, "hw_rf": 0.08, "z0": 0.21, "z_rk": 0.31, "z_belt": 0.61, "z_sh": 0.70, "z_rf": 0.72},
    {"y": 2.30, "hw": 0.76, "hw_rk": 0.70, "hw_rf": 0.16, "z0": 0.18, "z_rk": 0.30, "z_belt": 0.67, "z_sh": 0.76, "z_rf": 0.78},
    {"y": 2.12, "hw": 0.88, "hw_rk": 0.82, "hw_rf": 0.22, "z0": 0.16, "z_rk": 0.28, "z_belt": 0.74, "z_sh": 0.83, "z_rf": 0.85},
    {"y": 1.78, "hw": 0.94, "hw_rk": 0.88, "hw_rf": 0.32, "z0": 0.15, "z_rk": 0.26, "z_belt": 0.84, "z_sh": 0.92, "z_rf": 0.94},
    {"y": 1.50, "hw": 0.97, "hw_rk": 0.91, "hw_rf": 0.38, "z0": 0.14, "z_rk": 0.25, "z_belt": 0.88, "z_sh": 0.96, "z_rf": 0.98},
    {"y": 1.16, "hw": 0.97, "hw_rk": 0.91, "hw_rf": 0.78, "z0": 0.14, "z_rk": 0.24, "z_belt": 0.94, "z_sh": 1.00, "z_rf": 1.02},
    {"y": 0.72, "hw": 0.97, "hw_rk": 0.91, "hw_rf": 0.86, "z0": 0.14, "z_rk": 0.23, "z_belt": 0.96, "z_sh": 1.02, "z_rf": 1.04},
    {"y": 0.08, "hw": 0.97, "hw_rk": 0.91, "hw_rf": 0.88, "z0": 0.14, "z_rk": 0.23, "z_belt": 0.96, "z_sh": 1.02, "z_rf": 1.04},
    {"y": -0.52, "hw": 0.96, "hw_rk": 0.90, "hw_rf": 0.86, "z0": 0.14, "z_rk": 0.23, "z_belt": 0.95, "z_sh": 1.01, "z_rf": 1.03},
    {"y": -1.02, "hw": 0.95, "hw_rk": 0.89, "hw_rf": 0.78, "z0": 0.14, "z_rk": 0.24, "z_belt": 0.92, "z_sh": 0.99, "z_rf": 1.01},
    {"y": -1.50, "hw": 0.97, "hw_rk": 0.91, "hw_rf": 0.38, "z0": 0.14, "z_rk": 0.25, "z_belt": 0.86, "z_sh": 0.96, "z_rf": 1.00},
    {"y": -1.88, "hw": 0.89, "hw_rk": 0.84, "hw_rf": 0.26, "z0": 0.16, "z_rk": 0.27, "z_belt": 0.80, "z_sh": 0.90, "z_rf": 0.93},
    {"y": -2.22, "hw": 0.72, "hw_rk": 0.68, "hw_rf": 0.18, "z0": 0.18, "z_rk": 0.29, "z_belt": 0.72, "z_sh": 0.82, "z_rf": 0.86},
    {"y": -2.43, "hw": 0.40, "hw_rk": 0.37, "hw_rf": 0.08, "z0": 0.20, "z_rk": 0.31, "z_belt": 0.60, "z_sh": 0.70, "z_rf": 0.72},
)

WHEEL_LOCATIONS = {
    "wheel_lf": (-0.845, 1.50, 0.39),
    "wheel_rf": (0.845, 1.50, 0.39),
    "wheel_lr": (-0.845, -1.50, 0.39),
    "wheel_rr": (0.845, -1.50, 0.39),
}

GREENHOUSE = (
    (1.12, 0.56, 0.98, 1.10),
    (0.78, 0.70, 0.96, 1.34),
    (0.12, 0.74, 0.95, 1.40),
    (-0.48, 0.72, 0.94, 1.38),
    (-1.02, 0.58, 0.97, 1.20),
    (-1.40, 0.44, 1.00, 1.06),
)


def cli_value(name, default=None):
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    if name not in args:
        return default
    index = args.index(name)
    if index + 1 >= len(args):
        raise ValueError(f"{name} requires a value")
    return os.path.abspath(args[index + 1])


def lerp(a, b, t):
    return a + (b - a) * t


def station_at(y):
    if y >= STATIONS[0]["y"]:
        return dict(STATIONS[0])
    if y <= STATIONS[-1]["y"]:
        return dict(STATIONS[-1])
    for index in range(len(STATIONS) - 1):
        a = STATIONS[index]
        b = STATIONS[index + 1]
        if a["y"] >= y >= b["y"]:
            span = a["y"] - b["y"]
            t = 0.0 if span == 0 else (a["y"] - y) / span
            return {key: lerp(a[key], b[key], t) for key in a}
    return dict(STATIONS[-1])


def make_collection(name):
    existing = bpy.data.collections.get(name)
    if existing:
        return existing
    collection = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(collection)
    return collection


def link_object(obj, collection):
    for current in list(obj.users_collection):
        current.objects.unlink(obj)
    if obj.name not in collection.objects:
        collection.objects.link(obj)


def set_active(obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def recalculate_normals(mesh):
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()


def new_mesh_object(name, vertices, faces, mat, collection, smooth=True, bevel=0.0, subsurf=False):
    mesh = bpy.data.meshes.new(f"{name}_mesh")
    mesh.from_pydata(vertices, [], faces)
    recalculate_normals(mesh)
    if smooth:
        for polygon in mesh.polygons:
            polygon.use_smooth = True
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    if mat is not None:
        obj.data.materials.append(mat)
    if bevel:
        modifier = obj.modifiers.new(name="EDGE_SOFTENING", type="BEVEL")
        modifier.width = bevel
        modifier.segments = 2
        modifier.limit_method = "ANGLE"
        modifier.angle_limit = math.radians(30.0)
    if subsurf:
        modifier = obj.modifiers.new(name="BODY_SUBSURF", type="SUBSURF")
        modifier.subdivision_type = "CATMULL_CLARK"
        modifier.levels = 1
        modifier.render_levels = 1
        modifier.show_only_control_edges = True
    return obj


def principled_material(name, color, metallic=0.0, roughness=0.45, emission=None, transmission=0.0, alpha=1.0, coat=0.0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color[:3], alpha)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*color[:3], 1.0)
        bsdf.inputs["Metallic"].default_value = metallic
        bsdf.inputs["Roughness"].default_value = roughness
        if "Coat Weight" in bsdf.inputs:
            bsdf.inputs["Coat Weight"].default_value = coat
        if "Transmission Weight" in bsdf.inputs:
            bsdf.inputs["Transmission Weight"].default_value = transmission
        elif "Transmission" in bsdf.inputs:
            bsdf.inputs["Transmission"].default_value = transmission
        bsdf.inputs["Alpha"].default_value = alpha
        if emission:
            emit_color, strength = emission
            if "Emission Color" in bsdf.inputs:
                bsdf.inputs["Emission Color"].default_value = (*emit_color[:3], 1.0)
            if "Emission Strength" in bsdf.inputs:
                bsdf.inputs["Emission Strength"].default_value = strength
    if alpha < 1.0 or transmission > 0.0:
        mat.blend_method = "BLEND"
        if hasattr(mat, "shadow_method"):
            mat.shadow_method = "HASHED"
        if hasattr(mat, "use_screen_refraction"):
            mat.use_screen_refraction = True
    return mat


def box(name, x_min, x_max, y_min, y_max, z_min, z_max, mat, collection, bevel=0.012):
    vertices = [
        (x_min, y_min, z_min),
        (x_max, y_min, z_min),
        (x_max, y_max, z_min),
        (x_min, y_max, z_min),
        (x_min, y_min, z_max),
        (x_max, y_min, z_max),
        (x_max, y_max, z_max),
        (x_min, y_max, z_max),
    ]
    faces = (
        (0, 1, 2, 3),
        (4, 7, 6, 5),
        (0, 4, 5, 1),
        (1, 5, 6, 2),
        (2, 6, 7, 3),
        (3, 7, 4, 0),
    )
    return new_mesh_object(name, vertices, faces, mat, collection, bevel=bevel)


def apply_boolean(target, cutter, name, operation="DIFFERENCE"):
    set_active(target)
    modifier = target.modifiers.new(name=name, type="BOOLEAN")
    modifier.operation = operation
    modifier.solver = "EXACT"
    modifier.object = cutter
    bpy.ops.object.modifier_apply(modifier=name)


def empty(name, location, collection, display="PLAIN_AXES", size=0.12):
    obj = bpy.data.objects.new(name, None)
    obj.location = location
    obj.empty_display_type = display
    obj.empty_display_size = size
    collection.objects.link(obj)
    return obj


def report_sollumz():
    names = list(bpy.context.preferences.addons.keys())
    found = [name for name in names if "sollum" in name.lower()]
    if found:
        print(f"SOLLUMZ_ADDONS={','.join(found)}")
    else:
        print("SOLLUMZ_ADDONS=NOT_ENABLED")
    return found


def load_v002():
    current = bpy.data.filepath.replace("/", os.sep)
    if os.path.normcase(current) != os.path.normcase(V002_PATH):
        if not os.path.isfile(V002_PATH):
            raise FileNotFoundError(V002_PATH)
        bpy.ops.wm.open_mainfile(filepath=V002_PATH)
    print(f"Loaded blockout: {bpy.data.filepath}")


def archive_blockout():
    reference = make_collection("QCOMET_V002_BLOCKOUT_REFERENCE")
    reference.hide_viewport = True
    reference.hide_render = True
    for obj in list(bpy.data.objects):
        if obj.name.startswith("REF_"):
            continue
        base = obj.name
        obj.name = f"REF_{base}"
        obj.hide_viewport = True
        obj.hide_render = True
        obj.hide_set(True)
        obj.display_type = "WIRE"
        link_object(obj, reference)
    print(f"Archived v002 objects: {len(reference.objects)}")


def ring_from_station(station):
    y = station["y"]
    hw = station["hw"]
    hw_rk = station["hw_rk"]
    hw_rf = station["hw_rf"]
    z0 = station["z0"]
    z_rk = station["z_rk"]
    z_belt = station["z_belt"]
    z_sh = station["z_sh"]
    z_rf = station["z_rf"]
    half = [
        (0.0, y, z0),
        (hw_rk * 0.42, y, z0 + 0.008),
        (hw_rk * 0.88, y, z_rk),
        (hw, y, z_rk + (z_belt - z_rk) * 0.28),
        (hw + 0.010, y, z_rk + (z_belt - z_rk) * 0.62),
        (hw + 0.004, y, z_sh),
        (hw * 0.97, y, z_belt),
        (hw_rf + (hw - hw_rf) * 0.42, y, z_belt + 0.06),
        (hw_rf * 1.08, y, (z_belt + z_rf) * 0.55),
        (hw_rf, y, z_rf - 0.012),
        (hw_rf * 0.48, y, z_rf),
        (0.0, y, z_rf + 0.004),
    ]
    left = [(-x, y, z) for x, y, z in reversed(half[1:-1])]
    return half + left


def loft_stations(name, stations, mat, collection, subsurf=True):
    rings = [ring_from_station(station) for station in stations]
    ring_len = len(rings[0])
    vertices = [vertex for ring in rings for vertex in ring]
    faces = []
    for station_index in range(len(rings) - 1):
        current = station_index * ring_len
        following = (station_index + 1) * ring_len
        for ring_index in range(ring_len):
            next_index = (ring_index + 1) % ring_len
            faces.append(
                (
                    current + ring_index,
                    current + next_index,
                    following + next_index,
                    following + ring_index,
                )
            )
    faces.append(tuple(reversed(range(ring_len))))
    last = (len(rings) - 1) * ring_len
    faces.append(tuple(last + index for index in range(ring_len)))
    return new_mesh_object(name, vertices, faces, mat, collection, subsurf=subsurf)


def loft_simple(name, stations, ring_vertices, shape_power, mat, collection):
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
    for station_index in range(len(stations) - 1):
        current = station_index * ring_vertices
        following = (station_index + 1) * ring_vertices
        for ring_index in range(ring_vertices):
            next_index = (ring_index + 1) % ring_vertices
            faces.append(
                (
                    current + ring_index,
                    current + next_index,
                    following + next_index,
                    following + ring_index,
                )
            )
    faces.append(tuple(reversed(range(ring_vertices))))
    last = (len(stations) - 1) * ring_vertices
    faces.append(tuple(last + index for index in range(ring_vertices)))
    return new_mesh_object(name, vertices, faces, mat, collection, subsurf=True)


def cut_wheel_arches(chassis, construction):
    subsurf = chassis.modifiers.get("BODY_SUBSURF")
    if subsurf:
        chassis.modifiers.remove(subsurf)
    for wheel_name, location in WHEEL_LOCATIONS.items():
        cutter_name = wheel_name.replace("wheel_", "wheel_arch_cutter_")
        bpy.ops.mesh.primitive_cylinder_add(
            vertices=48,
            radius=0.43,
            depth=0.38,
            location=location,
            rotation=(0.0, math.radians(90.0), 0.0),
        )
        cutter = bpy.context.object
        cutter.name = cutter_name
        link_object(cutter, construction)
        apply_boolean(chassis, cutter, f"CUT_{wheel_name.upper()}")
        cutter.display_type = "WIRE"
        cutter.hide_render = True
        cutter.hide_set(True)
    modifier = chassis.modifiers.new(name="BODY_SUBSURF", type="SUBSURF")
    modifier.subdivision_type = "CATMULL_CLARK"
    modifier.levels = 1
    modifier.render_levels = 1


def side_x(station, z, extra=0.0):
    z0 = station["z0"]
    z_rk = station["z_rk"]
    z_sh = station["z_sh"]
    z_belt = station["z_belt"]
    z_rf = station["z_rf"]
    hw = station["hw"]
    hw_rk = station["hw_rk"]
    hw_rf = station["hw_rf"]
    if z <= z_rk:
        t = 0.0 if z_rk == z0 else max(0.0, min(1.0, (z - z0) / (z_rk - z0)))
        return lerp(hw_rk * 0.55, hw_rk, t) + extra
    if z <= z_sh:
        t = 0.0 if z_sh == z_rk else max(0.0, min(1.0, (z - z_rk) / (z_sh - z_rk)))
        return lerp(hw_rk, hw + 0.008, t) + extra
    if z <= z_belt:
        t = 0.0 if z_belt == z_sh else max(0.0, min(1.0, (z - z_sh) / (z_belt - z_sh)))
        return lerp(hw + 0.008, hw * 0.97, t) + extra
    t = 0.0 if z_rf == z_belt else max(0.0, min(1.0, (z - z_belt) / (z_rf - z_belt)))
    return lerp(hw * 0.97, hw_rf, t) + extra


def panel_grid(name, y0, y1, z0, z1, x_sign, thickness, mat, collection, y_steps=8, z_steps=6, extra=0.006):
    vertices = []
    faces = []
    for yi in range(y_steps):
        y = lerp(y0, y1, yi / (y_steps - 1))
        station = station_at(y)
        for zi in range(z_steps):
            z = lerp(z0, z1, zi / (z_steps - 1))
            x = x_sign * side_x(station, z, extra=extra)
            vertices.append((x, y, z))
    for yi in range(y_steps):
        y = lerp(y0, y1, yi / (y_steps - 1))
        station = station_at(y)
        for zi in range(z_steps):
            z = lerp(z0, z1, zi / (z_steps - 1))
            x = x_sign * side_x(station, z, extra=extra - thickness)
            vertices.append((x, y, z))
    def idx(layer, yi, zi):
        return layer * y_steps * z_steps + yi * z_steps + zi

    for yi in range(y_steps - 1):
        for zi in range(z_steps - 1):
            faces.append((idx(0, yi, zi), idx(0, yi + 1, zi), idx(0, yi + 1, zi + 1), idx(0, yi, zi + 1)))
            faces.append((idx(1, yi, zi), idx(1, yi, zi + 1), idx(1, yi + 1, zi + 1), idx(1, yi + 1, zi)))
    for yi in range(y_steps - 1):
        faces.append((idx(0, yi, 0), idx(1, yi, 0), idx(1, yi + 1, 0), idx(0, yi + 1, 0)))
        faces.append((idx(0, yi, z_steps - 1), idx(0, yi + 1, z_steps - 1), idx(1, yi + 1, z_steps - 1), idx(1, yi, z_steps - 1)))
    for zi in range(z_steps - 1):
        faces.append((idx(0, 0, zi), idx(0, 0, zi + 1), idx(1, 0, zi + 1), idx(1, 0, zi)))
        faces.append((idx(0, y_steps - 1, zi), idx(1, y_steps - 1, zi), idx(1, y_steps - 1, zi + 1), idx(0, y_steps - 1, zi + 1)))
    return new_mesh_object(name, vertices, faces, mat, collection, bevel=0.004)


def hood_panel(mat, collection):
    y_steps, x_steps = 10, 11
    y0, y1 = 1.14, 2.26
    vertices = []
    for yi in range(y_steps):
        y = lerp(y0, y1, yi / (y_steps - 1))
        station = station_at(y)
        half = station["hw"] * 0.78
        for xi in range(x_steps):
            x = lerp(-half, half, xi / (x_steps - 1))
            channel = 0.018 * math.exp(-((abs(x) - 0.30) ** 2) / 0.018)
            z = station["z_sh"] + 0.012 - channel - 0.04 * ((y - y0) / (y1 - y0))
            vertices.append((x, y, z))
    lower = [(x, y, z - 0.014) for x, y, z in vertices]
    verts = vertices + lower
    faces = []
    def idx(layer, yi, xi):
        return layer * y_steps * x_steps + yi * x_steps + xi
    for yi in range(y_steps - 1):
        for xi in range(x_steps - 1):
            faces.append((idx(0, yi, xi), idx(0, yi, xi + 1), idx(0, yi + 1, xi + 1), idx(0, yi + 1, xi)))
            faces.append((idx(1, yi, xi), idx(1, yi + 1, xi), idx(1, yi + 1, xi + 1), idx(1, yi, xi + 1)))
    return new_mesh_object("bonnet", verts, faces, mat, collection, bevel=0.005, subsurf=True)


def boot_panel(mat, collection):
    y_steps, x_steps = 8, 11
    y0, y1 = -2.24, -1.38
    vertices = []
    for yi in range(y_steps):
        y = lerp(y0, y1, yi / (y_steps - 1))
        station = station_at(y)
        half = station["hw"] * 0.82
        t = (y - y0) / (y1 - y0)
        ducktail = 0.016 * math.exp(-((t) ** 2) / 0.08)
        for xi in range(x_steps):
            x = lerp(-half, half, xi / (x_steps - 1))
            z = station["z_sh"] + 0.008 + ducktail
            vertices.append((x, y, z))
    lower = [(x, y, z - 0.014) for x, y, z in vertices]
    verts = vertices + lower
    faces = []
    def idx(layer, yi, xi):
        return layer * y_steps * x_steps + yi * x_steps + xi
    for yi in range(y_steps - 1):
        for xi in range(x_steps - 1):
            faces.append((idx(0, yi, xi), idx(0, yi + 1, xi), idx(0, yi + 1, xi + 1), idx(0, yi, xi + 1)))
            faces.append((idx(1, yi, xi), idx(1, yi, xi + 1), idx(1, yi + 1, xi + 1), idx(1, yi + 1, xi)))
    return new_mesh_object("boot", verts, faces, mat, collection, bevel=0.005, subsurf=True)


def dimple_intake(mat, collection):
    x_count, z_count = 18, 7
    x_min, x_max = -0.42, 0.42
    z_min, z_max = 0.34, 0.52
    y_face = 2.355
    vertices = []
    faces = []
    for zi in range(z_count):
        for xi in range(x_count):
            x = lerp(x_min, x_max, xi / (x_count - 1))
            z = lerp(z_min, z_max, zi / (z_count - 1))
            hex_phase = (xi + (zi % 2) * 0.5)
            dent = 0.011 if (int(hex_phase) + zi) % 2 == 0 else 0.003
            fade = 1.0 - min(1.0, abs(x) / 0.42)
            vertices.append((x, y_face - dent * fade, z))
    for zi in range(z_count):
        for xi in range(x_count):
            x = lerp(x_min, x_max, xi / (x_count - 1))
            z = lerp(z_min, z_max, zi / (z_count - 1))
            vertices.append((x, y_face - 0.016, z))
    def idx(layer, zi, xi):
        return layer * z_count * x_count + zi * x_count + xi
    for zi in range(z_count - 1):
        for xi in range(x_count - 1):
            faces.append((idx(0, zi, xi), idx(0, zi, xi + 1), idx(0, zi + 1, xi + 1), idx(0, zi + 1, xi)))
            faces.append((idx(1, zi, xi), idx(1, zi + 1, xi), idx(1, zi + 1, xi + 1), idx(1, zi, xi + 1)))
    return new_mesh_object("front_dimple_intake", vertices, faces, mat, collection, bevel=0.002)


def ribbon(name, points, width, height, mat, collection):
    vertices = []
    faces = []
    for point in points:
        x, y, z = point
        vertices.extend(
            [
                (x, y, z + height * 0.5),
                (x, y + width, z + height * 0.5),
                (x, y + width, z - height * 0.5),
                (x, y, z - height * 0.5),
            ]
        )
    for index in range(len(points) - 1):
        a = index * 4
        b = (index + 1) * 4
        faces.append((a, a + 1, b + 1, b))
        faces.append((a + 1, a + 2, b + 2, b + 1))
        faces.append((a + 2, a + 3, b + 3, b + 2))
        faces.append((a + 3, a, b, b + 3))
    faces.append((0, 3, 2, 1))
    last = (len(points) - 1) * 4
    faces.append((last, last + 1, last + 2, last + 3))
    return new_mesh_object(name, vertices, faces, mat, collection, bevel=0.0015)


def headlight_blades(side, emit_mat, lens_mat, collection):
    sign = -1.0 if side == "dside" else 1.0
    prefix = f"headlight_{side}"
    blades = []
    for index, z in enumerate((0.58, 0.66, 0.74)):
        points = []
        for step in range(14):
            t = step / 13.0
            x = sign * lerp(0.48, 0.86, t)
            y = lerp(2.33, 2.16, t)
            wave = 0.014 * math.sin(t * math.pi * 2.4 + index * 0.55)
            points.append((x, y, z + wave))
        blades.append(ribbon(f"{prefix}_blade_{index + 1}", points, 0.014, 0.006, emit_mat, collection))
    housing = box(
        f"{prefix}_housing",
        sign * 0.50 if sign > 0 else sign * 0.84,
        sign * 0.84 if sign > 0 else sign * 0.50,
        2.20,
        2.34,
        0.55,
        0.78,
        lens_mat,
        collection,
        bevel=0.008,
    )
    return blades + [housing]


def front_drl(side, emit_mat, collection):
    sign = -1.0 if side == "dside" else 1.0
    x = sign * 0.88
    points = [(x, 2.30, z) for z in (0.28, 0.34, 0.42, 0.50, 0.56)]
    return ribbon(f"drl_{side}", points, 0.016, 0.008, emit_mat, collection)


def rear_light_bar(emit_mat, brake_mat, lens_mat, collection):
    objects = []
    for layer, z0, mat, label in (
        (0, 0.78, emit_mat, "tail_bar_running"),
        (1, 0.81, brake_mat, "tail_bar_brake"),
    ):
        points = []
        for step in range(25):
            t = step / 24.0
            x = lerp(-0.82, 0.82, t)
            wave = 0.016 * math.sin(t * math.pi * 3.0) + 0.008 * math.sin(t * math.pi * 7.0 + layer)
            y = -2.30 - 0.01 * abs(math.sin(t * math.pi))
            points.append((x, y, z0 + wave))
        objects.append(ribbon(label, points, 0.022, 0.010, mat, collection))
    objects.append(box("tail_lens", -0.86, 0.86, -2.34, -2.24, 0.70, 0.90, lens_mat, collection, 0.008))
    return objects


def q_plus_badge(name, location, normal_y, mat, collection, scale=0.046):
    ring_verts = []
    faces = []
    segments = 20
    for index in range(segments):
        angle = math.tau * index / segments
        skip = 1.2 < angle < 1.7
        inner = 0.55 * scale if not skip else 0.0
        outer = scale
        c, s = math.cos(angle), math.sin(angle)
        x = location[0] + c * outer
        z = location[2] + s * outer
        y = location[1]
        ring_verts.append((x, y, z))
        ring_verts.append((location[0] + c * inner, y - 0.004 * normal_y, location[2] + s * inner))
    for index in range(segments):
        a = index * 2
        b = ((index + 1) % segments) * 2
        faces.append((a, b, b + 1, a + 1))
    plus = [
        (location[0] - 0.007, location[1] + 0.006 * normal_y, location[2] - 0.022),
        (location[0] + 0.007, location[1] + 0.006 * normal_y, location[2] - 0.022),
        (location[0] + 0.007, location[1] + 0.006 * normal_y, location[2] + 0.022),
        (location[0] - 0.007, location[1] + 0.006 * normal_y, location[2] + 0.022),
    ]
    plus += [(x, y - 0.008 * normal_y, z) for x, y, z in plus]
    offset = len(ring_verts)
    ring_verts.extend(plus)
    faces.extend(
        (
            (offset, offset + 1, offset + 2, offset + 3),
            (offset + 4, offset + 7, offset + 6, offset + 5),
        )
    )
    return new_mesh_object(name, ring_verts, faces, mat, collection, bevel=0.001)


def make_wheel(name, location, tire_mat, rim_mat, bronze_mat, caliper_mat, rubber_mat, collection):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=48,
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
    tire_bevel.width = 0.04
    tire_bevel.segments = 3

    bpy.ops.mesh.primitive_cylinder_add(
        vertices=36,
        radius=0.27,
        depth=ENVELOPE["tire_width"] * 0.62,
        location=(location[0] + (0.03 if location[0] > 0 else -0.03), location[1], location[2]),
        rotation=(0.0, math.radians(90.0), 0.0),
    )
    rim = bpy.context.object
    rim.name = name.replace("wheel_", "rim_")
    rim.data.materials.append(rim_mat)
    link_object(rim, collection)

    sign = 1.0 if location[0] > 0 else -1.0
    hub_x = location[0] + sign * 0.06
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=24,
        radius=0.055,
        depth=0.04,
        location=(hub_x, location[1], location[2]),
        rotation=(0.0, math.radians(90.0), 0.0),
    )
    hub = bpy.context.object
    hub.name = name.replace("wheel_", "hub_")
    hub.data.materials.append(bronze_mat)
    link_object(hub, collection)

    for spoke_index in range(10):
        angle = math.tau * spoke_index / 10.0
        bpy.ops.mesh.primitive_cube_add(location=(hub_x, location[1], location[2]))
        spoke = bpy.context.object
        spoke.name = f"{name}_spoke_{spoke_index + 1:02d}"
        spoke.scale = (0.012, 0.20, 0.016)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        spoke.rotation_euler = (angle + 0.12, math.radians(90.0), 0.0)
        spoke.location = (
            hub_x,
            location[1] + math.cos(angle) * 0.11,
            location[2] + math.sin(angle) * 0.11,
        )
        spoke.data.materials.append(bronze_mat)
        link_object(spoke, collection)

    caliper = box(
        name.replace("wheel_", "caliper_"),
        location[0] - 0.04,
        location[0] + 0.04,
        location[1] - 0.08,
        location[1] + 0.08,
        location[2] + 0.10,
        location[2] + 0.22,
        caliper_mat,
        collection,
        bevel=0.008,
    )
    return tire, rim, hub, caliper


def camera_mirror(side, carbon, bronze, emit_mat, collection):
    sign = -1.0 if side == "dside" else 1.0
    x = sign * 0.98
    y = 0.92
    z = 1.04
    stalk = box(f"mirror_{side}_stalk", x - sign * 0.01, x + sign * 0.04, y - 0.012, y + 0.012, z - 0.008, z + 0.008, carbon, collection, 0.003)
    body = box(f"mirror_{side}", x + sign * 0.03, x + sign * 0.10, y - 0.03, y + 0.03, z - 0.014, z + 0.014, carbon, collection, 0.004)
    accent = box(f"mirror_{side}_bronze", x + sign * 0.035, x + sign * 0.09, y - 0.022, y + 0.022, z - 0.018, z - 0.014, bronze, collection, 0.001)
    indicator = box(f"mirror_{side}_indicator", x + sign * 0.04, x + sign * 0.09, y + 0.028, y + 0.034, z - 0.004, z + 0.004, emit_mat, collection, 0.001)
    return body, accent, indicator


def seat(name, x, y, tan, olive, collection):
    cushion = box(f"{name}_cushion", x - 0.20, x + 0.20, y - 0.22, y + 0.22, 0.42, 0.56, tan, collection, 0.03)
    back = box(f"{name}_back", x - 0.20, x + 0.20, y + 0.16, y + 0.24, 0.54, 1.08, tan, collection, 0.025)
    bolster_l = box(f"{name}_bolster_l", x - 0.24, x - 0.17, y - 0.18, y + 0.18, 0.48, 0.78, olive, collection, 0.02)
    bolster_r = box(f"{name}_bolster_r", x + 0.17, x + 0.24, y - 0.18, y + 0.18, 0.48, 0.78, olive, collection, 0.02)
    head = box(f"{name}", x - 0.12, x + 0.12, y + 0.14, y + 0.22, 1.00, 1.16, tan, collection, 0.02)
    return cushion, back, bolster_l, bolster_r, head


def steering_wheel(bronze, olive, collection):
    bpy.ops.mesh.primitive_torus_add(
        location=(-0.38, 0.46, 1.02),
        rotation=(math.radians(72.0), 0.0, 0.0),
        major_radius=0.17,
        minor_radius=0.014,
        major_segments=36,
        minor_segments=12,
    )
    wheel = bpy.context.object
    wheel.name = "steeringwheel"
    wheel.data.materials.append(olive)
    link_object(wheel, collection)
    hub = box("steeringwheel_hub", -0.43, -0.33, 0.44, 0.50, 0.97, 1.07, bronze, collection, 0.008)
    spoke_l = box("steeringwheel_spoke_l", -0.52, -0.28, 0.45, 0.49, 1.00, 1.04, bronze, collection, 0.004)
    spoke_r = box("steeringwheel_spoke_r", -0.48, -0.28, 0.45, 0.49, 0.96, 1.00, bronze, collection, 0.004)
    return wheel, hub, spoke_l, spoke_r


def build_body(mats):
    body = make_collection("QCOMET_BODY_PANELS")
    glass = make_collection("QCOMET_GLASS")
    lights = make_collection("QCOMET_LIGHTS")
    running = make_collection("QCOMET_RUNNING_GEAR")
    interior = make_collection("QCOMET_INTERIOR")
    construction = make_collection("QCOMET_CONSTRUCTION_GUIDES")
    dimensions = make_collection("QCOMET_DIMENSION_GUIDES")

    chassis = loft_stations("chassis", STATIONS, mats["olive"], body, subsurf=True)
    cut_wheel_arches(chassis, construction)

    loft_simple("panoramic_glass_greenhouse", GREENHOUSE, 24, 5.4, mats["roof_glass"], glass)
    box("glass_windshield", -0.58, 0.58, 0.78, 1.16, 0.98, 1.32, mats["cabin_glass"], glass, 0.006)
    box("glass_rear", -0.50, 0.50, -1.42, -1.06, 0.98, 1.20, mats["cabin_glass"], glass, 0.006)
    box("glass_side_dside", -0.78, -0.70, -1.18, 0.82, 0.98, 1.32, mats["cabin_glass"], glass, 0.003)
    box("glass_side_pside", 0.70, 0.78, -1.18, 0.82, 0.98, 1.32, mats["cabin_glass"], glass, 0.003)
    box("pillar_a_dside", -0.76, -0.70, 0.84, 1.10, 0.96, 1.34, mats["blackout"], body, 0.003)
    box("pillar_a_pside", 0.70, 0.76, 0.84, 1.10, 0.96, 1.34, mats["blackout"], body, 0.003)
    box("pillar_b_dside", -0.76, -0.71, -0.18, -0.08, 0.96, 1.34, mats["blackout"], body, 0.002)
    box("pillar_b_pside", 0.71, 0.76, -0.18, -0.08, 0.96, 1.34, mats["blackout"], body, 0.002)
    box("pillar_c_dside", -0.74, -0.68, -1.32, -1.04, 0.96, 1.22, mats["blackout"], body, 0.003)
    box("pillar_c_pside", 0.68, 0.74, -1.32, -1.04, 0.96, 1.22, mats["blackout"], body, 0.003)
    box("drip_trim_dside", -0.74, -0.71, -1.28, 0.92, 1.32, 1.35, mats["bronze"], body, 0.001)
    box("drip_trim_pside", 0.71, 0.74, -1.28, 0.92, 1.32, 1.35, mats["bronze"], body, 0.001)

    panel_grid("door_dside_f", -0.16, 0.90, 0.36, 0.98, -1.0, 0.013, mats["olive"], body)
    panel_grid("door_pside_f", -0.16, 0.90, 0.36, 0.98, 1.0, 0.013, mats["olive"], body)
    panel_grid("door_dside_r", -1.26, -0.18, 0.37, 0.96, -1.0, 0.013, mats["olive"], body)
    panel_grid("door_pside_r", -1.26, -0.18, 0.37, 0.96, 1.0, 0.013, mats["olive"], body)
    for name, y in (("handle_dside_f", 0.42), ("handle_pside_f", 0.42), ("handle_dside_r", -0.62), ("handle_pside_r", -0.62)):
        sign = -1.0 if "dside" in name else 1.0
        station = station_at(y)
        x = sign * (station["hw"] + 0.012)
        box(name, x - 0.006, x + 0.006, y - 0.07, y + 0.07, 0.78, 0.81, mats["olive"], body, 0.002)

    hood_panel(mats["olive"], body)
    boot_panel(mats["olive"], body)

    box("front_bumper", -0.90, 0.90, 2.16, 2.43, 0.20, 0.54, mats["olive"], body, 0.02)
    dimple_intake(mats["olive"], body)
    box("front_splitter", -0.92, 0.92, 2.20, 2.44, 0.165, 0.236, mats["carbon"], body, 0.012)
    box("front_splitter_bronze", -0.90, 0.90, 2.22, 2.43, 0.232, 0.248, mats["bronze"], body, 0.004)
    box("rear_bumper", -0.88, 0.88, -2.43, -2.14, 0.20, 0.58, mats["olive"], body, 0.02)
    box("rear_diffuser", -0.86, 0.86, -2.44, -2.18, 0.16, 0.30, mats["carbon"], body, 0.01)
    for index, x in enumerate((-0.48, -0.16, 0.16, 0.48)):
        box(f"diffuser_fin_{index + 1}", x - 0.018, x + 0.018, -2.44, -2.22, 0.16, 0.34, mats["carbon"], body, 0.004)
    box("rear_diffuser_bronze", -0.84, 0.84, -2.42, -2.20, 0.298, 0.312, mats["bronze"], body, 0.003)
    box("reverse_dside", -0.22, -0.10, -2.40, -2.28, 0.22, 0.28, mats["reverse"], lights, 0.004)
    box("reverse_pside", 0.10, 0.22, -2.40, -2.28, 0.22, 0.28, mats["reverse"], lights, 0.004)

    box("side_skirt_l", -0.98, -0.90, -1.62, 1.52, 0.18, 0.30, mats["carbon"], body, 0.008)
    box("side_skirt_r", 0.90, 0.98, -1.62, 1.52, 0.18, 0.30, mats["carbon"], body, 0.008)
    box("side_skirt_bronze_l", -0.97, -0.91, -1.60, 1.50, 0.298, 0.312, mats["bronze"], body, 0.002)
    box("side_skirt_bronze_r", 0.91, 0.97, -1.60, 1.50, 0.298, 0.312, mats["bronze"], body, 0.002)
    box("skirt_kickup_l", -0.99, -0.90, -1.62, -1.38, 0.18, 0.38, mats["carbon"], body, 0.008)
    box("skirt_kickup_r", 0.90, 0.99, -1.62, -1.38, 0.18, 0.38, mats["carbon"], body, 0.008)

    box("fender_vent_dside", -0.99, -0.90, 1.08, 1.22, 0.58, 0.78, mats["carbon"], body, 0.004)
    box("fender_vent_pside", 0.90, 0.99, 1.08, 1.22, 0.58, 0.78, mats["carbon"], body, 0.004)
    box("fender_vent_bronze_dside", -0.995, -0.988, 1.10, 1.20, 0.66, 0.68, mats["bronze"], body, 0.001)
    box("fender_vent_bronze_pside", 0.988, 0.995, 1.10, 1.20, 0.66, 0.68, mats["bronze"], body, 0.001)

    camera_mirror("dside", mats["carbon"], mats["bronze"], mats["indicator"], body)
    camera_mirror("pside", mats["carbon"], mats["bronze"], mats["indicator"], body)

    q_plus_badge("badge_front", (0.0, 2.36, 0.62), 1.0, mats["bronze"], body)
    q_plus_badge("badge_rear", (0.0, -2.28, 0.66), -1.0, mats["bronze"], body)

    headlight_blades("dside", mats["headlight"], mats["lens"], lights)
    headlight_blades("pside", mats["headlight"], mats["lens"], lights)
    front_drl("dside", mats["headlight"], lights)
    front_drl("pside", mats["headlight"], lights)
    rear_light_bar(mats["tail"], mats["brake"], mats["lens"], lights)

    for name, location in WHEEL_LOCATIONS.items():
        make_wheel(name, location, mats["tire"], mats["rim"], mats["bronze"], mats["caliper"], mats["tire"], running)

    box("underbody_skate", -0.78, 0.78, -1.70, 1.70, 0.10, 0.18, mats["carbon"], body, 0.02)

    box("dash_glass_bar", -0.72, 0.72, 0.48, 0.62, 0.92, 1.02, mats["screen"], interior, 0.004)
    box("dash_ambient_strip", -0.70, 0.70, 0.50, 0.58, 0.88, 0.90, mats["ambient"], interior, 0.002)
    box("center_console", -0.16, 0.16, -0.55, 0.48, 0.42, 0.70, mats["olive_int"], interior, 0.012)
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.045, depth=0.02, location=(0.0, 0.22, 0.71))
    rotary = bpy.context.object
    rotary.name = "console_rotary"
    rotary.data.materials.append(mats["bronze"])
    link_object(rotary, interior)
    box("cupholder_l", -0.10, -0.02, 0.02, 0.10, 0.68, 0.71, mats["screen"], interior, 0.004)
    box("cupholder_r", 0.02, 0.10, 0.02, 0.10, 0.68, 0.71, mats["screen"], interior, 0.004)
    box("armrest", -0.14, 0.14, -0.52, -0.10, 0.68, 0.74, mats["olive_int"], interior, 0.01)
    box("pedal_brake", -0.46, -0.34, 0.62, 0.70, 0.28, 0.40, mats["bronze"], interior, 0.004)
    box("pedal_accel", -0.30, -0.18, 0.62, 0.70, 0.28, 0.40, mats["bronze"], interior, 0.004)
    box("door_card_dside_f", -0.94, -0.86, -0.10, 0.82, 0.42, 0.86, mats["tan"], interior, 0.01)
    box("door_card_pside_f", 0.86, 0.94, -0.10, 0.82, 0.42, 0.86, mats["tan"], interior, 0.01)
    box("door_card_dside_r", -0.93, -0.85, -1.18, -0.22, 0.42, 0.84, mats["tan"], interior, 0.01)
    box("door_card_pside_r", 0.85, 0.93, -1.18, -0.22, 0.42, 0.84, mats["tan"], interior, 0.01)

    seat("seat_dside_f", -0.38, 0.12, mats["tan"], mats["olive_int"], interior)
    seat("seat_pside_f", 0.38, 0.12, mats["tan"], mats["olive_int"], interior)
    seat("seat_dside_r", -0.38, -0.78, mats["tan"], mats["olive_int"], interior)
    seat("seat_pside_r", 0.38, -0.78, mats["tan"], mats["olive_int"], interior)
    steering_wheel(mats["bronze"], mats["olive_int"], interior)

    empty("PIVOT_door_dside_f", (-0.97, 0.90, 0.67), dimensions)
    empty("PIVOT_door_pside_f", (0.97, 0.90, 0.67), dimensions)
    empty("PIVOT_door_dside_r", (-0.96, -0.18, 0.67), dimensions)
    empty("PIVOT_door_pside_r", (0.96, -0.18, 0.67), dimensions)
    empty("PIVOT_bonnet", (0.0, 1.14, 0.98), dimensions)
    empty("PIVOT_boot", (0.0, -1.38, 0.94), dimensions)
    for name, location in {
        "GUIDE_front_extent": (0.0, 2.43, 0.0),
        "GUIDE_rear_extent": (0.0, -2.43, 0.0),
        "GUIDE_passenger_extent": (0.97, 0.0, 0.0),
        "GUIDE_driver_extent": (-0.97, 0.0, 0.0),
        "GUIDE_roof_extent": (0.0, 0.0, 1.44),
        "GUIDE_ground_clearance": (0.0, 0.0, 0.13),
    }.items():
        empty(name, location, dimensions)

    set_active(chassis)
    return chassis


def make_materials():
    return {
        "olive": principled_material("M_QCOMET_OLIVE_BODY", (0.38, 0.40, 0.22), metallic=0.22, roughness=0.38, coat=0.12),
        "bronze": principled_material("M_QCOMET_BRONZE", (0.42, 0.22, 0.08), metallic=0.85, roughness=0.28),
        "carbon": principled_material("M_QCOMET_CARBON", (0.02, 0.022, 0.02), metallic=0.18, roughness=0.22, coat=0.55),
        "blackout": principled_material("M_QCOMET_BLACKOUT", (0.012, 0.012, 0.012), metallic=0.05, roughness=0.18, coat=0.4),
        "cabin_glass": principled_material("M_QCOMET_GLASS_CABIN", (0.08, 0.12, 0.14), roughness=0.04, transmission=0.88, alpha=0.22),
        "roof_glass": principled_material("M_QCOMET_GLASS_ROOF", (0.03, 0.04, 0.05), roughness=0.05, transmission=0.62, alpha=0.38),
        "lens": principled_material("M_QCOMET_LENS_SMOKE", (0.04, 0.04, 0.05), roughness=0.08, transmission=0.55, alpha=0.35),
        "tire": principled_material("M_QCOMET_TIRE", (0.02, 0.02, 0.02), roughness=0.78),
        "rim": principled_material("M_QCOMET_RIM_DARK", (0.04, 0.04, 0.045), metallic=0.7, roughness=0.32),
        "caliper": principled_material("M_QCOMET_CALIPER", (0.40, 0.20, 0.07), metallic=0.8, roughness=0.3),
        "headlight": principled_material("M_QCOMET_HEADLIGHT", (0.9, 0.92, 0.85), roughness=0.18, emission=((0.95, 0.96, 0.88), 12.0)),
        "tail": principled_material("M_QCOMET_TAIL", (0.55, 0.04, 0.04), roughness=0.22, emission=((0.85, 0.05, 0.04), 8.0)),
        "brake": principled_material("M_QCOMET_BRAKE", (0.7, 0.05, 0.05), roughness=0.2, emission=((1.0, 0.08, 0.06), 16.0)),
        "reverse": principled_material("M_QCOMET_REVERSE", (0.85, 0.85, 0.82), roughness=0.2, emission=((0.9, 0.9, 0.88), 6.0)),
        "indicator": principled_material("M_QCOMET_INDICATOR", (0.85, 0.45, 0.08), roughness=0.22, emission=((1.0, 0.5, 0.08), 6.0)),
        "tan": principled_material("M_QCOMET_TAN_LEATHER", (0.55, 0.42, 0.28), roughness=0.48),
        "olive_int": principled_material("M_QCOMET_OLIVE_LEATHER", (0.18, 0.20, 0.12), roughness=0.5),
        "screen": principled_material("M_QCOMET_SCREEN", (0.01, 0.012, 0.015), roughness=0.08, metallic=0.2),
        "ambient": principled_material("M_QCOMET_AMBIENT", (0.7, 0.45, 0.2), roughness=0.3, emission=((0.85, 0.5, 0.2), 3.0)),
    }


def configure_scene(scene):
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "METERS"
    scene.unit_settings.scale_length = 1.0
    scene["qcomet_status"] = "BODY_SURFACING_V004"
    scene["qcomet_dimensions_note"] = "Provisional envelope retained from v002; awaiting owner dimension sheet"
    scene["qcomet_front_axis"] = "+Y"
    scene["qcomet_passenger_axis"] = "+X"
    scene["qcomet_source_blockout"] = "qcomet_blockout_v002.blend"
    for key, value in ENVELOPE.items():
        scene[f"qcomet_{key}"] = value


def point_camera(camera, location, target):
    camera.location = Vector(location)
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()


def render_review_views(scene, review_dir):
    os.makedirs(review_dir, exist_ok=True)
    engine_ids = [item.identifier for item in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
    if "BLENDER_EEVEE_NEXT" in engine_ids:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    elif "BLENDER_EEVEE" in engine_ids:
        scene.render.engine = "BLENDER_EEVEE"
    else:
        scene.render.engine = "BLENDER_WORKBENCH"
    if hasattr(scene, "eevee") and hasattr(scene.eevee, "use_raytracing"):
        scene.eevee.use_raytracing = True
    scene.render.resolution_x = 1100
    scene.render.resolution_y = 780
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    world = bpy.data.worlds.new("QCOMET_REVIEW_WORLD")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = (0.42, 0.44, 0.46, 1.0)
        bg.inputs[1].default_value = 2.4
    sun_data = bpy.data.lights.new("QCOMET_REVIEW_SUN", type="SUN")
    sun_data.energy = 6.0
    sun_data.angle = 0.12
    sun = bpy.data.objects.new("QCOMET_REVIEW_SUN", sun_data)
    sun.location = (4.5, 6.5, 8.0)
    sun.rotation_euler = (math.radians(42.0), math.radians(12.0), math.radians(28.0))
    scene.collection.objects.link(sun)

    camera_data = bpy.data.cameras.new("QCOMET_REVIEW_CAMERA")
    camera = bpy.data.objects.new("QCOMET_REVIEW_CAMERA", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera

    target = (0.0, 0.0, 0.70)
    views = (
        ("front", "FRONT", (0.0, 8.2, 0.72), "ORTHO", 1.95),
        ("side", "SIDE", (8.2, 0.0, 0.72), "ORTHO", 4.35),
        ("top", "TOP", (0.0, 0.0, 8.2), "ORTHO", 5.5),
        ("front_three_quarter", "FRONT THREE-QUARTER", (5.6, 7.6, 3.6), "PERSP", None),
        ("rear_three_quarter", "REAR THREE-QUARTER", (5.4, -7.4, 3.4), "PERSP", None),
    )
    paths = []
    scene.render.use_stamp = True
    scene.render.use_stamp_note = True
    scene.render.use_stamp_date = False
    scene.render.use_stamp_time = False
    scene.render.use_stamp_render_time = False
    scene.render.use_stamp_frame = False
    scene.render.stamp_font_size = 26
    scene.render.stamp_note_text = ""
    for filename, label, location, camera_type, ortho_scale in views:
        camera.data.type = camera_type
        if camera_type == "ORTHO":
            camera.data.ortho_scale = ortho_scale
        else:
            camera.data.lens = 50
        point_camera(camera, location, target)
        scene.render.stamp_note_text = f"Q COMET BODY V004 / {label}"
        path = os.path.join(review_dir, f"qcomet_body_v004_{filename}.png")
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        paths.append(path)
        print(f"Rendered review view: {path}")

    loaded = [bpy.data.images.load(path, check_existing=False) for path in paths[:4]]
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
    sheet = bpy.data.images.new("QCOMET_V004_CONTACT_SHEET", width=width * 2, height=height * 2, alpha=True)
    sheet.pixels.foreach_set(canvas.ravel())
    sheet.file_format = "PNG"
    sheet.filepath_raw = os.path.join(review_dir, "qcomet_body_v004_contact_sheet.png")
    sheet.save()
    print(f"Rendered contact sheet: {sheet.filepath_raw}")


def add_image_empty(name, path, location, rotation, display_size, collection):
    image = bpy.data.images.load(path, check_existing=True)
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_type = "IMAGE"
    obj.data = image
    obj.location = location
    obj.rotation_euler = rotation
    obj.empty_display_size = display_size
    obj.hide_render = True
    collection.objects.link(obj)
    return obj


def setup_reference_images():
    """Place the owner's concept photos as tracing planes. Not game geometry."""
    collection = make_collection("QCOMET_CONCEPT_REFERENCES")
    collection.hide_render = True
    ortho_dir = os.path.join(PROJECT_ROOT, "vehicles", "qcomet", "source", "concepts", "orthos")
    concepts = os.path.join(PROJECT_ROOT, "vehicles", "qcomet", "source", "concepts")
    front = os.path.join(ortho_dir, "qcomet_ref_front.png")
    rear = os.path.join(ortho_dir, "qcomet_ref_rear.png")
    left = os.path.join(ortho_dir, "qcomet_ref_left.png")
    right = os.path.join(ortho_dir, "qcomet_ref_right.png")
    showroom = os.path.join(concepts, "Q Comet Front view showroom.png")
    lights = os.path.join(concepts, "q comet wheel headlight tail light on and off.png")
    if os.path.isfile(front):
        add_image_empty("REFIMG_front", front, (0.0, 2.62, 0.72), (math.radians(90.0), 0.0, math.radians(180.0)), 1.94, collection)
    if os.path.isfile(rear):
        add_image_empty("REFIMG_rear", rear, (0.0, -2.62, 0.72), (math.radians(90.0), 0.0, 0.0), 1.94, collection)
    if os.path.isfile(left):
        add_image_empty("REFIMG_left", left, (-1.12, 0.0, 0.72), (math.radians(90.0), 0.0, math.radians(90.0)), 4.86, collection)
    if os.path.isfile(right):
        add_image_empty("REFIMG_right", right, (1.12, 0.0, 0.72), (math.radians(90.0), 0.0, math.radians(-90.0)), 4.86, collection)
    if os.path.isfile(showroom):
        add_image_empty("REFIMG_showroom", showroom, (4.2, 5.4, 2.2), (math.radians(72.0), 0.0, math.radians(35.0)), 3.4, collection)
    if os.path.isfile(lights):
        add_image_empty("REFIMG_lights", lights, (-4.4, 5.0, 2.0), (math.radians(72.0), 0.0, math.radians(-35.0)), 3.2, collection)
    print(f"Concept reference planes: {len(collection.objects)}")


def main():
    output_path = cli_value("--output", DEFAULT_OUTPUT)
    review_dir = cli_value("--review-dir", DEFAULT_REVIEW)
    load_v002()
    archive_blockout()
    scene = bpy.context.scene
    configure_scene(scene)
    setup_reference_images()
    mats = make_materials()
    build_body(mats)
    report_sollumz()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=output_path)
    print(f"Saved Q Comet body v004: {output_path}")
    render_review_views(scene, review_dir)
    bpy.ops.wm.save_mainfile()
    print("QCOMET_BODY_V004_OK")


if __name__ == "__main__":
    main()
