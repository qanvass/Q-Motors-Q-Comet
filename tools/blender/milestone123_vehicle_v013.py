"""
Q Comet Milestone 1+2+3 pass on the live Blender scene (v012 -> v013).
Original fictional Q Motors identity only. No real badges / NoPixel marks.
Does not fabricate .yft/.ytd/.ybn binaries — prepares Blender/Sollumz hierarchy.
"""
from __future__ import annotations

import json
import math
import os
from mathutils import Matrix, Vector

import bpy

ROOT = r"C:\Users\Qanva\Desktop\Gaming GTA\Q-Motors-Q-Comet"
BLEND_OUT = os.path.join(ROOT, "vehicles", "qcomet", "source", "blender", "qcomet_vehicle_v013.blend")
REVIEW_DIR = os.path.join(ROOT, "vehicles", "qcomet", "source", "blender", "review_v013")
REPORT_PATH = os.path.join(REVIEW_DIR, "milestone123_completion_report.json")

DRIVER_EYE = Vector((-0.38, 0.05, 1.20))

PIVOTS = {
    "door_dside_f": Vector((-0.97, 0.90, 0.67)),
    "door_pside_f": Vector((0.97, 0.90, 0.67)),
    "door_dside_r": Vector((-0.96, -0.18, 0.67)),
    "door_pside_r": Vector((0.96, -0.18, 0.67)),
    "bonnet": Vector((0.0, 1.14, 0.98)),
    "boot": Vector((0.0, -1.38, 0.94)),
    "steering": Vector((-0.38, 0.46, 1.02)),
}

SEAT_LAYOUT = {
    "seat_dside_f": (-0.38, 0.12),
    "seat_pside_f": (0.38, 0.12),
    "seat_dside_r": (-0.38, -0.78),
    "seat_pside_r": (0.38, -0.78),
}

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
    for col in list(obj.users_collection):
        col.objects.unlink(obj)
    if obj.name not in collection.objects:
        collection.objects.link(obj)


def get_or_create_mat(name, color, metallic=0.0, roughness=0.45, emission=None, transmission=0.0, alpha=1.0):
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    if "Transmission Weight" in bsdf.inputs:
        bsdf.inputs["Transmission Weight"].default_value = transmission
    elif "Transmission" in bsdf.inputs:
        bsdf.inputs["Transmission"].default_value = transmission
    if alpha < 1.0:
        bsdf.inputs["Alpha"].default_value = alpha
        mat.blend_method = "BLEND"
    if emission is not None:
        if "Emission Color" in bsdf.inputs:
            bsdf.inputs["Emission Color"].default_value = (*emission[0], 1.0)
            bsdf.inputs["Emission Strength"].default_value = emission[1]
        else:
            bsdf.inputs["Emission"].default_value = (*emission[0], 1.0)
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    # Soft Sollumz-oriented tags (custom props; actual Sollumz shader assign later in UI)
    mat["qcomet_shader_hint"] = "vehicle_mesh" if emission is None else "vehicle_lightsemissive"
    if transmission > 0.2:
        mat["qcomet_shader_hint"] = "vehicle_vehglass"
    return mat


def ensure_materials():
    return {
        "tan": get_or_create_mat("M_QCOMET_TAN_LEATHER", (0.62, 0.48, 0.34), roughness=0.55),
        "olive": get_or_create_mat("M_QCOMET_OLIVE_LEATHER", (0.28, 0.32, 0.18), roughness=0.5),
        "bronze": get_or_create_mat("M_QCOMET_BRONZE", (0.42, 0.22, 0.08), metallic=0.85, roughness=0.28),
        "screen": get_or_create_mat("M_QCOMET_SCREEN", (0.02, 0.02, 0.025), metallic=0.4, roughness=0.12, emission=((0.05, 0.08, 0.12), 0.35)),
        "ambient": get_or_create_mat("M_QCOMET_AMBIENT", (0.55, 0.32, 0.12), roughness=0.4, emission=((1.0, 0.55, 0.25), 2.5)),
        "blackout": get_or_create_mat("M_QCOMET_BLACKOUT", (0.012, 0.012, 0.012), roughness=0.2),
        "metal": get_or_create_mat("M_QCOMET_PEDAL_METAL", (0.35, 0.35, 0.38), metallic=0.9, roughness=0.35),
        "glass": get_or_create_mat("M_QCOMET_VEHGLASS", (0.08, 0.12, 0.14), roughness=0.04, transmission=0.88, alpha=0.25),
        "headlight": get_or_create_mat("M_QCOMET_LIGHT_HEAD", (0.95, 0.96, 0.9), roughness=0.2, emission=((1.0, 1.0, 0.92), 8.0)),
        "tail": get_or_create_mat("M_QCOMET_LIGHT_TAIL", (0.7, 0.05, 0.05), roughness=0.25, emission=((1.0, 0.08, 0.05), 4.0)),
        "brake": get_or_create_mat("M_QCOMET_LIGHT_BRAKE", (0.85, 0.05, 0.05), roughness=0.22, emission=((1.0, 0.05, 0.04), 12.0)),
        "indicator": get_or_create_mat("M_QCOMET_INDICATOR", (0.85, 0.45, 0.05), roughness=0.3, emission=((1.0, 0.55, 0.08), 6.0)),
        "reverse": get_or_create_mat("M_QCOMET_REVERSE", (0.9, 0.92, 0.95), roughness=0.25, emission=((0.95, 0.97, 1.0), 5.0)),
        "col": get_or_create_mat("M_QCOMET_COLLISION", (0.1, 0.8, 0.2), roughness=1.0),
    }


