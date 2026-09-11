"""
Complete M1 gaps + M2 + M3 on the live cabin-refined scene.
Preserves existing high-detail cabin meshes; does not rebuild seats/dash.
Saves as qcomet_vehicle_v013.blend.
"""
from __future__ import annotations

import json
import math
import os
import traceback

import bpy
from mathutils import Matrix, Vector

ROOT = r"C:\Users\Qanva\Desktop\Gaming GTA\Q-Motors-Q-Comet"
BLEND_OUT = os.path.join(ROOT, "vehicles", "qcomet", "source", "blender", "qcomet_vehicle_v013.blend")
REVIEW_DIR = os.path.join(ROOT, "vehicles", "qcomet", "source", "blender", "review_v013")
REPORT_PATH = os.path.join(REVIEW_DIR, "milestone123_completion_report.json")
DRIVER_EYE = Vector((-0.38, 0.05, 1.20))

LOG = []


def log(msg):
    LOG.append(str(msg))
    print(msg)


def ensure_collection(name):
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(col)
    return col


def link_object(obj, collection):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    if obj.name not in collection.objects:
        collection.objects.link(obj)


def parent_keep_world(child, parent):
    if child is None or parent is None or child == parent:
        return
    mw = child.matrix_world.copy()
    child.parent = parent
    child.matrix_parent_inverse = parent.matrix_world.inverted()
    child.matrix_world = mw


def set_origin_world(obj, world_location):
    if obj is None:
        return
    if obj.type != "MESH" or obj.data is None:
        obj.matrix_world.translation = Vector(world_location)
        return
    mw = obj.matrix_world.copy()
    local = mw.inverted() @ Vector(world_location)
    obj.data.transform(Matrix.Translation(-local))
    obj.matrix_world.translation = Vector(world_location)
    obj.data.update()


def safe_rename(obj, new_name):
    if obj is None:
        return None
    existing = bpy.data.objects.get(new_name)
    if existing is not None and existing != obj:
        existing.name = f"{new_name}__dup"
    obj.name = new_name
    return obj


def make_empty(name, location, collection, size=0.08):
    obj = bpy.data.objects.get(name)
    if obj is None:
        obj = bpy.data.objects.new(name, None)
        link_object(obj, collection)
    obj.empty_display_type = "PLAIN_AXES"
    obj.empty_display_size = size
    obj.location = Vector(location)
    return obj


def get_mat(name, color, metallic=0.0, roughness=0.5, emission=None, transmission=0.0, alpha=1.0):
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = None
    for n in nt.nodes:
        if n.type == "BSDF_PRINCIPLED":
            bsdf = n
            break
    if bsdf is None:
        for n in list(nt.nodes):
            nt.nodes.remove(n)
        out = nt.nodes.new("ShaderNodeOutputMaterial")
        bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
        nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    if emission is not None:
        if "Emission Color" in bsdf.inputs:
            bsdf.inputs["Emission Color"].default_value = (*emission[0], 1.0)
            bsdf.inputs["Emission Strength"].default_value = emission[1]
    if transmission > 0:
        key = "Transmission Weight" if "Transmission Weight" in bsdf.inputs else "Transmission"
        if key in bsdf.inputs:
            bsdf.inputs[key].default_value = transmission
    if alpha < 1.0 and "Alpha" in bsdf.inputs:
        bsdf.inputs["Alpha"].default_value = alpha
        mat.blend_method = "BLEND"
    if emission is not None:
        mat["qcomet_shader_hint"] = "vehicle_lightsemissive"
    elif transmission > 0.2:
        mat["qcomet_shader_hint"] = "vehicle_vehglass"
    else:
        mat["qcomet_shader_hint"] = "vehicle_mesh"
    return mat


def box_mesh(name, x0, x1, y0, y1, z0, z1, mat, collection):
    obj = bpy.data.objects.get(name)
    if obj is not None:
        mesh = obj.data if obj.type == "MESH" else None
        bpy.data.objects.remove(obj, do_unlink=True)
        if mesh and mesh.users == 0:
            bpy.data.meshes.remove(mesh)
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=((x0 + x1) * 0.5, (y0 + y1) * 0.5, (z0 + z1) * 0.5))
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = (x1 - x0, y1 - y0, z1 - z0)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.clear()
    obj.data.materials.append(mat)
    link_object(obj, collection)
    return obj


