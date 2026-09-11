"""Q Comet v016: production UV pass on top of the v015 Sollumz authoring file.

Input : qcomet_sollumz_v015.blend (must be the active file; never modified)
Output: qcomet_sollumz_v016.blend + review_v016/uv_validation.json + readiness.md

What it does
- Dash text (7 FONT-derived meshes): the text-to-mesh conversion left a layer
  called 'UVMap', so Sollumz saw no 'UVMap 0'. Rename it, then write an
  aspect-preserving planar unwrap in the text's own dash plane (normal = the
  slab's thin axis, u = screen-right for the driver, v = up) into UVMap 0 and
  UVMap 1, on the visible authoring mesh, the exp_ model and its three LODs.
- Glass (15 vehglass meshes incl. phys_ twins): vehicle_vehglass samples
  TexCoord0..2. Add 'UVMap 2' as a per-pane 0..1 planar projection in the
  pane's own plane (u = horizontal tangent, v = up; roof glass uses +X/+Y) so
  crack/damage lookups cover each pane exactly once. UVMap 0/1 are untouched.
- Re-runs the in-memory Sollumz fragment build (same audit as v015) and
  records the remaining Sollumz warnings. No .yft/.ytd/.ybn is written.
"""
from __future__ import annotations

import contextlib
import importlib
import io
import json
import time
import traceback
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'vehicles/qcomet/source/blender'
REVIEW = OUTPUT / 'review_v016'
INPUT_NAME = 'qcomet_sollumz_v015.blend'
OUTPUT_NAME = 'qcomet_sollumz_v016.blend'
PACKAGE = 'bl_ext.sollumz_org.sollumz'
PROPS = importlib.import_module(PACKAGE + '.sollumz_properties')
LOD = PROPS.LODLevel
TEXT_SOURCES = ('dash_speed', 'dash_battery', 'dash_touch_label')
GLASS_SOURCES = ('window_', 'windscreen', 'glass_', 'panoramic_glass')
UP = Vector((0, 0, 1))
REPORT = {'input': INPUT_NAME, 'output': OUTPUT_NAME, 'text': {}, 'glass': {}, 'audit': {}, 'warnings': [], 'blockers': []}


def lod_meshes(obj):
    result = []
    for level in (LOD.MEDIUM, LOD.LOW, LOD.VERYLOW):
        mesh = obj.sz_lods.get_lod(level).mesh
        if mesh is not None and mesh != obj.data:
            result.append(mesh)
    return result


def extents(mesh):
    minimum = Vector([min(v.co[i] for v in mesh.vertices) for i in range(3)])
    maximum = Vector([max(v.co[i] for v in mesh.vertices) for i in range(3)])
    return minimum, maximum


def tangent_frame(normal):
    normal = normal.normalized()
    if abs(normal.dot(UP)) > 0.9:
        u = Vector((1, 0, 0))
    else:
        u = UP.cross(normal)
    u = (u - normal * u.dot(normal)).normalized()
    v = normal.cross(u).normalized()
    return normal, u, v


def text_frame(mesh):
    """FONT slabs have front/back faces that cancel in an area-weighted normal,
    so take the slab's thin axis instead and point it toward the cabin."""
    minimum, maximum = extents(mesh)
    size = maximum - minimum
    axis = min(range(3), key=lambda i: size[i])
    center = (minimum + maximum) / 2
    if axis == 1:
        normal = Vector((0, -1, 0))
    elif axis == 0:
        normal = Vector((-1 if center.x > 0 else 1, 0, 0))
    else:
        normal = UP.copy()
    return tangent_frame(normal), center


CABIN_REFERENCE = Vector((0, 0, 0.9))


def glass_frame(mesh):
    """Glass panes are solidified slabs: front and back faces cancel in an
    area-weighted normal and the rim faces win, which squashed the windscreen
    in the first v016 pass. Fit the pane plane with a principal-component
    analysis of the vertices instead (least-variance axis = pane normal) and
    point the normal away from the cabin so u/v read correctly from outside."""
    import numpy as np
    points = np.array([vertex.co[:] for vertex in mesh.vertices], dtype=np.float64)
    center = points.mean(axis=0)
    covariance = np.cov((points - center).T)
    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    normal = Vector(eigenvectors[:, int(np.argmin(eigenvalues))].tolist())
    center = Vector(center.tolist())
    if normal.dot(center - CABIN_REFERENCE) < 0:
        normal = -normal
    return tangent_frame(normal), center