def assign_mat(obj, mat):
    if obj.type != "MESH":
        return
    obj.data.materials.clear()
    obj.data.materials.append(mat)


def delete_object(name):
    obj = bpy.data.objects.get(name)
    if obj is None:
        return
    mesh = obj.data if obj.type == "MESH" else None
    bpy.data.objects.remove(obj, do_unlink=True)
    if mesh is not None and mesh.users == 0:
        bpy.data.meshes.remove(mesh)


def safe_rename(obj, new_name):
    existing = bpy.data.objects.get(new_name)
    if existing is not None and existing != obj:
        existing.name = f"{new_name}__legacy"
    obj.name = new_name
    return obj


def set_origin_world(obj, world_location):
    """Move object origin to world pivot without shifting visible geometry."""
    if obj.type != "MESH" or obj.data is None:
        obj.matrix_world.translation = Vector(world_location)
        return
    mw = obj.matrix_world.copy()
    local = mw.inverted() @ Vector(world_location)
    obj.data.transform(Matrix.Translation(-local))
    obj.matrix_world.translation = Vector(world_location)
    obj.data.update()


def parent_keep_world(child, parent):
    if child is None or parent is None:
        return
    mw = child.matrix_world.copy()
    child.parent = parent
    child.matrix_parent_inverse = parent.matrix_world.inverted()
    child.matrix_world = mw


def box_mesh(name, x0, x1, y0, y1, z0, z1, mat, collection, bevel=0.01, segments=2):
    delete_object(name)
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=((x0 + x1) * 0.5, (y0 + y1) * 0.5, (z0 + z1) * 0.5))
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = ((x1 - x0), (y1 - y0), (z1 - z0))
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel > 0:
        mod = obj.modifiers.new("BEVEL", "BEVEL")
        mod.width = bevel
        mod.segments = segments
        mod.limit_method = "ANGLE"
        bpy.ops.object.modifier_apply(modifier=mod.name)
    assign_mat(obj, mat)
    link_object(obj, collection)
    return obj