def milestone1_finish(interior):
    log("M1 finish naming/parenting")
    # Cupholders rename
    for old, new in (("cupholder_1", "cupholder_l"), ("cupholder_2", "cupholder_r")):
        o = bpy.data.objects.get(old) or bpy.data.objects.get(new)
        if o:
            safe_rename(o, new)

    # Steering alias + parenting
    steering = bpy.data.objects.get("steering")
    if steering:
        alias = make_empty("steeringwheel", steering.matrix_world.translation, interior, 0.06)
        parent_keep_world(alias, steering)
        for n in ("steering_qplus", "steering_column", "steering_hub", "steering_spoke_l", "steering_spoke_r"):
            c = bpy.data.objects.get(n)
            if c:
                parent_keep_world(c, steering)
        steering["qcomet_role"] = "steering"

    # Parent console hardware
    console = bpy.data.objects.get("center_console")
    if console:
        for n in ("armrest", "cupholder_l", "cupholder_r", "console_rotary"):
            c = bpy.data.objects.get(n)
            if c:
                parent_keep_world(c, console)

    # Parent dash instruments under glass bar
    dash = bpy.data.objects.get("dash_glass_bar")
    if dash:
        for n in (
            "dash_ambient_strip",
            "dash_battery",
            "dash_speed",
            "dash_speed_units",
            "dash_passenger_qplus",
            "dash_touch_icon_1",
            "dash_touch_icon_2",
            "dash_touch_icon_3",
            "dash_touch_icon_4",
            "dash_touch_label_1",
            "dash_touch_label_2",
            "dash_touch_label_3",
            "dash_touch_label_4",
            "dash_lower_shell",
            "dash_cluster",
            "dash_qplus_badge",
        ):
            c = bpy.data.objects.get(n)
            if c:
                parent_keep_world(c, dash)

    # Ensure required materials exist
    get_mat("M_QCOMET_TAN_LEATHER", (0.62, 0.48, 0.34), roughness=0.55)
    get_mat("M_QCOMET_OLIVE_LEATHER", (0.28, 0.32, 0.18), roughness=0.5)
    get_mat("M_QCOMET_SCREEN", (0.02, 0.02, 0.025), metallic=0.4, roughness=0.12, emission=((0.05, 0.08, 0.12), 0.35))
    get_mat("M_QCOMET_AMBIENT", (0.55, 0.32, 0.12), roughness=0.4, emission=((1.0, 0.55, 0.25), 2.5))
    get_mat("M_QCOMET_BRONZE", (0.42, 0.22, 0.08), metallic=0.85, roughness=0.28)

    for seat in ("seat_dside_f", "seat_pside_f", "seat_dside_r", "seat_pside_r"):
        o = bpy.data.objects.get(seat)
        if o:
            o["qcomet_role"] = "seat"

    return {
        "cupholders": [n for n in ("cupholder_l", "cupholder_r") if bpy.data.objects.get(n)],
        "steering": steering.name if steering else None,
        "steeringwheel_alias": bpy.data.objects.get("steeringwheel") is not None,
        "seats": [n for n in ("seat_dside_f", "seat_pside_f", "seat_dside_r", "seat_pside_r") if bpy.data.objects.get(n)],
    }


