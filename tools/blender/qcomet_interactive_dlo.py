"""Q Comet interactive steps — one Run Script click each.

Revision: a-pillar-2

Sequence
--------
1. Checkpoint the unsaved scene, Save As unused working file, verify.
2. Hide identified references, frame Q Comet collections, stop if that is the next step.
3. Measure and rake A-pillars only. Then stop for local visual review.

No "all" mode. No material edits. No C/B-pillar, glass, or drip-rail changes.

Open this file in the already-running Blender window (Scripting workspace)
and click Run Script. Watch the System Console (Window > Toggle System Console).
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime

import bpy
from mathutils import Vector


SCRIPT_REVISION = "a-pillar-2"

PROTECTED_BLEND_NAMES = {
    "qcomet_blockout_v001.blend",
    "qcomet_blockout_v002.blend",
    "qcomet_body_v003.blend",
    "qcomet_body_v004.blend",
    "qcomet_body_v005.blend",
}

QCOMET_COLLECTIONS = (
    "QCOMET_BODY_PANELS",
    "QCOMET_GLASS",
    "QCOMET_LIGHTS",
    "QCOMET_RUNNING_GEAR",
    "QCOMET_INTERIOR",
)

STEPS = (
    "checkpoint_and_retarget",
    "hide_refs_and_frame",
    "apply_a_pillars",
)

PILLAR_A = ("pillar_a_dside", "pillar_a_pside")
GREENHOUSE = "panoramic_glass_greenhouse"

MAX_PILLAR_VERTS = 128
HEIGHT_FRAC = 0.18
ENDPOINT_Y_SPREAD_MAX = 0.12
SYMMETRY_TOL = 0.008
THICKNESS_TOL = 0.006
AMBIGUOUS_TARGET_Y_SPREAD = 0.28
ALLOWED_PILLAR_MODIFIERS = frozenset({"BEVEL"})


def log(msg):
    print(f"QCOMET | {msg}", flush=True)
    try:
        bpy.context.workspace.status_text_set(("QCOMET | " + msg)[:255])
    except Exception:
        pass


def scn():
    return bpy.context.scene


def evidence_dir():
    path = os.path.join(blend_dir(), "review_interactive")
    os.makedirs(path, exist_ok=True)
    return path


def blend_dir():
    if bpy.data.filepath:
        return os.path.dirname(bpy.data.filepath)
    return os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "vehicles", "qcomet", "source", "blender")
    )


def is_protected_path(path):
    return os.path.basename(path) in PROTECTED_BLEND_NAMES


def same_path(a, b):
    if not a or not b:
        return False
    return os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))


def write_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
    os.replace(tmp, path)


def write_report(name, payload):
    folder = evidence_dir()
    write_json(os.path.join(folder, f"{name}.json"), payload)
    text_path = os.path.join(folder, f"{name}.txt")
    with open(text_path, "w", encoding="utf-8") as handle:
        handle.write(f"QCOMET {name}\nrevision={SCRIPT_REVISION}\n{datetime.now().isoformat()}\n\n")
        handle.write(json.dumps(payload, indent=2))
        handle.write("\n")
    log(f"wrote {text_path}")
    return text_path


def ensure_gui():
    if bpy.app.background:
        raise RuntimeError("Refusing background Blender. Use the open window.")


def op_finished(result, label):
    if result != {"FINISHED"}:
        raise RuntimeError(f"{label} did not return FINISHED: {result}")


def verify_file(path, label, min_bytes):
    if not path or not os.path.isfile(path):
        raise RuntimeError(f"{label} missing: {path}")
    size = os.path.getsize(path)
    if size < min_bytes:
        raise RuntimeError(f"{label} too small ({size} B): {path}")
    if time.time() - os.path.getmtime(path) > 180:
        raise RuntimeError(f"{label} is stale: {path}")
    return size


def unused_working_path():
    folder = blend_dir()
    for number in range(6, 100):
        name = f"qcomet_body_v{number:03d}.blend"
        path = os.path.join(folder, name)
        if name not in PROTECTED_BLEND_NAMES and not os.path.exists(path):
            return path
    raise RuntimeError("No free working filename starting at v006")


def is_reference_object(obj):
    if obj.name.startswith("REFIMG") or obj.name.startswith("REF_"):
        return True
    if obj.type == "EMPTY" and getattr(obj, "empty_display_type", "") == "IMAGE":
        return True
    if "CONCEPT_REFERENCES" in {c.name for c in obj.users_collection}:
        return True
    return False


def in_qcomet_collection(obj):
    return any(col.name in QCOMET_COLLECTIONS for col in obj.users_collection)


def view_layer_object_names():
    return {obj.name for obj in bpy.context.view_layer.objects}


def vec3(v):
    return [float(v.x), float(v.y), float(v.z)]


def evaluated_world_verts(obj):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        matrix = evaluated.matrix_world
        return [matrix @ vert.co.copy() for vert in mesh.vertices]
    finally:
        evaluated.to_mesh_clear()


def base_world_verts(obj):
    """World-space coordinates of the undeformed base mesh (not the bevel eval)."""
    matrix = obj.matrix_world.copy()
    return [matrix @ vert.co.copy() for vert in obj.data.vertices]


def ensure_object_mode():
    if getattr(bpy.context, "mode", "OBJECT") != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")


def snapshot_bevel_state(obj):
    rows = []
    for mod in obj.modifiers:
        rows.append(
            {
                "name": mod.name,
                "type": mod.type,
                "show_viewport": bool(mod.show_viewport),
                "show_render": bool(mod.show_render),
                "width": float(getattr(mod, "width", 0.0) or 0.0),
                "segments": int(getattr(mod, "segments", 0) or 0),
                "limit_method": str(getattr(mod, "limit_method", "")),
                "offset_type": str(getattr(mod, "offset_type", "")),
                "affect": str(getattr(mod, "affect", "")),
                "harden_normals": bool(getattr(mod, "harden_normals", False)),
                "use_clamp_overlap": bool(getattr(mod, "use_clamp_overlap", True)),
            }
        )
    return rows


def bevel_width_slack(obj):
    loc = base_world_verts(obj)
    size = 0.05
    if loc:
        size = max(
            max(p.x for p in loc) - min(p.x for p in loc),
            max(p.y for p in loc) - min(p.y for p in loc),
            max(p.z for p in loc) - min(p.z for p in loc),
            0.01,
        )
    slack = 0.0
    for mod in obj.modifiers:
        if mod.type != "BEVEL":
            continue
        width = float(getattr(mod, "width", 0.0) or 0.0)
        if str(getattr(mod, "offset_type", "OFFSET")) == "PERCENT":
            slack += abs(width) * 0.01 * size
        else:
            slack += abs(width)
    return slack


def pillar_modifier_stack_ok(obj):
    types = [mod.type for mod in obj.modifiers]
    if not types:
        return True, "ok"
    extra = [t for t in types if t not in ALLOWED_PILLAR_MODIFIERS]
    if extra:
        return False, f"unsupported modifiers: {types}"
    for mod in obj.modifiers:
        if not mod.show_viewport:
            return False, (
                f"BEVEL {mod.name!r} disabled in viewport "
                "(invalid / muted / applied-needed)"
            )
        width = float(getattr(mod, "width", 0.0) or 0.0)
        if width < 0.0 or width != width:
            return False, f"BEVEL {mod.name!r} has invalid width {width}"
        segments = int(getattr(mod, "segments", 1) or 0)
        if segments < 1:
            return False, f"BEVEL {mod.name!r} has invalid segments {segments}"
    return True, "bevel_ok"


def cluster_xy_span(cluster):
    if cluster is None:
        return None
    pts = cluster["points"]
    xs = [p.x for p in pts]
    ys = [p.y for p in pts]
    return (max(xs) - min(xs), max(ys) - min(ys))


def aabb_overlap(report_a, report_b, eps=1e-6):
    if report_a["min"] is None or report_b["min"] is None:
        return True
    a_min, a_max = report_a["min"], report_a["max"]
    b_min, b_max = report_b["min"], report_b["max"]
    return (
        a_min.x <= b_max.x + eps
        and a_max.x >= b_min.x - eps
        and a_min.y <= b_max.y + eps
        and a_max.y >= b_min.y - eps
        and a_min.z <= b_max.z + eps
        and a_max.z >= b_min.z - eps
    )


def evaluated_pillar_report(obj):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        matrix = evaluated.matrix_world.copy()
        points = [matrix @ vert.co.copy() for vert in mesh.vertices]
        degenerate = 0
        for poly in mesh.polygons:
            if float(poly.area) <= 1e-12:
                degenerate += 1
        has_nan = any(p.x != p.x or p.y != p.y or p.z != p.z for p in points)
        lower = cluster_by_z(points, "lower") if len(points) >= 4 else None
        upper = cluster_by_z(points, "upper") if len(points) >= 4 else None
        if points:
            mins = Vector(
                (min(p.x for p in points), min(p.y for p in points), min(p.z for p in points))
            )
            maxs = Vector(
                (max(p.x for p in points), max(p.y for p in points), max(p.z for p in points))
            )
        else:
            mins = maxs = None
        return {
            "points": points,
            "n_verts": len(mesh.vertices),
            "n_polys": len(mesh.polygons),
            "degenerate": degenerate,
            "has_nan": has_nan,
            "lower": lower,
            "upper": upper,
            "min": mins,
            "max": maxs,
            "bevel_slack": bevel_width_slack(obj),
            "bevel_state": snapshot_bevel_state(obj),
        }
    finally:
        evaluated.to_mesh_clear()


def cluster_by_z(points, which):
    zs = [p.z for p in points]
    zmin, zmax = min(zs), max(zs)
    height = zmax - zmin
    if height < 0.05:
        return None
    if which == "lower":
        group = [p for p in points if p.z <= zmin + height * HEIGHT_FRAC]
    else:
        group = [p for p in points if p.z >= zmax - height * HEIGHT_FRAC]
    if len(group) < 2:
        return None
    ys = [p.y for p in group]
    if max(ys) - min(ys) > ENDPOINT_Y_SPREAD_MAX + 0.20 and which == "lower":
        # Boxes have Y thickness; allow pillar depth, reject chaotic clouds.
        if max(ys) - min(ys) > 0.40:
            return None
    center = Vector(
        (
            sum(p.x for p in group) / len(group),
            sum(p.y for p in group) / len(group),
            sum(p.z for p in group) / len(group),
        )
    )
    return {"center": center, "count": len(group), "points": group}


def audit_legacy_state():
    scene = scn()
    flags = {
        "filepath": bpy.data.filepath,
        "script_revision_in_scene": scene.get("qcomet_script_revision", ""),
        "interactive_index": int(scene.get("qcomet_interactive_index", 0)),
        "completed_step": scene.get("qcomet_completed_step", ""),
        "checkpoint_verified": bool(scene.get("qcomet_checkpoint_verified", False)),
        "checkpoint_path": scene.get("qcomet_interactive_checkpoint", ""),
        "working_path": scene.get("qcomet_working_file", ""),
        "status": scene.get("qcomet_status", ""),
        "a_pillar_marker": scene.get("qcomet_a_pillars_complete", False),
        "objects": {},
    }
    log("=== STATE AUDIT (not resetting index) ===")
    log(f"filepath={flags['filepath'] or '(unsaved)'}")
    log(f"index={flags['interactive_index']} completed_step={flags['completed_step']!r}")
    log(f"revision_in_scene={flags['script_revision_in_scene']!r} this_script={SCRIPT_REVISION}")
    log(f"checkpoint_verified={flags['checkpoint_verified']}")
    log(f"checkpoint_path={flags['checkpoint_path']}")
    log(f"working_path={flags['working_path']}")
    for name in PILLAR_A + ("pillar_b_dside", "pillar_c_dside", GREENHOUSE):
        obj = bpy.data.objects.get(name)
        if obj is None:
            log(f"  MISSING {name}")
            flags["objects"][name] = None
            continue
        rec = {
            "location": vec3(obj.location),
            "rotation_euler": [float(a) for a in obj.rotation_euler],
            "scale": vec3(obj.scale),
            "delta_rotation": [float(a) for a in obj.delta_rotation_euler],
            "mesh_users": int(obj.data.users) if obj.type == "MESH" else 0,
            "modifiers": [mod.type for mod in obj.modifiers],
            "custom": {
                key: obj[key]
                for key in obj.keys()
                if key.startswith("qcomet_")
            },
        }
        flags["objects"][name] = rec
        log(
            f"  {name} loc={rec['location']} rot={rec['rotation_euler']} "
            f"scale={rec['scale']} users={rec['mesh_users']} mods={rec['modifiers']} "
            f"flags={rec['custom']}"
        )
    write_report("00_state_audit", flags)
    return flags


def checkpoint_is_verified(flags):
    checkpoint = flags["checkpoint_path"]
    working = flags["working_path"] or bpy.data.filepath
    if not flags["checkpoint_verified"]:
        return False, "scene flag qcomet_checkpoint_verified is false"
    if not checkpoint or not os.path.isfile(checkpoint):
        return False, f"checkpoint file missing: {checkpoint}"
    if not working or not os.path.isfile(working):
        return False, f"working file missing: {working}"
    if is_protected_path(working):
        return False, f"session still on protected file {working}"
    if is_protected_path(checkpoint):
        return False, "checkpoint path is a protected original"
    if not same_path(bpy.data.filepath, working):
        return False, f"filepath {bpy.data.filepath} != working {working}"
    if same_path(bpy.data.filepath, checkpoint):
        return False, "filepath still points at the checkpoint copy"
    return True, "verified"


def record_scene_progress(step_name, index):
    scene = scn()
    scene["qcomet_script_revision"] = SCRIPT_REVISION
    scene["qcomet_completed_step"] = step_name
    scene["qcomet_interactive_index"] = int(index)
    scene["qcomet_status"] = "BLOCKOUT_INTERACTIVE_WORKING"


def step_checkpoint_and_retarget(flags):
    ok, reason = checkpoint_is_verified(flags)
    if ok:
        log(f"Checkpoint already verified ({reason}). Not writing another copy.")
        payload = {
            "valid": True,
            "idempotent_skip": True,
            "checkpoint": flags["checkpoint_path"],
            "working": bpy.data.filepath,
            "revision": SCRIPT_REVISION,
        }
        record_scene_progress("checkpoint_and_retarget", max(flags["interactive_index"], 1))
        write_report("01_checkpoint_and_retarget", payload)
        return payload

    current = bpy.data.filepath
    if current and is_protected_path(current):
        log(f"Source {os.path.basename(current)} is protected and will not be overwritten")
    folder = blend_dir()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    checkpoint = os.path.join(folder, f"qcomet_v004_unsaved_checkpoint_{stamp}.blend")
    if os.path.exists(checkpoint) or is_protected_path(checkpoint):
        raise RuntimeError(f"Checkpoint path not allowed: {checkpoint}")

    before = os.path.getsize(current) if current and os.path.isfile(current) else 200000
    result = bpy.ops.wm.save_as_mainfile(filepath=checkpoint, copy=True, check_existing=False)
    op_finished(result, "Checkpoint save_as copy")
    ck_size = verify_file(checkpoint, "Checkpoint", max(10000, int(before * 0.5)))
    if same_path(bpy.data.filepath, checkpoint):
        raise RuntimeError("copy=True changed bpy.data.filepath onto the checkpoint")

    working = unused_working_path()
    if is_protected_path(working) or os.path.exists(working):
        raise RuntimeError(f"Refusing working path {working}")
    result = bpy.ops.wm.save_as_mainfile(filepath=working, copy=False, check_existing=False)
    op_finished(result, "Working Save As")
    if not same_path(bpy.data.filepath, working):
        raise RuntimeError(
            f"filepath after Save As is {bpy.data.filepath!r}, expected {working!r}"
        )
    wk_size = verify_file(working, "Working file", max(10000, int(ck_size * 0.5)))
    if is_protected_path(bpy.data.filepath):
        raise RuntimeError("Session still on a protected original")
    if same_path(bpy.data.filepath, checkpoint):
        raise RuntimeError("Session points at checkpoint; original/checkpoint must stay read-only")

    scene = scn()
    scene["qcomet_interactive_checkpoint"] = checkpoint
    scene["qcomet_working_file"] = working
    scene["qcomet_checkpoint_verified"] = True
    record_scene_progress("checkpoint_and_retarget", 1)
    result = bpy.ops.wm.save_mainfile()
    op_finished(result, "Working save after recording paths")
    if not same_path(bpy.data.filepath, working):
        raise RuntimeError("save_mainfile retargeted the session")
    verify_file(working, "Working file after props", max(10000, int(wk_size * 0.5)))
    if same_path(checkpoint, working):
        raise RuntimeError("Checkpoint and working paths are identical")

    payload = {
        "valid": True,
        "revision": SCRIPT_REVISION,
        "checkpoint": checkpoint,
        "checkpoint_bytes": ck_size,
        "working": working,
        "working_bytes": os.path.getsize(working),
        "filepath": bpy.data.filepath,
        "operator": "FINISHED",
        "completed_step": "checkpoint_and_retarget",
    }
    write_report("01_checkpoint_and_retarget", payload)
    log(f"CHECKPOINT OK {checkpoint} ({ck_size} B)")
    log(f"WORKING OK {working} ({payload['working_bytes']} B)")
    log("File > Save now writes the working file only.")
    return payload


def step_hide_refs_and_frame(_flags):
    ok, reason = checkpoint_is_verified(
        {
            "checkpoint_verified": bool(scn().get("qcomet_checkpoint_verified", False)),
            "checkpoint_path": scn().get("qcomet_interactive_checkpoint", ""),
            "working_path": scn().get("qcomet_working_file", bpy.data.filepath),
        }
    )
    if not ok:
        raise RuntimeError(f"Refuse hide/frame until checkpoint is verified: {reason}")

    vis_path = os.path.join(evidence_dir(), "original_reference_visibility.json")
    recorded = {"objects": {}}
    if os.path.isfile(vis_path):
        with open(vis_path, "r", encoding="utf-8") as handle:
            recorded = json.load(handle)

    hidden = []
    layer_names = view_layer_object_names()
    for obj in bpy.data.objects:
        if not is_reference_object(obj):
            continue
        if obj.name not in recorded["objects"]:
            recorded["objects"][obj.name] = {
                "hide_get": bool(obj.hide_get()),
                "hide_viewport": bool(obj.hide_viewport),
                "hide_render": bool(obj.hide_render),
                "in_view_layer": obj.name in layer_names,
            }
        obj.hide_set(True)
        obj.hide_viewport = True
        obj.hide_render = True
        hidden.append(obj.name)
    write_json(vis_path, recorded)

    selectable = []
    for obj in bpy.context.view_layer.objects:
        if obj.type != "MESH":
            continue
        if is_reference_object(obj):
            continue
        if not in_qcomet_collection(obj):
            continue
        if "cutter" in obj.name.lower():
            continue
        if obj.hide_get() or obj.hide_viewport:
            continue
        selectable.append(obj)

    if not selectable:
        raise RuntimeError("No visible Q Comet collection meshes in the active view layer")

    bpy.ops.object.select_all(action="DESELECT")
    for obj in selectable:
        obj.select_set(True)
    chassis = bpy.data.objects.get("chassis")
    if chassis and chassis in selectable:
        bpy.context.view_layer.objects.active = chassis
    else:
        bpy.context.view_layer.objects.active = selectable[0]

    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type != "VIEW_3D":
                continue
            for space in area.spaces:
                if space.type != "VIEW_3D":
                    continue
                shading = space.shading
                shading.type = "SOLID"
                if hasattr(shading, "show_xray"):
                    shading.show_xray = False
                if hasattr(shading, "color_type"):
                    shading.color_type = "SINGLE"
                if hasattr(shading, "single_color"):
                    shading.single_color = (0.55, 0.55, 0.55)

    framed = False
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type != "VIEW_3D":
                continue
            region = next((r for r in area.regions if r.type == "WINDOW"), None)
            space = next((s for s in area.spaces if s.type == "VIEW_3D"), None)
            if region is None or space is None:
                continue
            with bpy.context.temp_override(
                window=window,
                screen=window.screen,
                area=area,
                region=region,
                space=space,
                scene=scn(),
                view_layer=bpy.context.view_layer,
            ):
                bpy.ops.view3d.view_selected(use_all_regions=False)
            framed = True
            break
        if framed:
            break

    payload = {
        "valid": True,
        "refs_hidden": hidden,
        "visibility_record": vis_path,
        "framed_objects": [obj.name for obj in selectable],
        "framed_count": len(selectable),
        "view_framed": framed,
        "unhid_all_meshes": False,
        "completed_step": "hide_refs_and_frame",
    }
    record_scene_progress("hide_refs_and_frame", 2)
    result = bpy.ops.wm.save_mainfile()
    op_finished(result, "Save after hide/frame")
    write_report("02_hide_refs_and_frame", payload)
    log(f"Hid {len(hidden)} refs. Framed {len(selectable)} Q Comet meshes. Did not unhide the rest.")
    return payload


def greenhouse_connection(greenhouse_pts, pillar_x, z_lo, z_hi, edge):
    x_sign = 1.0 if pillar_x >= 0.0 else -1.0
    band = [
        p
        for p in greenhouse_pts
        if z_lo <= p.z <= z_hi and (p.x * x_sign) > 0.20
    ]
    if len(band) < 3:
        raise RuntimeError(f"Ambiguous greenhouse {edge} connection: {len(band)} verts in z-band")
    ys = [p.y for p in band]
    if max(ys) - min(ys) > AMBIGUOUS_TARGET_Y_SPREAD:
        # Prefer the front (max Y) or rear (min Y) lip rather than the whole cabin.
        if edge == "upper":
            y_cut = max(ys) - 0.08
            band = [p for p in band if p.y >= y_cut] or band
        else:
            y_cut = max(ys) - 0.08
            band = [p for p in band if p.y >= y_cut] or band
    # Lateral station: verts whose |x| is closest to the pillar |x|.
    lateral = sorted(band, key=lambda p: abs(abs(p.x) - abs(pillar_x)))[: max(4, len(band) // 4)]
    center = Vector(
        (
            sum(p.x for p in lateral) / len(lateral),
            sum(p.y for p in lateral) / len(lateral),
            sum(p.z for p in lateral) / len(lateral),
        )
    )
    return center, len(lateral)


def pillar_topology_ok(obj):
    if obj.type != "MESH" or obj.data is None:
        return False, "not a mesh"
    if len(obj.data.vertices) < 4 or len(obj.data.vertices) > MAX_PILLAR_VERTS:
        return False, f"unsupported vert count {len(obj.data.vertices)}"
    ok, why = pillar_modifier_stack_ok(obj)
    if not ok:
        return False, why
    return True, "ok"


def make_mesh_single_user(obj):
    if obj.data.users > 1:
        log(f"{obj.name} mesh users={obj.data.users}; making single-user copy")
        obj.data = obj.data.copy()


def stored_originals_path():
    return os.path.join(evidence_dir(), "a_pillar_originals.json")


def originals_have_pillar_verts(data):
    objects = (data or {}).get("objects") or {}
    return all((objects.get(name) or {}).get("verts") for name in PILLAR_A)


def capture_a_pillar_originals():
    path = stored_originals_path()
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not originals_have_pillar_verts(data):
            raise RuntimeError(
                "a_pillar_originals.json exists but is missing A-pillar verts; "
                "refusing to recapture blindly"
            )
        log(f"Preserving stored A-pillar originals -> {path}")
        return data
    data = {"objects": {}, "captured_at": datetime.now().isoformat(), "filepath": bpy.data.filepath}
    for name in PILLAR_A:
        obj = bpy.data.objects[name]
        data["objects"][name] = {
            "location": vec3(obj.location),
            "rotation_euler": [float(a) for a in obj.rotation_euler],
            "scale": vec3(obj.scale),
            "verts": [vec3(v.co) for v in obj.data.vertices],
        }
    write_json(path, data)
    log(f"Captured A-pillar originals once -> {path}")
    return data


def restore_a_pillar_originals(data):
    ensure_object_mode()
    for name in PILLAR_A:
        rec = data["objects"][name]
        obj = bpy.data.objects[name]
        make_mesh_single_user(obj)
        if len(rec["verts"]) != len(obj.data.vertices):
            raise RuntimeError(f"{name} vertex count changed since original capture")
        obj.location = Vector(rec["location"])
        obj.rotation_euler = rec["rotation_euler"]
        obj.scale = Vector(rec["scale"])
        for vert, xyz in zip(obj.data.vertices, rec["verts"]):
            vert.co = Vector(xyz)
        obj.data.update()


def apply_upper_displacement(obj, lower, upper, disp_upper):
    """Keep lower attachment fixed. Interpolate world displacement along BASE height."""
    ensure_object_mode()
    make_mesh_single_user(obj)
    matrix = obj.matrix_world.copy()
    inverse = matrix.inverted()
    height = upper.z - lower.z
    if abs(height) < 0.05:
        raise RuntimeError(f"{obj.name} height too small")
    log(
        f"{obj.name} editing BASE mesh in world space; "
        f"preserving modifiers={[m.type for m in obj.modifiers]}"
    )
    for vert in obj.data.vertices:
        point = matrix @ vert.co
        t = (point.z - lower.z) / height
        t = 0.0 if t < 0.0 else 1.0 if t > 1.0 else t
        vert.co = inverse @ (point + disp_upper * t)
    obj.data.update()
    return height


def preflight_a_pillar_modifiers():
    problems = []
    for name in PILLAR_A:
        obj = bpy.data.objects.get(name)
        if obj is None:
            problems.append(f"Missing {name}")
            continue
        ok, why = pillar_topology_ok(obj)
        if not ok:
            problems.append(f"{name}: {why}")
        else:
            log(
                f"{name} preflight modifiers={[m.type for m in obj.modifiers]} "
                f"users={obj.data.users} -> {why}"
            )
    if problems:
        raise RuntimeError(
            "A-pillar preflight failed (no vertex writes): " + "; ".join(problems)
        )


def preflight_a_pillar_endpoints():
    problems = []
    for name in PILLAR_A:
        obj = bpy.data.objects[name]
        pts = base_world_verts(obj)
        if cluster_by_z(pts, "lower") is None or cluster_by_z(pts, "upper") is None:
            problems.append(f"{name}: ambiguous upper/lower endpoints")
    if problems:
        raise RuntimeError("A-pillar endpoint preflight failed: " + "; ".join(problems))


def measure_pillar_pair():
    greenhouse = bpy.data.objects.get(GREENHOUSE)
    if greenhouse is None:
        raise RuntimeError("Missing panoramic_glass_greenhouse")
    gh_pts = evaluated_world_verts(greenhouse)
    measures = {}
    for name in PILLAR_A:
        obj = bpy.data.objects.get(name)
        if obj is None:
            raise RuntimeError(f"Missing {name}")
        ok, why = pillar_topology_ok(obj)
        if not ok:
            raise RuntimeError(f"{name}: {why}")
        pts = base_world_verts(obj)
        lower = cluster_by_z(pts, "lower")
        upper = cluster_by_z(pts, "upper")
        if lower is None or upper is None:
            raise RuntimeError(f"{name}: ambiguous upper/lower endpoints")
        zmin = min(p.z for p in pts)
        zmax = max(p.z for p in pts)
        h = zmax - zmin
        gh_lower, n_lo = greenhouse_connection(
            gh_pts, lower["center"].x, zmin, zmin + h * HEIGHT_FRAC, "lower"
        )
        gh_upper, n_up = greenhouse_connection(
            gh_pts, upper["center"].x, zmax - h * HEIGHT_FRAC, zmax, "upper"
        )
        measures[name] = {
            "lower": lower["center"],
            "upper": upper["center"],
            "lower_span": cluster_xy_span(lower),
            "upper_span": cluster_xy_span(upper),
            "gh_lower": gh_lower,
            "gh_upper": gh_upper,
            "gh_lower_count": n_lo,
            "gh_upper_count": n_up,
            "lower_disp": Vector((0.0, 0.0, 0.0)),
            "upper_disp": gh_upper - upper["center"],
        }
        log(
            f"{name} BASE LOWER world={vec3(lower['center'])} gh={vec3(gh_lower)} "
            f"disp=(fixed 0,0,0)"
        )
        log(
            f"{name} BASE UPPER world={vec3(upper['center'])} gh={vec3(gh_upper)} "
            f"disp_m={vec3(measures[name]['upper_disp'])}"
        )
    return measures


def collect_a_pillar_failures(measures, after_base, before_eval, after_eval):
    failures = []
    d_after = after_base["pillar_a_dside"]
    p_after = after_base["pillar_a_pside"]
    if abs(d_after["upper"].x + p_after["upper"].x) > SYMMETRY_TOL:
        failures.append("base upper X not symmetric about 0")
    if abs(d_after["upper"].y - p_after["upper"].y) > SYMMETRY_TOL:
        failures.append("base upper Y not symmetric")
    if abs(d_after["lower"].x + p_after["lower"].x) > SYMMETRY_TOL:
        failures.append("base lower X not symmetric about 0")
    for name, rec in after_base.items():
        orig_lower = measures[name]["lower"]
        if (rec["lower"] - orig_lower).length > SYMMETRY_TOL:
            failures.append(f"{name} lower attachment moved")
        expected_upper = measures[name]["upper"] + measures[name]["upper_disp"]
        if (rec["upper"] - expected_upper).length > SYMMETRY_TOL:
            failures.append(f"{name} base upper missed planned displacement")
        for label, before_span, after_span in (
            ("lower", measures[name]["lower_span"], rec["lower_span"]),
            ("upper", measures[name]["upper_span"], rec["upper_span"]),
        ):
            if before_span is None or after_span is None:
                failures.append(f"{name} {label} thickness unmeasurable")
                continue
            if abs(after_span[0] - before_span[0]) > THICKNESS_TOL:
                failures.append(f"{name} {label} X thickness changed")
            if abs(after_span[1] - before_span[1]) > THICKNESS_TOL:
                failures.append(f"{name} {label} Y thickness changed")

    d_eval = after_eval["pillar_a_dside"]
    p_eval = after_eval["pillar_a_pside"]
    if d_eval["upper"] is None or p_eval["upper"] is None:
        failures.append("evaluated upper endpoints missing (bevel artifact)")
    else:
        if abs(d_eval["upper"]["center"].x + p_eval["upper"]["center"].x) > SYMMETRY_TOL:
            failures.append("evaluated upper X not symmetric about 0")
        if abs(d_eval["upper"]["center"].y - p_eval["upper"]["center"].y) > SYMMETRY_TOL:
            failures.append("evaluated upper Y not symmetric")
    if d_eval["lower"] is None or p_eval["lower"] is None:
        failures.append("evaluated lower endpoints missing (bevel artifact)")
    elif abs(d_eval["lower"]["center"].x + p_eval["lower"]["center"].x) > SYMMETRY_TOL:
        failures.append("evaluated lower X not symmetric about 0")
    if aabb_overlap(d_eval, p_eval):
        failures.append("evaluated A-pillars intersect each other")

    for name in PILLAR_A:
        before = before_eval[name]
        after = after_eval[name]
        slack = max(after["bevel_slack"], before["bevel_slack"], SYMMETRY_TOL)
        if after["bevel_state"] != before["bevel_state"]:
            failures.append(f"{name} bevel settings changed")
        if after["has_nan"]:
            failures.append(f"{name} evaluated verts contain NaN (bevel artifact)")
        if after["n_polys"] < 1 or after["n_verts"] < 4:
            failures.append(f"{name} evaluated mesh collapsed")
        if after["n_verts"] < max(4, int(before["n_verts"] * 0.85)):
            failures.append(f"{name} evaluated vert count dropped (bevel artifact)")
        if after["degenerate"] > before["degenerate"]:
            failures.append(f"{name} bevel produced degenerate faces")
        if before["min"] is not None and after["min"] is not None:
            before_size = before["max"] - before["min"]
            after_size = after["max"] - after["min"]
            if (after_size - before_size).length > max(0.05, slack * 4.0):
                failures.append(f"{name} evaluated bounds exploded (bevel artifact)")
        if before["lower"] is None or after["lower"] is None:
            failures.append(f"{name} evaluated belt cluster missing")
        elif (after["lower"]["center"] - before["lower"]["center"]).length > SYMMETRY_TOL + slack * 0.25:
            failures.append(f"{name} evaluated belt attachment moved")
        else:
            before_span = cluster_xy_span(before["lower"])
            after_span = cluster_xy_span(after["lower"])
            if before_span and after_span:
                if abs(after_span[0] - before_span[0]) > THICKNESS_TOL + slack:
                    failures.append(f"{name} evaluated belt X thickness changed")
                if abs(after_span[1] - before_span[1]) > THICKNESS_TOL + slack:
                    failures.append(f"{name} evaluated belt Y thickness changed")
        if before["upper"] is None or after["upper"] is None:
            failures.append(f"{name} evaluated roof cluster missing")
        else:
            planned = measures[name]["upper_disp"]
            moved = after["upper"]["center"] - before["upper"]["center"]
            follow_tol = SYMMETRY_TOL + slack + planned.length * HEIGHT_FRAC
            if (moved - planned).length > follow_tol:
                failures.append(f"{name} evaluated roof did not follow planned displacement")
            gh_upper = measures[name]["gh_upper"]
            contact_after = (after["upper"]["center"] - gh_upper).length
            contact_before = (before["upper"]["center"] - gh_upper).length
            if contact_after > contact_before + SYMMETRY_TOL + slack:
                failures.append(f"{name} evaluated roof contact worsened ({contact_after:.4f}m)")
    return failures


def symmetrize_design(measures):
    dside = measures["pillar_a_dside"]
    pside = measures["pillar_a_pside"]
    # One world-space design: average Y/Z, mirror X. Never copy local vertex offsets.
    dy = 0.5 * (dside["upper_disp"].y + pside["upper_disp"].y)
    dz = 0.5 * (dside["upper_disp"].z + pside["upper_disp"].z)
    dx_dside = 0.5 * (dside["upper_disp"].x - pside["upper_disp"].x)
    dside_disp = Vector((dx_dside, dy, dz))
    pside_disp = Vector((-dx_dside, dy, dz))
    log(
        f"SYMMETRY DESIGN upper_disp_m dside={vec3(dside_disp)} pside={vec3(pside_disp)}"
    )
    measures["pillar_a_dside"]["upper_disp"] = dside_disp
    measures["pillar_a_pside"]["upper_disp"] = pside_disp
    return measures


def set_opaque_solid_render():
    scene = scn()
    scene.render.engine = "BLENDER_WORKBENCH"
    if scene.render.engine != "BLENDER_WORKBENCH":
        raise RuntimeError(f"Workbench unavailable: {scene.render.engine}")
    shading = scene.display.shading
    if hasattr(shading, "type"):
        shading.type = "SOLID"
    if hasattr(shading, "show_xray"):
        shading.show_xray = False
    if hasattr(shading, "color_type"):
        shading.color_type = "SINGLE"
    if hasattr(shading, "single_color"):
        shading.single_color = (0.55, 0.55, 0.55)
    scene.render.resolution_x = 960
    scene.render.resolution_y = 540
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.use_stamp = False


def render_review_views(prefix):
    set_opaque_solid_render()
    points = []
    for obj in bpy.context.view_layer.objects:
        if obj.type != "MESH" or not in_qcomet_collection(obj) or is_reference_object(obj):
            continue
        if obj.hide_get() or obj.hide_viewport:
            continue
        points.extend(evaluated_world_verts(obj))
    if not points:
        raise RuntimeError("No visible Q Comet verts to frame for evidence")
    mins = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
    maxs = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
    center = (mins + maxs) * 0.5
    size = maxs - mins
    dist = max(size) * 3.0
    cam = bpy.data.objects.get("QCOMET_REVIEW_CAMERA")
    if cam is None:
        data = bpy.data.cameras.new("QCOMET_REVIEW_CAMERA")
        cam = bpy.data.objects.new("QCOMET_REVIEW_CAMERA", data)
        scn().collection.objects.link(cam)
    cam.data.type = "ORTHO"
    scn().camera = cam
    views = {
        "front": ((center.x, center.y + dist, center.z), max(size.x, size.z) * 1.12),
        "side": ((center.x + dist, center.y, center.z), max(size.y, size.z) * 1.12),
        "three_quarter": (
            (center.x + dist * 0.72, center.y + dist * 0.85, center.z + dist * 0.42),
            max(size) * 1.12,
        ),
    }
    written = {}
    for name, (location, scale) in views.items():
        cam.location = Vector(location)
        cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()
        cam.data.ortho_scale = scale
        path = os.path.join(evidence_dir(), f"{prefix}_{name}.png")
        scn().render.filepath = path
        bpy.ops.render.render(write_still=True)
        if not os.path.isfile(path) or os.path.getsize(path) < 1000:
            raise RuntimeError(f"Evidence failed: {path}")
        written[name] = path
        log(f"evidence {name} -> {path}")
    return written


def step_apply_a_pillars(flags):
    ok, reason = checkpoint_is_verified(
        {
            "checkpoint_verified": bool(scn().get("qcomet_checkpoint_verified", False)),
            "checkpoint_path": scn().get("qcomet_interactive_checkpoint", ""),
            "working_path": scn().get("qcomet_working_file", bpy.data.filepath),
        }
    )
    if not ok:
        raise RuntimeError(f"Refuse A-pillar edits until checkpoint is verified: {reason}")

    for name in ("pillar_c_dside", "pillar_c_pside", "pillar_b_dside", "drip_trim_dside"):
        obj = flags["objects"].get(name) if isinstance(flags.get("objects"), dict) else None
        if obj and obj.get("custom"):
            log(f"NOTE {name} still has older custom flags {obj['custom']}; this step will not edit it")

    if scn().get("qcomet_a_pillars_complete") and os.path.isfile(stored_originals_path()):
        log("A-pillars already marked complete. Restoring originals, then re-applying (repeat-safe).")

    preflight_a_pillar_modifiers()

    originals = capture_a_pillar_originals()
    restore_a_pillar_originals(originals)
    bpy.context.view_layer.update()
    preflight_a_pillar_endpoints()

    measures = measure_pillar_pair()
    measures = symmetrize_design(measures)
    plan = {
        name: {
            "lower_world": vec3(rec["lower"]),
            "upper_world": vec3(rec["upper"]),
            "greenhouse_lower": vec3(rec["gh_lower"]),
            "greenhouse_upper": vec3(rec["gh_upper"]),
            "proposed_lower_disp_m": [0.0, 0.0, 0.0],
            "proposed_upper_disp_m": vec3(rec["upper_disp"]),
            "modifiers": snapshot_bevel_state(bpy.data.objects[name]),
        }
        for name, rec in measures.items()
    }
    write_json(os.path.join(evidence_dir(), "a_pillar_plan.json"), plan)
    log("Proposed A-pillar upper displacements are in a_pillar_plan.json (meters)")

    before_eval = {name: evaluated_pillar_report(bpy.data.objects[name]) for name in PILLAR_A}

    try:
        for name, rec in measures.items():
            apply_upper_displacement(
                bpy.data.objects[name], rec["lower"], rec["upper"], rec["upper_disp"]
            )
        bpy.context.view_layer.update()
        after_base = measure_pillar_pair()
        after_eval = {name: evaluated_pillar_report(bpy.data.objects[name]) for name in PILLAR_A}
        failures = collect_a_pillar_failures(measures, after_base, before_eval, after_eval)
    except Exception as exc:
        restore_a_pillar_originals(originals)
        bpy.context.view_layer.update()
        payload = {
            "valid": False,
            "reason": [str(exc)],
            "restored": True,
            "index_advanced": False,
            "a_pillar_marker": bool(scn().get("qcomet_a_pillars_complete", False)),
            "recovery_checkpoint": scn().get("qcomet_interactive_checkpoint"),
        }
        write_report("03_apply_a_pillars", payload)
        raise RuntimeError(
            "A-pillar deformation failed; both pillars restored from originals. "
            "Index not advanced. " + str(exc)
        ) from exc

    if failures:
        restore_a_pillar_originals(originals)
        bpy.context.view_layer.update()
        payload = {
            "valid": False,
            "reason": failures,
            "restored": True,
            "index_advanced": False,
            "a_pillar_marker": bool(scn().get("qcomet_a_pillars_complete", False)),
            "recovery_checkpoint": scn().get("qcomet_interactive_checkpoint"),
        }
        write_report("03_apply_a_pillars", payload)
        raise RuntimeError(
            "A-pillar validation failed; both pillars restored from originals. "
            "Index not advanced. " + "; ".join(failures)
        )

    evidence = render_review_views("03_a_pillars")
    scn()["qcomet_a_pillars_complete"] = True
    record_scene_progress("apply_a_pillars", 3)
    result = bpy.ops.wm.save_mainfile()
    op_finished(result, "Save after A-pillars")
    payload = {
        "valid": True,
        "plan": plan,
        "evidence": evidence,
        "unchanged": ["C-pillars", "B-pillars", "glass", "materials", "drip rails"],
        "approval": "not_approved",
        "completed_step": "apply_a_pillars",
        "bevel_preserved": {
            name: snapshot_bevel_state(bpy.data.objects[name]) for name in PILLAR_A
        },
        "stop": "Inspect side/front/three-quarter locally. Do not continue to C-pillars yet.",
    }
    write_report("03_apply_a_pillars", payload)
    log("A-PILLARS APPLIED. STOP FOR LOCAL REVIEW. C/B/glass/drip untouched. BEVEL preserved.")
    return payload


def next_step_name(index):
    if index < 0:
        index = 0
    if index >= len(STEPS):
        return None
    return STEPS[index]


def resolve_index(flags):
    """Honor persisted index. Do not reset it. Re-run a step only if files/flags disagree."""
    index = int(flags["interactive_index"])
    completed = flags["completed_step"]
    verified, _reason = checkpoint_is_verified(flags)
    if verified and index == 0 and completed in {"", "checkpoint_and_retarget"}:
        index = 1
    if completed == "checkpoint_and_retarget" and index < 1:
        index = 1
    if completed == "hide_refs_and_frame" and index < 2:
        index = 2
    if completed == "apply_a_pillars" and index < 3:
        index = 3
    # Older scripts used extra steps (inspect, C-pillars, drip). Never execute those.
    if completed in {
        "inspect_measure_propose",
        "apply_measured_pillar_endpoints",
        "drip_rail_decision",
        "review_evidence_report",
        "hide_refs_opaque_solid",
    }:
        log(f"Older completed_step={completed!r} index={index}. Mapping onto the reduced sequence.")
        if completed in {"hide_refs_opaque_solid", "inspect_measure_propose"}:
            index = max(index, 2)
        elif completed in {"apply_measured_pillar_endpoints", "drip_rail_decision", "review_evidence_report"}:
            log("Older script may already have edited geometry. A-pillar step is repeat-safe from stored originals.")
            index = 2
    return index


def main():
    ensure_gui()
    if bpy.data.objects.get("chassis") is None:
        raise RuntimeError("No chassis in this scene. Wrong file.")
    flags = audit_legacy_state()
    index = resolve_index(flags)
    log(f"Resolved next index={index} ({next_step_name(index) or 'DONE'})")

    if index >= len(STEPS):
        log("STOP. A-pillar checkpoint is already complete. Review evidence locally. Not auto-approved.")
        return

    name = STEPS[index]
    if name == "apply_a_pillars":
        ok, reason = checkpoint_is_verified(
            {
                "checkpoint_verified": bool(scn().get("qcomet_checkpoint_verified", False)),
                "checkpoint_path": scn().get("qcomet_interactive_checkpoint", ""),
                "working_path": scn().get("qcomet_working_file", bpy.data.filepath),
            }
        )
        if not ok:
            log(f"Blocking A-pillar edit: {reason}")
            raise RuntimeError(f"Checkpoint/working retarget not verified: {reason}")

    log(f"RUN {index + 1}/{len(STEPS)} {name}")
    if name == "checkpoint_and_retarget":
        step_checkpoint_and_retarget(flags)
    elif name == "hide_refs_and_frame":
        step_hide_refs_and_frame(flags)
    elif name == "apply_a_pillars":
        step_apply_a_pillars(flags)
    else:
        raise RuntimeError(f"Unknown step {name}")

    nxt = next_step_name(int(scn().get("qcomet_interactive_index", index + 1)))
    if nxt:
        log(f"DONE {name}. Next click: {nxt}")
    else:
        log("DONE. STOP FOR LOCAL SIDE/FRONT/THREE-QUARTER REVIEW. Not approved.")


if __name__ == "__main__":
    main()