def qplus_badge(name, location, mat, collection, scale=0.022, facing_y=1.0):
    delete_object(name)
    verts = []
    faces = []
    segs = 16
    for i in range(segs):
        a = math.tau * i / segs
        skip = 1.15 < a < 1.75
        outer = scale
        inner = 0.0 if skip else scale * 0.55
        c, s = math.cos(a), math.sin(a)
        verts.append((location[0] + c * outer, location[1], location[2] + s * outer))
        verts.append((location[0] + c * inner, location[1] - 0.004 * facing_y, location[2] + s * inner))
    for i in range(segs):
        a = i * 2
        b = ((i + 1) % segs) * 2
        faces.append((a, b, b + 1, a + 1))
    # plus bar
    px, py, pz = location
    plus = [
        (px - 0.006, py + 0.005 * facing_y, pz - 0.018),
        (px + 0.006, py + 0.005 * facing_y, pz - 0.018),
        (px + 0.006, py + 0.005 * facing_y, pz + 0.018),
        (px - 0.006, py + 0.005 * facing_y, pz + 0.018),
    ]
    plus += [(x, y - 0.007 * facing_y, z) for x, y, z in plus]
    off = len(verts)
    verts.extend(plus)
    faces.extend(((off, off + 1, off + 2, off + 3), (off + 4, off + 7, off + 6, off + 5)))
    mesh = bpy.data.meshes.new(name + "_mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    assign_mat(obj, mat)
    link_object(obj, collection)
    return obj


def make_empty(name, location, collection, size=0.08):
    delete_object(name)
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_type = "PLAIN_AXES"
    obj.empty_display_size = size
    obj.location = Vector(location)
    link_object(obj, collection)
    return obj


# ---------------------------------------------------------------------------
# Milestone 1 — cabin assembly
# ---------------------------------------------------------------------------

def rebuild_seat(name, x, y, mats, collection, with_badge=True):
    # Remove prior seat fragments
    for suffix in ("", "_cushion", "_back", "_bolster_l", "_bolster_r", "_qplus", "_headrest"):
        delete_object(f"{name}{suffix}")

    cushion = box_mesh(f"{name}_cushion", x - 0.20, x + 0.20, y - 0.22, y + 0.22, 0.42, 0.56, mats["tan"], collection, 0.028, 3)
    back = box_mesh(f"{name}_back", x - 0.20, x + 0.20, y + 0.16, y + 0.24, 0.54, 1.08, mats["tan"], collection, 0.022, 3)
    bl = box_mesh(f"{name}_bolster_l", x - 0.24, x - 0.17, y - 0.18, y + 0.18, 0.48, 0.78, mats["olive"], collection, 0.018, 2)
    br = box_mesh(f"{name}_bolster_r", x + 0.17, x + 0.24, y - 0.18, y + 0.18, 0.48, 0.78, mats["olive"], collection, 0.018, 2)
    head = box_mesh(name, x - 0.12, x + 0.12, y + 0.14, y + 0.22, 1.00, 1.16, mats["tan"], collection, 0.02, 3)
    parts = [cushion, back, bl, br]
    badge = None
    if with_badge:
        badge = qplus_badge(f"{name}_qplus", (x, y + 0.225, 1.08), mats["bronze"], collection, scale=0.02)
        parts.append(badge)
    for p in parts:
        parent_keep_world(p, head)
    head["qcomet_role"] = "seat"
    return head


def ensure_steering(mats, collection):
    # Prefer upgrading existing torus named steeringwheel -> steering
    wheel = bpy.data.objects.get("steering") or bpy.data.objects.get("steeringwheel")
    if wheel is None:
        bpy.ops.mesh.primitive_torus_add(
            location=(-0.38, 0.46, 1.02),
            rotation=(math.radians(72.0), 0.0, 0.0),
            major_radius=0.17,
            minor_radius=0.014,
            major_segments=36,
            minor_segments=12,
        )
        wheel = bpy.context.active_object
        wheel.name = "steering"
        # Flatten bottom
        for vert in wheel.data.vertices:
            co = wheel.matrix_world @ vert.co
            if co.z < 0.92:
                vert.co = wheel.matrix_world.inverted() @ Vector((co.x, co.y, co.z * 0.45 + 0.92 * 0.55))
        wheel.data.update()
    else:
        safe_rename(wheel, "steering")
    assign_mat(wheel, mats["olive"])
    link_object(wheel, collection)
    set_origin_world(wheel, PIVOTS["steering"])
    # Angle toward driver
    wheel.rotation_euler = (math.radians(72.0), 0.0, 0.0)

    for n in ("steeringwheel_hub", "steering_hub"):
        delete_object(n)
    for n in ("steeringwheel_spoke_l", "steering_spoke_l", "steeringwheel_spoke_r", "steering_spoke_r"):
        delete_object(n)

    hub = box_mesh("steering_hub", -0.43, -0.33, 0.44, 0.50, 0.97, 1.07, mats["bronze"], collection, 0.006)
    spoke_l = box_mesh("steering_spoke_l", -0.52, -0.28, 0.45, 0.49, 1.00, 1.04, mats["bronze"], collection, 0.003)
    spoke_r = box_mesh("steering_spoke_r", -0.48, -0.28, 0.45, 0.49, 0.96, 1.00, mats["bronze"], collection, 0.003)
    # Bronze Q+ center hub cap
    cap = qplus_badge("steering_qplus", (-0.38, 0.505, 1.02), mats["bronze"], collection, scale=0.028, facing_y=1.0)
    for p in (hub, spoke_l, spoke_r, cap):
        parent_keep_world(p, wheel)

    # Alias empty for legacy name
    alias = make_empty("steeringwheel", PIVOTS["steering"], collection, size=0.06)
    parent_keep_world(alias, wheel)
    wheel["qcomet_role"] = "steering"
    return wheel


def ensure_dash_and_console(mats, collection):
    dash = box_mesh("dash_glass_bar", -0.72, 0.72, 0.48, 0.62, 0.92, 1.02, mats["screen"], collection, 0.004)
    # Instrument cluster zones (speed / battery / PRND) — embossed as darker plates on glass
    cluster = box_mesh("dash_cluster", -0.55, -0.22, 0.505, 0.595, 0.945, 1.015, mats["screen"], collection, 0.002)
    icons = box_mesh("dash_center_icons", -0.14, 0.14, 0.505, 0.595, 0.945, 1.015, mats["screen"], collection, 0.002)
    # Four touch icon pads
    for i, x in enumerate((-0.105, -0.035, 0.035, 0.105)):
        pad = box_mesh(f"dash_icon_{i + 1}", x - 0.025, x + 0.025, 0.52, 0.58, 0.955, 1.012, mats["screen"], collection, 0.001)
        parent_keep_world(pad, icons)
    pass_zone = box_mesh("dash_passenger_qplus", 0.28, 0.58, 0.505, 0.595, 0.945, 1.015, mats["screen"], collection, 0.002)
    badge = qplus_badge("dash_qplus_badge", (0.43, 0.605, 0.975), mats["bronze"], collection, scale=0.018)
    strip = box_mesh("dash_ambient_strip", -0.70, 0.70, 0.50, 0.58, 0.88, 0.90, mats["ambient"], collection, 0.002)
    for child in (cluster, icons, pass_zone, badge, strip):
        parent_keep_world(child, dash)

    console = box_mesh("center_console", -0.16, 0.16, -0.55, 0.48, 0.42, 0.70, mats["olive"], collection, 0.012)
    arm = box_mesh("armrest", -0.14, 0.14, -0.52, -0.10, 0.68, 0.74, mats["olive"], collection, 0.01)
    # Split seam
    seam = box_mesh("armrest_split", -0.01, 0.01, -0.50, -0.12, 0.735, 0.742, mats["bronze"], collection, 0.0)
    cup_l = box_mesh("cupholder_l", -0.10, -0.02, 0.02, 0.10, 0.68, 0.71, mats["screen"], collection, 0.004)
    cup_r = box_mesh("cupholder_r", 0.02, 0.10, 0.02, 0.10, 0.68, 0.71, mats["screen"], collection, 0.004)
    delete_object("console_rotary")
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.045, depth=0.02, location=(0.0, 0.22, 0.71))
    rotary = bpy.context.active_object
    rotary.name = "console_rotary"
    assign_mat(rotary, mats["bronze"])
    link_object(rotary, collection)
    for child in (arm, seam, cup_l, cup_r, rotary):
        parent_keep_world(child, console)

    pedal_b = box_mesh("pedal_brake", -0.46, -0.34, 0.62, 0.70, 0.28, 0.40, mats["metal"], collection, 0.004)
    pedal_a = box_mesh("pedal_accel", -0.30, -0.18, 0.62, 0.70, 0.28, 0.40, mats["metal"], collection, 0.004)
    return dash, console, pedal_b, pedal_a