def milestone2():
    log("M2 hinge origins + door parenting")
    panels = ["door_dside_f", "door_pside_f", "door_dside_r", "door_pside_r", "bonnet", "boot"]
    pivot_report = {}
    for panel in panels:
        obj = bpy.data.objects.get(panel)
        pe = bpy.data.objects.get(f"PIVOT_{panel}")
        if obj is None or pe is None:
            pivot_report[panel] = {"ok": False, "reason": "missing"}
            continue
        pivot = pe.matrix_world.translation.copy()
        v0_before = None
        if obj.type == "MESH" and len(obj.data.vertices):
            v0_before = (obj.matrix_world @ obj.data.vertices[0].co).copy()
        # Temporarily clear children parenting? Keep children — set_origin only transforms mesh data
        set_origin_world(obj, pivot)
        delta = None
        if v0_before is not None:
            delta = (obj.matrix_world @ obj.data.vertices[0].co - v0_before).length
        origin_delta = (obj.matrix_world.translation - pivot).length
        pivot_report[panel] = {
            "ok": origin_delta < 1e-4 and (delta is None or delta < 1e-3),
            "origin_delta": round(origin_delta, 8),
            "vertex0_delta": None if delta is None else round(delta, 8),
            "pivot": [round(v, 4) for v in pivot],
        }

    mapping = {
        "door_dside_f": [
            "door_card_dside_f",
            "mirror_dside",
            "mirror_dside_stalk",
            "mirror_dside_bronze",
            "mirror_dside_camera_lens",
            "mirror_dside_indicator",
            "glass_dside_f",
            "window_lf",
            "handle_dside_f",
        ],
        "door_pside_f": [
            "door_card_pside_f",
            "mirror_pside",
            "mirror_pside_stalk",
            "mirror_pside_bronze",
            "mirror_pside_camera_lens",
            "mirror_pside_indicator",
            "glass_pside_f",
            "window_rf",
            "handle_pside_f",
        ],
        "door_dside_r": ["door_card_dside_r", "glass_dside_r", "window_lr", "handle_dside_r"],
        "door_pside_r": ["door_card_pside_r", "glass_pside_r", "window_rr", "handle_pside_r"],
    }
    parent_report = {}
    for door_name, children in mapping.items():
        door = bpy.data.objects.get(door_name)
        attached = []
        if door is None:
            parent_report[door_name] = {"ok": False, "attached": []}
            continue
        for cname in children:
            child = bpy.data.objects.get(cname)
            if child is None:
                continue
            parent_keep_world(child, door)
            attached.append(cname)
        parent_report[door_name] = {"ok": True, "attached": attached}

    # Hinge clearance tests
    tests = {}
    rotations = {
        "door_dside_f": (0, 0, math.radians(55)),
        "door_pside_f": (0, 0, math.radians(-55)),
        "door_dside_r": (0, 0, math.radians(55)),
        "door_pside_r": (0, 0, math.radians(-55)),
        "bonnet": (math.radians(-50), 0, 0),
        "boot": (math.radians(55), 0, 0),
    }
    for name, rot in rotations.items():
        obj = bpy.data.objects.get(name)
        if obj is None:
            continue
        base = obj.rotation_euler.copy()
        obj.rotation_euler = rot
        bpy.context.view_layer.update()
        bb = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
        mn = Vector((min(v.x for v in bb), min(v.y for v in bb), min(v.z for v in bb)))
        mx = Vector((max(v.x for v in bb), max(v.y for v in bb), max(v.z for v in bb)))
        ok = True
        if "dside" in name:
            ok = mn.x < -0.85
        elif "pside" in name:
            ok = mx.x > 0.85
        elif name == "bonnet":
            ok = mx.z > 1.05
        elif name == "boot":
            ok = mx.z > 1.0
        tests[name] = {
            "rotation_deg": [round(math.degrees(r), 1) for r in rot],
            "bbox_min": [round(v, 3) for v in mn],
            "bbox_max": [round(v, 3) for v in mx],
            "clearance_proxy_ok": ok,
        }
        obj.rotation_euler = base
    bpy.context.view_layer.update()
    return pivot_report, parent_report, tests