def planar_mapping(reference_mesh, frame, center, keep_aspect, padding):
    _, u, v = frame
    coords = [((vertex.co - center).dot(u), (vertex.co - center).dot(v)) for vertex in reference_mesh.vertices]
    s_min, s_max = min(c[0] for c in coords), max(c[0] for c in coords)
    t_min, t_max = min(c[1] for c in coords), max(c[1] for c in coords)
    s_span, t_span = max(s_max - s_min, 1e-6), max(t_max - t_min, 1e-6)
    inner = 1 - 2 * padding
    if keep_aspect:
        scale = inner / max(s_span, t_span)
        s_scale = t_scale = scale
        s_off = 0.5 - s_span * scale / 2
        t_off = 0.5 - t_span * scale / 2
    else:
        s_scale, t_scale = inner / s_span, inner / t_span
        s_off = t_off = padding

    def mapper(co):
        s = (co - center).dot(u)
        t = (co - center).dot(v)
        return ((s - s_min) * s_scale + s_off, (t - t_min) * t_scale + t_off)
    return mapper, {'u_axis': [round(x, 4) for x in u], 'v_axis': [round(x, 4) for x in v], 'plane_span_m': [round(s_span, 4), round(t_span, 4)]}


def write_layer(mesh, layer_name, mapper):
    layer = mesh.uv_layers.get(layer_name) or mesh.uv_layers.new(name=layer_name)
    for polygon in mesh.polygons:
        for loop_index in polygon.loop_indices:
            layer.data[loop_index].uv = mapper(mesh.vertices[mesh.loops[loop_index].vertex_index].co)
    return layer


def uv_bounds(mesh, layer_name):
    layer = mesh.uv_layers[layer_name]
    us = [d.uv[0] for d in layer.data]
    vs = [d.uv[1] for d in layer.data]
    return [round(min(us), 4), round(min(vs), 4), round(max(us), 4), round(max(vs), 4)]


def rename_legacy_layer(mesh):
    legacy = mesh.uv_layers.get('UVMap')
    if legacy is not None and mesh.uv_layers.get('UVMap 0') is None:
        legacy.name = 'UVMap 0'
        return True
    return False


def process_text():
    for source_name in sorted(o.name for o in bpy.data.objects if o.name.startswith(TEXT_SOURCES) and not o.name.startswith(('exp_', 'phys_'))):
        authoring = bpy.data.objects[source_name]
        model = bpy.data.objects.get('exp_' + source_name)
        if model is None or model.type != 'MESH':
            REPORT['blockers'].append(f'exp_{source_name} missing')
            continue
        frame, center = text_frame(model.data)
        mapper, info = planar_mapping(model.data, frame, center, keep_aspect=True, padding=0.02)
        touched = {}
        for mesh in [model.data] + lod_meshes(model):
            renamed = rename_legacy_layer(mesh)
            for layer_name in ('UVMap 0', 'UVMap 1'):
                write_layer(mesh, layer_name, mapper)
            touched[mesh.name] = {'renamed_legacy_UVMap': renamed, 'layers': [l.name for l in mesh.uv_layers], 'uv0_bounds': uv_bounds(mesh, 'UVMap 0')}
        # Visible authoring copy shares the rig-space coordinates of exp_ (both are rest pose, chassis bone at origin).
        renamed = rename_legacy_layer(authoring.data)
        write_layer(authoring.data, 'UVMap 0', mapper)
        touched[authoring.data.name] = {'authoring': True, 'renamed_legacy_UVMap': renamed, 'layers': [l.name for l in authoring.data.uv_layers], 'uv0_bounds': uv_bounds(authoring.data, 'UVMap 0')}
        REPORT['text'][source_name] = {'frame': info, 'meshes': touched}


def process_glass():
    families = {}
    for obj in bpy.data.objects:
        if obj.type != 'MESH' or not obj.name.startswith(('exp_', 'phys_')):
            continue
        source_name = obj.get('qcomet_source_object') or obj.name.split('_', 1)[1]
        if source_name.startswith(GLASS_SOURCES):
            families[obj.name] = obj
    rig = bpy.data.objects['qcomet']
    # Visual exp_ meshes live in rig space; phys_ twins are the same geometry in
    # bone-local space. Fit the plane once on the exp_ mesh and push phys_
    # vertices through the bone matrix so both twins get identical UVMap 2.
    for name, obj in sorted(families.items()):
        if name.startswith('exp_'):
            frame, center = glass_frame(obj.data)
            mapper, info = planar_mapping(obj.data, frame, center, keep_aspect=False, padding=0.0)
            space = 'rig'
        else:
            visual = families.get('exp_' + name[len('phys_'):])
            if visual is None:
                REPORT['blockers'].append(f'{name} has no exp_ twin to take its UV frame from')
                continue
            frame, center = glass_frame(visual.data)
            rig_mapper, info = planar_mapping(visual.data, frame, center, keep_aspect=False, padding=0.0)
            # Neither twin carries the bone name; the visible authoring object does (set by the v015 build).
            bone_matrix = rig.data.bones[bpy.data.objects[name[len('phys_'):]]['qcomet_rig_bone']].matrix_local
            mapper = lambda co, _m=rig_mapper, _b=bone_matrix: _m(_b @ co)
            space = 'bone-local via ' + str(bone_matrix.translation[:])
        touched = {}
        for mesh in [obj.data] + lod_meshes(obj):
            write_layer(mesh, 'UVMap 2', mapper)
            touched[mesh.name] = {'layers': [l.name for l in mesh.uv_layers], 'uv2_bounds': uv_bounds(mesh, 'UVMap 2')}
        REPORT['glass'][name] = {'frame': info, 'space': space, 'normal': [round(x, 4) for x in frame[0]], 'meshes': touched}