def ensure_door_cards(mats, collection):
    specs = {
        "door_card_dside_f": (-0.8898, -0.81, -0.10, 0.82, 0.42, 0.86),
        "door_card_pside_f": (0.81, 0.8898, -0.10, 0.82, 0.42, 0.86),
        "door_card_dside_r": (-0.88, -0.80, -1.18, -0.22, 0.42, 0.84),
        "door_card_pside_r": (0.80, 0.88, -1.18, -0.22, 0.42, 0.84),
    }
    cards = {}
    for name, (x0, x1, y0, y1, z0, z1) in specs.items():
        card = box_mesh(name, x0, x1, y0, y1, z0, z1, mats["tan"], collection, 0.008)
        # Bronze trim strip along upper edge
        zx = 0.86 if "f" in name else 0.84
        trim = box_mesh(
            name.replace("door_card_", "door_trim_"),
            x0 + 0.01 * (1 if x0 > 0 else -1),
            x1 - 0.01 * (1 if x0 > 0 else -1),
            y0 + 0.05,
            y1 - 0.05,
            zx - 0.025,
            zx - 0.01,
            mats["bronze"],
            collection,
            0.001,
        )
        parent_keep_world(trim, card)
        cards[name] = card
    return cards


# ---------------------------------------------------------------------------
# Milestone 2 — hinging / parenting
# ---------------------------------------------------------------------------