def milestone3(body_col, mats):
    log("M3 hierarchy / lights / collision")
    chassis = bpy.data.objects.get("chassis")
    if chassis is None:
        chassis = make_empty("chassis", (0, 0, 0.2), body_col, 0.2)
    bodyshell = make_empty("bodyshell", (0, 0, 0.55), body_col, 0.18)
    parent_keep_world(bodyshell, chassis)

    fixed = [
        "front_bumper",
        "rear_bumper",
        "front_splitter",
        "rear_diffuser",
        "skirt_dside",
        "skirt_pside",
        "underbody_skate",
        "panoramic_glass_greenhouse",
        "windscreen",
        "glass_rear",
    ]
    body_attached = []
    for name in fixed:
        obj = bpy.data.objects.get(name)
        if obj:
            parent_keep_world(obj, bodyshell)
            body_attached.append(name)

    glass_report = {}
    for old, new in (
        ("glass_dside_f", "window_lf"),
        ("glass_pside_f", "window_rf"),
        ("glass_dside_r", "window_lr"),
        ("glass_pside_r", "window_rr"),
    ):
        obj = bpy.data.objects.get(old) or bpy.data.objects.get(new)
        if obj:
            safe_rename(obj, new)
            for slot in obj.material_slots:
                if slot.material:
                    slot.material["qcomet_shader_hint"] = "vehicle_vehglass"
            glass_report[new] = True
        else:
            glass_report[new] = False

    # Re-parent windows to doors after rename
    for door, win in (
        ("door_dside_f", "window_lf"),
        ("door_pside_f", "window_rf"),
        ("door_dside_r", "window_lr"),
        ("door_pside_r", "window_rr"),
    ):
        d = bpy.data.objects.get(door)
        w = bpy.data.objects.get(win)
        if d and w:
            parent_keep_world(w, d)

    lights_col = ensure_collection("QCOMET_LIGHTS_GTA")

    def group(name, location, light_id, children):
        root = make_empty(name, location, lights_col, 0.1)
        root["LightId"] = int(light_id)
        root["qcomet_role"] = "light"
        root["qcomet_shader_hint"] = "vehicle_lightsemissive"
        attached = []
        for cname in children:
            child = bpy.data.objects.get(cname)
            if child is None:
                continue
            parent_keep_world(child, root)
            for slot in getattr(child, "material_slots", []):
                if slot.material:
                    slot.material["qcomet_shader_hint"] = "vehicle_lightsemissive"
            attached.append(cname)
        return {"light_id": light_id, "attached": attached}

    lights = {
        "headlight_l": group(
            "headlight_l",
            (-0.65, 2.05, 0.75),
            0,
            [
                "headlight_dside_housing",
                "headlight_dside_blade_1",
                "headlight_dside_blade_2",
                "headlight_dside_blade_3",
                "drl_dside",
            ],
        ),
        "headlight_r": group(
            "headlight_r",
            (0.65, 2.05, 0.75),
            1,
            [
                "headlight_pside_housing",
                "headlight_pside_blade_1",
                "headlight_pside_blade_2",
                "headlight_pside_blade_3",
                "drl_pside",
            ],
        ),
        "taillight_l": group("taillight_l", (-0.55, -2.28, 0.87), 2, ["tail_bar_brake"]),
        "taillight_r": group("taillight_r", (0.55, -2.28, 0.87), 3, []),
        "brakelight_l": group("brakelight_l", (-0.45, -2.28, 0.87), 2, []),
        "brakelight_r": group("brakelight_r", (0.45, -2.28, 0.87), 3, []),
        "brakelight_m": group("brakelight_m", (0.0, -2.28, 0.87), -1, []),
        "indicator_lf": group("indicator_lf", (-0.9, 2.1, 0.7), -1, ["mirror_dside_indicator"]),
        "indicator_rf": group("indicator_rf", (0.9, 2.1, 0.7), -1, ["mirror_pside_indicator"]),
        "indicator_lr": group("indicator_lr", (-0.7, -2.28, 0.87), -1, []),
        "indicator_rr": group("indicator_rr", (0.7, -2.28, 0.87), -1, []),
        "reversinglight_l": group(
            "reversinglight_l", (-0.13, -2.34, 0.24), -1, ["reverse_dside", "reverse_dside_housing"]
        ),
        "reversinglight_r": group(
            "reversinglight_r", (0.13, -2.34, 0.24), -1, ["reverse_pside", "reverse_pside_housing"]
        ),
    }

    wheels = {}
    for name in ("wheel_lf", "wheel_rf", "wheel_lr", "wheel_rr"):
        obj = bpy.data.objects.get(name)
        if obj:
            obj["sollumz_is_wheel_mesh"] = True
            obj["qcomet_role"] = "wheel"
            # Ensure origin at geometric center if far from bbox center
            bb = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
            ctr = sum(bb, Vector()) / 8.0
            if (obj.matrix_world.translation - ctr).length > 0.05:
                set_origin_world(obj, ctr)
            wheels[name] = {"ok": True, "center": [round(v, 4) for v in obj.matrix_world.translation]}
        else:
            wheels[name] = {"ok": False}

    col_mat = mats["col"]
    col = ensure_collection("QCOMET_COLLISION")
    specs = {
        "col_chassis": (-0.90, 0.90, -2.20, 2.20, 0.12, 0.55),
        "col_greenhouse": (-0.78, 0.78, -1.10, 0.95, 0.95, 1.42),
        "col_roof": (-0.72, 0.72, -0.85, 0.25, 1.34, 1.45),
        "col_bumper_f": (-0.92, 0.92, 2.05, 2.43, 0.16, 0.55),
        "col_bumper_r": (-0.90, 0.90, -2.43, -2.05, 0.16, 0.58),
        "col_door_dside_f": (-1.00, -0.84, -0.13, 0.95, 0.28, 1.05),
        "col_door_pside_f": (0.84, 1.00, -0.13, 0.95, 0.28, 1.05),
        "col_door_dside_r": (-1.00, -0.84, -1.25, -0.18, 0.28, 1.02),
        "col_door_pside_r": (0.84, 1.00, -1.25, -0.18, 0.28, 1.02),
        "col_bonnet": (-0.72, 0.72, 1.10, 2.22, 0.78, 1.06),
        "col_boot": (-0.74, 0.74, -2.30, -1.38, 0.85, 1.06),
    }
    created_cols = []
    for name, dims in specs.items():
        obj = box_mesh(name, *dims, col_mat, col)
        obj.display_type = "WIRE"
        obj.hide_render = True
        obj["qcomet_role"] = "collision"
        obj["qcomet_bound"] = "composite"
        created_cols.append(name)

    for panel, coln in (
        ("door_dside_f", "col_door_dside_f"),
        ("door_pside_f", "col_door_pside_f"),
        ("door_dside_r", "col_door_dside_r"),
        ("door_pside_r", "col_door_pside_r"),
        ("bonnet", "col_bonnet"),
        ("boot", "col_boot"),
    ):
        p = bpy.data.objects.get(panel)
        c = bpy.data.objects.get(coln)
        if p and c:
            parent_keep_world(c, p)

    core_children = [
        "bodyshell",
        "bonnet",
        "boot",
        "door_dside_f",
        "door_pside_f",
        "door_dside_r",
        "door_pside_r",
        "wheel_lf",
        "wheel_rf",
        "wheel_lr",
        "wheel_rr",
        "steering",
        "seat_dside_f",
        "seat_pside_f",
        "seat_dside_r",
        "seat_pside_r",
        "dash_glass_bar",
        "center_console",
        "pedal_brake",
        "pedal_accel",
        "headlight_l",
        "headlight_r",
        "taillight_l",
        "taillight_r",
        "brakelight_l",
        "brakelight_r",
        "brakelight_m",
        "indicator_lf",
        "indicator_rf",
        "indicator_lr",
        "indicator_rr",
        "reversinglight_l",
        "reversinglight_r",
        "col_chassis",
        "col_greenhouse",
        "col_roof",
        "col_bumper_f",
        "col_bumper_r",
    ]
    core = []
    for name in core_children:
        obj = bpy.data.objects.get(name)
        if obj:
            parent_keep_world(obj, chassis)
            core.append(name)

    return {
        "bodyshell_children": body_attached,
        "glass_windows": glass_report,
        "lights": lights,
        "wheels": wheels,
        "collision": created_cols,
        "chassis_children": core,
    }