def audit(rig):
    LOGGER = importlib.import_module(PACKAGE + '.logger')
    logs = []

    class AuditLogger(LOGGER.LoggerBase):
        def do_log(self, message, level):
            logs.append((str(level), str(message)))
    context = importlib.import_module(PACKAGE + '.iecontext')
    gta = importlib.import_module('szio.gta5')
    exporter = importlib.import_module(PACKAGE + '.yft.yftexport')
    settings = context.ExportSettings(targets=(gta.AssetTarget(gta.AssetFormat.CWXML, gta.AssetVersion.GEN8),), apply_transforms=False)
    buffer = io.StringIO()
    result = {'native_asset_constructed': False}
    try:
        with LOGGER.use_logger(AuditLogger()), context.export_context_scope(context.ExportContext('qcomet', settings)), contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
            asset, _high = exporter.create_fragment_asset(rig, out_embedded_textures=[], out_hd_textures={})
        if asset is not None and asset.drawable is not None:
            result.update({
                'native_asset_constructed': bool(asset.drawable.models),
                'exported_skeleton_bones': len(asset.drawable.skeleton.bones),
                'exported_models_by_lod': {str(level): len(models) for level, models in asset.drawable.models.items()},
                'physics_children': len(asset.physics.lod1.children) if asset.physics else 0,
                'generated_vehicle_windows': len(getattr(asset, 'vehicle_windows', []) or []),
            })
        else:
            REPORT['blockers'].append('Sollumz could not construct the fragment asset.')
    except Exception:
        REPORT['blockers'].append('Native export audit raised an exception; see native_export_audit.log.')
        buffer.write(traceback.format_exc())
    finally:
        rig.data.pose_position = 'POSE'
    errors = [m for level, m in logs if 'ERROR' in level.upper()]
    warnings = [m for level, m in logs if 'ERROR' not in level.upper()]
    REPORT['blockers'].extend(errors)
    REPORT['warnings'].extend(warnings)
    result['sollumz_log_entries'] = len(logs)
    result['sollumz_uv_warnings'] = sum('missing UV maps' in m for m in warnings)
    result['sollumz_color_warnings'] = sum('missing color attributes' in m for m in warnings)
    (REVIEW / 'native_export_audit.log').write_text('\n'.join(f'{level}: {message}' for level, message in logs) + '\n' + buffer.getvalue(), encoding='utf-8')
    REPORT['audit'] = result


def main():
    active = Path(bpy.data.filepath).name
    if active != INPUT_NAME:
        raise RuntimeError(f'Active file must be {INPUT_NAME} (active is {active!r}).')
    if bpy.data.is_dirty:
        raise RuntimeError('Active file has unsaved changes; reload it first.')
    REVIEW.mkdir(exist_ok=True)
    started = time.time()
    window = bpy.context.window_manager.windows[0]
    with bpy.context.temp_override(window=window):
        process_text()
        process_glass()
        rig = bpy.data.objects['qcomet']
        assert rig.type == 'ARMATURE'
        audit(rig)
        scene = bpy.context.scene
        scene['qcomet_sollumz_revision'] = 16
        scene['qcomet_uv_status'] = 'v016: dash text planar UV0/UV1, glass UVMap 2 per pane; glass UV0/UV1 and body projection UVs still proxies.'
        text = bpy.data.texts.get(Path(__file__).name) or bpy.data.texts.new(Path(__file__).name)
        text.clear()
        text.write(Path(__file__).read_text(encoding='utf-8'))
        prefs = bpy.context.preferences.filepaths
        saved_versions = prefs.save_version
        prefs.save_version = 0
        try:
            bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT / OUTPUT_NAME))
        finally:
            prefs.save_version = saved_versions
    REPORT['elapsed_s'] = round(time.time() - started, 1)
    REPORT['saved'] = Path(bpy.data.filepath).name == OUTPUT_NAME
    (REVIEW / 'uv_validation.json').write_text(json.dumps(REPORT, indent=2), encoding='utf-8')
    status = {'saved': REPORT['saved'], 'file': OUTPUT_NAME, 'text_meshes': len(REPORT['text']), 'glass_meshes': len(REPORT['glass']), 'native_audit': REPORT['audit'].get('native_asset_constructed', False), 'sollumz_uv_warnings': REPORT['audit'].get('sollumz_uv_warnings'), 'blocker_count': len(REPORT['blockers']), 'game_ready': False}
    (REVIEW / 'job_status.json').write_text(json.dumps(status), encoding='utf-8')
    print(json.dumps(status))


if __name__ == '__main__':
    main()