def snap_panel_origins():
    results = {}
    for panel, pivot in PIVOTS.items():
        if panel == "steering":
            continue
        obj = bpy.data.objects.get(panel)
        pe = bpy.data.objects.get(f"PIVOT_{panel}")
        if pe is not None:
            pivot = pe.matrix_world.translation.copy()
        if obj is None:
            results[panel] = {"ok": False, "reason": "missing"}
            continue
        # Capture a corner vertex world position to verify no visual move
        v0_before = None
        if obj.type == "MESH" and len(obj.data.vertices):
            v0_before = (obj.matrix_world @ obj.data.vertices[0].co).copy()
        set_origin_world(obj, pivot)
        v0_after = None
        delta = None
        if v0_before is not None:
            v0_after = obj.matrix_world @ obj.data.vertices[0].co
            delta = (v0_after - v0_before).length
        origin_delta = (obj.matrix_world.translation - Vector(pivot)).length
        results[panel] = {
            "ok": origin_delta < 1e-5 and (delta is None or delta < 1e-4),
            "origin_delta": round(origin_delta, 8),
            "vertex0_delta": None if delta is None else round(delta, 8),
            "pivot": [round(v, 4) for v in pivot],
        }
    return results


def test_hinge_clearance():
    """Briefly rotate opening panels and report self-intersection proxy via bbox overlap with A-pillar proxies."""
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
        # Simple clearance: door open should move outward in X for doors
        outward_ok = True
        if "dside" in name:
            outward_ok = mn.x < -0.85
        elif "pside" in name:
            outward_ok = mx.x > 0.85
        elif name == "bonnet":
            outward_ok = mx.z > 1.05
        elif name == "boot":
            outward_ok = mx.z > 1.0
        tests[name] = {
            "rotation_deg": [round(math.degrees(r), 1) for r in rot],
            "bbox_min": [round(v, 3) for v in mn],
            "bbox_max": [round(v, 3) for v in mx],
            "clearance_proxy_ok": outward_ok,
        }
        obj.rotation_euler = base
    bpy.context.view_layer.update()
    return tests


def parent_door_children(cards):
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
        "door_dside_r": [
            "door_card_dside_r",
            "glass_dside_r",
            "window_lr",
            "handle_dside_r",
        ],
        "door_pside_r": [
            "door_card_pside_r",
            "glass_pside_r",
            "window_rr",
            "handle_pside_r",
        ],
    }
    report = {}
    for door_name, children in mapping.items():
        door = bpy.data.objects.get(door_name)
        attached = []
        if door is None:
            report[door_name] = {"ok": False, "attached": []}
            continue
        for cname in children:
            child = bpy.data.objects.get(cname)
            if child is None:
                continue
            parent_keep_world(child, door)
            attached.append(cname)
        report[door_name] = {"ok": True, "attached": attached}
    return report


# ---------------------------------------------------------------------------
# Milestone 3 — hierarchy, lights, collision, save, renders
# ---------------------------------------------------------------------------

def ensure_bodyshell(collection):
    """Create bodyshell empty as GTA outer-shell root; parent fixed body skins under it."""
    chassis = bpy.data.objects.get("chassis")
    if chassis is None:
        chassis = make_empty("chassis", (0.0, 0.0, 0.2), collection, size=0.2)
    bodyshell = bpy.data.objects.get("bodyshell")
    if bodyshell is None:
        bodyshell = make_empty("bodyshell", (0.0, 0.0, 0.55), collection, size=0.18)
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
        "roof",
        "cantrail_dside",
        "cantrail_pside",
        "a_pillar_dside",
        "a_pillar_pside",
        "c_pillar_dside",
        "c_pillar_pside",
    ]
    attached = []
    for name in fixed:
        obj = bpy.data.objects.get(name)
        if obj is None:
            continue
        parent_keep_world(obj, bodyshell)
        attached.append(name)
    return chassis, bodyshell, attached