def hierarchy_tree(obj, depth=0, max_depth=5):
    node = {"name": obj.name, "type": obj.type, "children": []}
    if obj.type == "MESH" and obj.data:
        node["verts"] = len(obj.data.vertices)
        node["faces"] = len(obj.data.polygons)
    if depth < max_depth:
        for child in sorted(obj.children, key=lambda o: o.name):
            node["children"].append(hierarchy_tree(child, depth + 1, max_depth))
    return node


def mesh_stats():
    total_v = total_f = 0
    objects = 0
    notable = {}
    for obj in bpy.data.objects:
        if obj.type != "MESH" or not obj.data:
            continue
        if obj.name.startswith(("v010_", "v011_", "v013_cabin_archive", "REF", "GUIDE")):
            continue
        v = len(obj.data.vertices)
        f = len(obj.data.polygons)
        total_v += v
        total_f += f
        objects += 1
        if obj.name in (
            "seat_dside_f",
            "steering",
            "door_dside_f",
            "bonnet",
            "boot",
            "dash_glass_bar",
            "wheel_lf",
            "windscreen",
            "window_lf",
        ):
            notable[obj.name] = {"verts": v, "faces": f}
    return {"objects": objects, "total_verts": total_v, "total_faces": total_f, "notable": notable}


def setup_cam():
    cam = bpy.data.objects.get("QCOMET_REVIEW_CAMERA")
    if cam is None:
        bpy.ops.object.camera_add()
        cam = bpy.context.active_object
        cam.name = "QCOMET_REVIEW_CAMERA"
    if bpy.data.objects.get("QCOMET_REVIEW_SUN") is None:
        bpy.ops.object.light_add(type="SUN", location=(4, -2, 6))
        sun = bpy.context.active_object
        sun.name = "QCOMET_REVIEW_SUN"
        sun.data.energy = 3.5
    bpy.context.scene.camera = cam
    return cam