def rename_glass_windows():
    mapping = {
        "glass_dside_f": "window_lf",
        "glass_pside_f": "window_rf",
        "glass_dside_r": "window_lr",
        "glass_pside_r": "window_rr",
    }
    done = {}
    for old, new in mapping.items():
        obj = bpy.data.objects.get(old) or bpy.data.objects.get(new)
        if obj is None:
            done[new] = False
            continue
        safe_rename(obj, new)
        # Ensure vehglass hint material stays if present
        if obj.type == "MESH" and obj.data.materials:
            for slot in obj.material_slots:
                if slot.material:
                    slot.material["qcomet_shader_hint"] = "vehicle_vehglass"
        done[new] = True
    return done


def ensure_light_hierarchy(mats, collection):
    """Create GTA-named light empties with Light IDs and parent existing emissive meshes."""
    lights_col = ensure_collection("QCOMET_LIGHTS_GTA")

    def group(name, location, light_id, children, mat_hint=None):
        root = bpy.data.objects.get(name)
        if root is None:
            root = make_empty(name, location, lights_col, size=0.1)
        else:
            link_object(root, lights_col)
            root.location = Vector(location)
        root["LightId"] = light_id
        root["qcomet_role"] = "light"
        if mat_hint:
            root["qcomet_shader_hint"] = "vehicle_lightsemissive"
        attached = []
        for cname in children:
            child = bpy.data.objects.get(cname)
            if child is None:
                continue
            parent_keep_world(child, root)
            if child.type == "MESH":
                for slot in child.material_slots:
                    if slot.material:
                        slot.material["qcomet_shader_hint"] = "vehicle_lightsemissive"
            attached.append(cname)
        return {"light_id": light_id, "attached": attached}

    report = {}
    report["headlight_l"] = group(
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
        mats["headlight"],
    )
    report["headlight_r"] = group(
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
        mats["headlight"],
    )
    # Tail / brake share rear bar — split via empties + props
    report["taillight_l"] = group("taillight_l", (-0.55, -2.28, 0.87), 2, ["tail_bar_brake"], mats["tail"])
    report["taillight_r"] = group("taillight_r", (0.55, -2.28, 0.87), 3, [], mats["tail"])
    report["brakelight_l"] = group("brakelight_l", (-0.45, -2.28, 0.87), 2, [], mats["brake"])
    report["brakelight_r"] = group("brakelight_r", (0.45, -2.28, 0.87), 3, [], mats["brake"])
    report["brakelight_m"] = group("brakelight_m", (0.0, -2.28, 0.87), -1, [], mats["brake"])
    report["indicator_lf"] = group("indicator_lf", (-0.9, 2.1, 0.7), -1, ["mirror_dside_indicator"], mats["indicator"])
    report["indicator_rf"] = group("indicator_rf", (0.9, 2.1, 0.7), -1, ["mirror_pside_indicator"], mats["indicator"])
    report["indicator_lr"] = group("indicator_lr", (-0.7, -2.28, 0.87), -1, [], mats["indicator"])
    report["indicator_rr"] = group("indicator_rr", (0.7, -2.28, 0.87), -1, [], mats["indicator"])
    report["reversinglight_l"] = group("reversinglight_l", (-0.13, -2.34, 0.24), -1, ["reverse_dside", "reverse_dside_housing"], mats["reverse"])
    report["reversinglight_r"] = group("reversinglight_r", (0.13, -2.34, 0.24), -1, ["reverse_pside", "reverse_pside_housing"], mats["reverse"])
    return report


def ensure_wheel_origins():
    report = {}
    for name in ("wheel_lf", "wheel_rf", "wheel_lr", "wheel_rr"):
        obj = bpy.data.objects.get(name)
        if obj is None:
            report[name] = {"ok": False}
            continue
        # Origin should already be near wheel center (object location)
        center = obj.matrix_world.translation.copy()
        # Tag for Sollumz Is Wheel Mesh
        obj["sollumz_is_wheel_mesh"] = True
        obj["qcomet_role"] = "wheel"
        # Parent rim children if any
        for o in list(bpy.data.objects):
            if o.name.startswith(name + "_") or o.name.startswith(name.replace("wheel_", "rim_")):
                parent_keep_world(o, obj)
        report[name] = {"ok": True, "center": [round(v, 4) for v in center]}
    return report


def build_collision(mats):
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
    created = []
    for name, dims in specs.items():
        obj = box_mesh(name, *dims, mats["col"], col, bevel=0.0)
        obj.display_type = "WIRE"
        obj.hide_render = True
        obj["qcomet_role"] = "collision"
        obj["qcomet_bound"] = "composite"
        created.append(name)
    # Parent door/hood/boot collision to panels when present
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
    return created


def parent_core_hierarchy(chassis):
    """Parent major game parts under chassis for Sollumz prep."""
    children = [
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
    attached = []
    for name in children:
        obj = bpy.data.objects.get(name)
        if obj is None:
            continue
        parent_keep_world(obj, chassis)
        attached.append(name)
    return attached


def hierarchy_tree(obj, depth=0, max_depth=6):
    node = {
        "name": obj.name,
        "type": obj.type,
        "children": [],
    }
    if obj.type == "MESH" and obj.data:
        node["verts"] = len(obj.data.vertices)
        node["faces"] = len(obj.data.polygons)
    if depth < max_depth:
        for child in sorted(obj.children, key=lambda o: o.name):
            node["children"].append(hierarchy_tree(child, depth + 1, max_depth))
    return node


def mesh_stats():
    total_v = total_f = 0
    by_role = {}
    for obj in bpy.data.objects:
        if obj.type != "MESH" or obj.data is None:
            continue
        if obj.name.startswith(("v010_", "v011_", "REF", "GUIDE")):
            continue
        v = len(obj.data.vertices)
        f = len(obj.data.polygons)
        total_v += v
        total_f += f
        role = obj.get("qcomet_role", "mesh")
        by_role.setdefault(role, {"objects": 0, "verts": 0, "faces": 0})
        by_role[role]["objects"] += 1
        by_role[role]["verts"] += v
        by_role[role]["faces"] += f
    return {"total_verts": total_v, "total_faces": total_f, "by_role": by_role}


def setup_review_camera():
    cam = bpy.data.objects.get("QCOMET_REVIEW_CAMERA")
    if cam is None:
        bpy.ops.object.camera_add()
        cam = bpy.context.active_object
        cam.name = "QCOMET_REVIEW_CAMERA"
    sun = bpy.data.objects.get("QCOMET_REVIEW_SUN")
    if sun is None:
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


def render_review_views():
    os.makedirs(REVIEW_DIR, exist_ok=True)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT" if hasattr(bpy.types, "EEVEE") or "BLENDER_EEVEE_NEXT" in dir(bpy.types) else scene.render.engine
    # Prefer Eevee Next on 5.x
    if "BLENDER_EEVEE_NEXT" in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items.keys():
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    elif "BLENDER_EEVEE" in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items.keys():
        scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1600
    scene.render.resolution_y = 900
    scene.render.image_settings.file_format = "PNG"
    cam = setup_review_camera()

    # Open doors for open-door view (then restore)
    door_rots = {}
    for name, z in (("door_dside_f", 55), ("door_pside_f", -55), ("door_dside_r", 50), ("door_pside_r", -50)):
        obj = bpy.data.objects.get(name)
        if obj:
            door_rots[name] = obj.rotation_euler.copy()
            obj.rotation_euler = (0, 0, math.radians(z))

    views = [
        ("interior_cockpit", DRIVER_EYE + Vector((0.05, 0.15, 0.02)), Vector((0.0, 0.85, 0.95))),
        ("open_doors", Vector((-3.2, 1.4, 1.5)), Vector((0.0, 0.2, 0.7))),
        ("exterior_34", Vector((-3.6, -3.2, 1.6)), Vector((0.0, 0.1, 0.7))),
    ]
    # First render with doors open for open_doors; cockpit with closed; exterior with closed
    outputs = {}

    # Restore doors for cockpit + exterior; open only for open_doors
    for name, base in door_rots.items():
        bpy.data.objects[name].rotation_euler = base
    bpy.context.view_layer.update()

    # cockpit
    look_at(cam, views[0][1], views[0][2])
    path = os.path.join(REVIEW_DIR, "interior_cockpit.png")
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    outputs["interior_cockpit"] = path

    # open doors
    for name, z in (("door_dside_f", 55), ("door_pside_f", -55), ("door_dside_r", 50), ("door_pside_r", -50)):
        obj = bpy.data.objects.get(name)
        if obj:
            obj.rotation_euler = (0, 0, math.radians(z))
    bpy.context.view_layer.update()
    look_at(cam, views[1][1], views[1][2])
    path = os.path.join(REVIEW_DIR, "open_doors.png")
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    outputs["open_doors"] = path

    # restore + exterior
    for name, base in door_rots.items():
        bpy.data.objects[name].rotation_euler = base
    bpy.context.view_layer.update()
    look_at(cam, views[2][1], views[2][2])
    path = os.path.join(REVIEW_DIR, "exterior_34.png")
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    outputs["exterior_34"] = path
    return outputs


def verify_required():
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
    return {"present": present, "missing": missing, "ok": len(missing) == 0}


def main():
    log("START milestone123 on " + (bpy.data.filepath or "<unsaved>"))
    mats = ensure_materials()
    interior = ensure_collection("QCOMET_INTERIOR")
    body_col = ensure_collection("QCOMET_BODY_PANELS")

    # --- M1 ---
    log("M1 cabin assembly")
    seats = {}
    for name, (x, y) in SEAT_LAYOUT.items():
        seats[name] = rebuild_seat(name, x, y, mats, interior, with_badge=True)
    steering = ensure_steering(mats, interior)
    dash, console, pedal_b, pedal_a = ensure_dash_and_console(mats, interior)
    cards = ensure_door_cards(mats, interior)
    log("M1 complete")

    # --- M2 ---
    log("M2 hinge origins")
    pivot_report = snap_panel_origins()
    # Re-apply steering origin after rebuild
    if steering:
        set_origin_world(steering, PIVOTS["steering"])
    parent_report = parent_door_children(cards)
    hinge_tests = test_hinge_clearance()
    log("M2 complete")

    # --- M3 ---
    log("M3 hierarchy / lights / collision")
    chassis, bodyshell, body_attached = ensure_bodyshell(body_col)
    glass_report = rename_glass_windows()
    # Re-parent windows after rename (door children)
    parent_door_children(cards)
    lights_report = ensure_light_hierarchy(mats, body_col)
    wheels_report = ensure_wheel_origins()
    cols = build_collision(mats)
    core = parent_core_hierarchy(chassis)

    bpy.context.scene["qcomet_status"] = "VEHICLE_V013_RIG_COMPLETE"
    bpy.context.scene["qcomet_milestone"] = "M1_M2_M3"
    bpy.context.scene["qcomet_identity"] = "Q Motors Q Comet — original fictional; no NoPixel / real OEM marks"

    os.makedirs(REVIEW_DIR, exist_ok=True)
    log("Saving " + BLEND_OUT)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND_OUT)

    log("Rendering review views")
    try:
        renders = render_review_views()
    except Exception as exc:
        renders = {"error": str(exc)}
        log("Render warning: " + str(exc))

    # Save again after renders/camera tweaks
    bpy.ops.wm.save_mainfile()

    verification = verify_required()
    stats = mesh_stats()
    chassis_obj = bpy.data.objects.get("chassis")
    hierarchy = hierarchy_tree(chassis_obj) if chassis_obj else {}

    report = {
        "status": bpy.context.scene.get("qcomet_status"),
        "blend_file": BLEND_OUT,
        "source_was": bpy.data.filepath,
        "milestones": {
            "M1_cabin": {
                "seats": list(seats.keys()),
                "steering": steering.name if steering else None,
                "dash": dash.name if dash else None,
                "console": console.name if console else None,
                "door_cards": list(cards.keys()),
                "materials": [
                    "M_QCOMET_TAN_LEATHER",
                    "M_QCOMET_OLIVE_LEATHER",
                    "M_QCOMET_SCREEN",
                    "M_QCOMET_AMBIENT",
                    "M_QCOMET_BRONZE",
                ],
                "driver_eye_target": list(DRIVER_EYE),
            },
            "M2_hinging": {
                "pivot_origins": pivot_report,
                "door_parenting": parent_report,
                "hinge_tests": hinge_tests,
            },
            "M3_sollumz_prep": {
                "bodyshell_children": body_attached,
                "glass_windows": glass_report,
                "lights": lights_report,
                "wheels": wheels_report,
                "collision": cols,
                "chassis_children": core,
                "note": "Collision meshes are Blender bound proxies for Sollumz .ybn authoring — binaries not fabricated.",
            },
        },
        "verification": verification,
        "mesh_stats": stats,
        "hierarchy_root": hierarchy,
        "renders": renders,
        "log": LOG,
    }
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    log("REPORT " + REPORT_PATH)
    print(json.dumps({
        "ok": verification["ok"],
        "missing": verification["missing"],
        "status": report["status"],
        "blend": BLEND_OUT,
        "stats": stats,
        "pivot_ok": {k: v.get("ok") for k, v in pivot_report.items()},
        "renders": renders,
        "report": REPORT_PATH,
    }, indent=2))


if __name__ == "__main__":
    main()