def look_at(cam, eye, target):
    cam.location = Vector(eye)
    direction = Vector(target) - Vector(eye)
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def render_views():
    os.makedirs(REVIEW_DIR, exist_ok=True)
    scene = bpy.context.scene
    engines = [e.identifier for e in scene.render.bl_rna.properties["engine"].enum_items]
    if "BLENDER_EEVEE_NEXT" in engines:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    elif "BLENDER_EEVEE" in engines:
        scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1600
    scene.render.resolution_y = 900
    scene.render.image_settings.file_format = "PNG"
    cam = setup_cam()
    door_rots = {}
    for name in ("door_dside_f", "door_pside_f", "door_dside_r", "door_pside_r"):
        obj = bpy.data.objects.get(name)
        if obj:
            door_rots[name] = obj.rotation_euler.copy()

    outputs = {}

    # cockpit — doors closed
    for name, base in door_rots.items():
        bpy.data.objects[name].rotation_euler = base
    bpy.context.view_layer.update()
    look_at(cam, DRIVER_EYE + Vector((0.05, 0.15, 0.02)), Vector((0.0, 0.85, 0.95)))
    path = os.path.join(REVIEW_DIR, "interior_cockpit.png")
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    outputs["interior_cockpit"] = path if os.path.isfile(path) else None

    # open doors
    for name, z in (("door_dside_f", 55), ("door_pside_f", -55), ("door_dside_r", 50), ("door_pside_r", -50)):
        obj = bpy.data.objects.get(name)
        if obj:
            obj.rotation_euler = (0, 0, math.radians(z))
    bpy.context.view_layer.update()
    look_at(cam, Vector((-3.2, 1.4, 1.5)), Vector((0.0, 0.2, 0.7)))
    path = os.path.join(REVIEW_DIR, "open_doors.png")
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    outputs["open_doors"] = path if os.path.isfile(path) else None

    # exterior
    for name, base in door_rots.items():
        bpy.data.objects[name].rotation_euler = base
    bpy.context.view_layer.update()
    look_at(cam, Vector((-3.6, -3.2, 1.6)), Vector((0.0, 0.1, 0.7)))
    path = os.path.join(REVIEW_DIR, "exterior_34.png")
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    outputs["exterior_34"] = path if os.path.isfile(path) else None
    return outputs


def verify():
    required = [
        "chassis",
        "bodyshell",
        "bonnet",
        "boot",
        "door_dside_f",
        "door_pside_f",
        "door_dside_r",
        "door_pside_r",
        "wheel_lf",
        "wheel_rf",
        "wheel_lr",
        "wheel_rr",
        "steering",
        "windscreen",
        "window_lf",
        "window_rf",
        "window_lr",
        "window_rr",
        "seat_dside_f",
        "seat_pside_f",
        "seat_dside_r",
        "seat_pside_r",
        "dash_glass_bar",
        "dash_ambient_strip",
        "center_console",
        "armrest",
        "cupholder_l",
        "cupholder_r",
        "console_rotary",
        "pedal_brake",
        "pedal_accel",
        "door_card_dside_f",
        "door_card_pside_f",
        "door_card_dside_r",
        "door_card_pside_r",
        "headlight_l",
        "headlight_r",
        "taillight_l",
        "taillight_r",
        "brakelight_l",
        "brakelight_r",
        "brakelight_m",
        "indicator_lf",
        "indicator_rf",
        "indicator_lr",
        "indicator_rr",
        "reversinglight_l",
        "reversinglight_r",
        "col_chassis",
        "col_greenhouse",
        "col_roof",
        "col_bonnet",
        "col_boot",
    ]
    present = [n for n in required if bpy.data.objects.get(n)]
    missing = [n for n in required if not bpy.data.objects.get(n)]
    return {"present_count": len(present), "missing": missing, "ok": not missing}


def main():
    try:
        log("START on " + (bpy.data.filepath or "<unsaved>"))
        interior = ensure_collection("QCOMET_INTERIOR")
        body_col = ensure_collection("QCOMET_BODY_PANELS")
        mats = {
            "col": get_mat("M_QCOMET_COLLISION", (0.1, 0.8, 0.2), roughness=1.0),
        }

        m1 = milestone1_finish(interior)
        pivot_report, parent_report, hinge_tests = milestone2()
        m3 = milestone3(body_col, mats)

        bpy.context.scene["qcomet_status"] = "VEHICLE_V013_RIG_COMPLETE"
        bpy.context.scene["qcomet_milestone"] = "M1_M2_M3"
        bpy.context.scene["qcomet_identity"] = "Q Motors Q Comet — original fictional; no NoPixel / real OEM marks"

        os.makedirs(REVIEW_DIR, exist_ok=True)
        # Avoid Windows version-backup lock failures (*.blend1)
        try:
            bpy.context.preferences.filepaths.save_version = 0
        except Exception:
            pass
        log("Saving " + BLEND_OUT)
        bpy.ops.wm.save_as_mainfile(filepath=BLEND_OUT, check_existing=False)

        log("Rendering")
        try:
            renders = render_views()
        except Exception as exc:
            renders = {"error": str(exc), "trace": traceback.format_exc()[-500:]}
            log("Render error: " + str(exc))

        try:
            bpy.context.preferences.filepaths.save_version = 0
            bpy.ops.wm.save_mainfile(check_existing=False)
        except Exception as exc:
            log("Final save warning: " + str(exc))
            alt = BLEND_OUT.replace(".blend", "_rig.blend")
            bpy.ops.wm.save_as_mainfile(filepath=alt, check_existing=False)
            log("Saved alternate " + alt)

        chassis = bpy.data.objects.get("chassis")
        report = {
            "status": bpy.context.scene.get("qcomet_status"),
            "blend_file": BLEND_OUT,
            "milestones": {
                "M1_cabin": m1,
                "M2_hinging": {
                    "pivot_origins": pivot_report,
                    "door_parenting": parent_report,
                    "hinge_tests": hinge_tests,
                },
                "M3_sollumz_prep": m3,
            },
            "verification": verify(),
            "mesh_stats": mesh_stats(),
            "hierarchy_root": hierarchy_tree(chassis) if chassis else {},
            "renders": renders,
            "log": LOG,
            "note": "Collision meshes are Blender bound proxies for Sollumz .ybn authoring — GTA binaries not fabricated.",
        }
        with open(REPORT_PATH, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

        summary = {
            "ok": report["verification"]["ok"],
            "missing": report["verification"]["missing"],
            "status": report["status"],
            "blend": BLEND_OUT,
            "stats": report["mesh_stats"],
            "pivot_ok": {k: v.get("ok") for k, v in pivot_report.items()},
            "renders": renders,
            "report": REPORT_PATH,
        }
        print("SUMMARY:" + json.dumps(summary))
        log("DONE")
    except Exception:
        print("FATAL:" + traceback.format_exc())
        raise


if __name__ == "__main__":
    main()
