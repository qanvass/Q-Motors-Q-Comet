from __future__ import annotations

import contextlib
import importlib
import inspect
import io
import json
import math
import traceback
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'vehicles/qcomet/source/blender'
REVIEW = OUTPUT / 'review_v015'
# v013 superseded v014 as the input: qcomet_vehicle_v013.blend's own completion
# report (review_v013/milestone123_completion_report.json) declares M1-M3 rig
# work complete (cabin + hinging + lights + collision), and it was saved after
# both qcomet_cabin_v014.blend and the last failed v015 attempt. Accept either
# so a stale guard never blocks the actually-newer file again; prefer v013 when
# both are on disk since it is the more complete milestone.
ACCEPTED_INPUTS = ('qcomet_vehicle_v013.blend', 'qcomet_cabin_v014.blend')
PACKAGE = 'bl_ext.sollumz_org.sollumz'
PROPS = importlib.import_module(PACKAGE + '.sollumz_properties')
HELPERS = importlib.import_module(PACKAGE + '.tools.blenderhelper')
DRAWABLE = importlib.import_module(PACKAGE + '.tools.drawablehelper')
SHADERS = importlib.import_module(PACKAGE + '.ydr.shader_materials_v2')
COLLISIONS = importlib.import_module(PACKAGE + '.ybn.collision_materials')


def _patch_sollumz_shader_config():
    """Sollumz 2.9 `get_shader_config` reads `texture` in the unknown-sampler
    branch without initializing it. Vehicle shaders hit that path and abort
    material conversion. Keep the fix in this recipe; do not edit the addon."""
    original = SHADERS.get_shader_config
    if getattr(original, '_qcomet_texture_init_patch', False):
        return
    source = inspect.getsource(original)
    if '    texture = None\n' in source:
        original._qcomet_texture_init_patch = True
        return
    source = source.replace(
        '    is_distance_map = False\n',
        '    is_distance_map = False\n    texture = None\n',
        1,
    )
    namespace = dict(vars(SHADERS))
    exec(compile(source, '<qcomet_sollumz_shader_patch>', 'exec'), namespace)
    patched = namespace['get_shader_config']
    patched._qcomet_texture_init_patch = True
    SHADERS.get_shader_config = patched


_patch_sollumz_shader_config()


def _patch_sollumz_compiler_caches():
    """Sollumz 2.9 `shared.shader_expr.compiler.Compiler` declares its
    compiled_expr/separate_xyz/uv_map caches as class-level dicts and never
    resets them per instance, so every material compiled in a session shares
    node references from earlier materials (and, after a file reload, dead
    ones: the 2026-09-11 01:37 run died with `outputs[0] out of range, size 0`
    on a stale UV node). Give each Compiler fresh caches. In memory only."""
    COMPILER = importlib.import_module(PACKAGE + '.shared.shader_expr.compiler')
    cls = COMPILER.Compiler
    if getattr(cls, '_qcomet_fresh_caches_patch', False):
        return
    original_init = cls.__init__

    def __init__(self, node_tree, root):
        self.compiled_expr_cache = {}
        self.separate_xyz_cache = {}
        self.uv_map_cache = {}
        original_init(self, node_tree, root)

    cls.__init__ = __init__
    cls._qcomet_fresh_caches_patch = True


_patch_sollumz_compiler_caches()
SOLLUM = PROPS.SollumType
LOD = PROPS.LODLevel
# The 2026-09-11 01:31 v015 run crashed mid-rebuild on this Sollumz 2.9.0 bug
# (review_v015/build_error.log); _patch_sollumz_shader_config above is the fix.
SHADER_CONFIG_SHIMMED = getattr(SHADERS.get_shader_config, '_qcomet_texture_init_patch', False)
REPORT = {'game_ready': False, 'binary_assets_written': False, 'phases': {}, 'bindings': {}, 'lods': {}, 'light_ids': {}, 'collision': {}, 'warnings': [], 'blockers': []}
PALETTE = {}
MATERIALS = {}
COLLISION_MATERIALS = {}


def collection(name):
    result = bpy.data.collections.get(name)
    if result is None:
        result = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(result)
    return result


def empty(name, group, kind=None):
    result = bpy.data.objects.new(name, None)
    group.objects.link(result)
    if kind:
        result.sollum_type = kind
    return result


def world_points(obj):
    return [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]


def extents(points):
    return Vector([min(point[axis] for point in points) for axis in range(3)]), Vector([max(point[axis] for point in points) for axis in range(3)])


def baked_mesh(obj):
    dependency_graph = bpy.context.evaluated_depsgraph_get()
    result = bpy.data.meshes.new_from_object(obj.evaluated_get(dependency_graph), preserve_all_data_layers=True, depsgraph=dependency_graph)
    result.transform(obj.matrix_world)
    return result


def bind_group(obj, bone):
    obj.vertex_groups.clear()
    group = obj.vertex_groups.new(name=bone)
    group.add(list(range(len(obj.data.vertices))), 1.0, 'REPLACE')


def skin(obj, rig, bone):
    bind_group(obj, bone)
    modifier = obj.modifiers.new('qcomet_fragment_skin', 'ARMATURE')
    modifier.object = rig
    modifier.use_vertex_groups = True


def repair_door_cards():
    repairs = {}
    for side, sign in [('dside', -1), ('pside', 1)]:
        for end in ['f', 'r']:
            door = bpy.data.objects['door_' + side + '_' + end]
            card = bpy.data.objects['door_card_' + side + '_' + end]
            door_min, door_max = extents(world_points(door))
            card_points = world_points(card)
            card_min, card_max = extents(card_points)
            inverse = door.matrix_world.inverted()
            for vertex, original in zip(card.data.vertices, card_points):
                fraction = (original.y - card_min.y) / (card_max.y - card_min.y)
                position = door_min.y + .035 + fraction * (door_max.y - door_min.y - .070)
                def outer_at(position):
                    hit, point, normal, face = door.ray_cast(inverse @ Vector((sign * 1.5, position, original.z)), inverse.to_3x3() @ Vector((-sign, 0, 0)))
                    return abs((door.matrix_world @ point).x) if hit else .84
                inset = max(.025, min(.15, outer_at(original.y) - abs(original.x)))
                updated = Vector((sign * (outer_at(position) - inset), position, original.z))
                vertex.co = card.matrix_world.inverted() @ updated
            repairs[card.name] = {'old_y': [card_min.y, card_max.y], 'fitted_y': [door_min.y + .035, door_max.y - .035], 'shell_inset_min_m': .025}
    REPORT['door_card_refit'] = repairs


def bone_assignment(name):
    if name in ['chassis', 'center_console', 'armrest', 'console_rotary', 'steering_column'] or name.startswith(('dash_', 'pedal_', 'cupholder_')):
        return 'chassis'
    if name.startswith('seat_'):
        return '_'.join(name.split('_')[:3])
    if name in ['steering', 'steering_qplus']:
        return 'steeringwheel'
    if name in ['windscreen', 'windscreen_r', 'window_lf', 'window_rf', 'window_lr', 'window_rr']:
        return name
    for end in ['lf', 'rf', 'lr', 'rr']:
        if name.endswith('_' + end) and any(token in name for token in ['wheel', 'rim_', 'hub_', 'tire_']):
            return 'wheel_' + end
    for side in ['dside', 'pside']:
        if name.startswith(('mirror_' + side, 'indicator_mirror_' + side)):
            return 'door_' + side + '_f'
        for end in ['f', 'r']:
            if name.endswith(side + '_' + end) and name.startswith(('door_', 'handle_')):
                return 'door_' + side + '_' + end
    if name in ['bonnet']:
        return 'bonnet'
    if name in ['boot', 'boot_ducktail']:
        return 'boot'
    return 'bodyshell'


def light_id(name, horizontal):
    left = horizontal < 0
    if name.startswith('headlight_') and '_blade_' in name or name.startswith('drl_'):
        return 1 if left else 2
    if name == 'tail_bar_brake':
        return 11 if abs(horizontal) < .115 else 9 if left else 10
    if name.startswith(('tail_bar_running', 'tail_quarter_branch_')):
        return 3 if left else 4
    if name.startswith('indicator_'):
        rear = '_rear_' in name
        return (7 if left else 8) if rear else (5 if left else 6)
    if name in ['reverse_dside', 'reverse_pside']:
        return 12 if left else 13
    return 0


def add_indicator(name, center, span, normal, parent_name, group):
    tangent = Vector(span)
    normal = Vector(normal).normalized()
    vertical = tangent.normalized().cross(normal).normalized() * .0018
    center = Vector(center)
    vertices = [center + tangent * end + vertical * height + normal * depth for depth in [-.001, .001] for height in [-1, 1] for end in [-.5, .5]]
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    material = bpy.data.materials.get('qcomet_indicator_amber_v015')
    if material is None:
        material = bpy.data.materials.new('qcomet_indicator_amber_v015')
        material.use_nodes = True
        shader = material.node_tree.nodes.get('Principled BSDF')
        shader.inputs['Base Color'].default_value = (.34, .10, .008, 1)
        shader.inputs['Emission Color'].default_value = (1, .29, .015, 1)
        shader.inputs['Emission Strength'].default_value = 0
    mesh.materials.append(material)
    obj = bpy.data.objects.new(name, mesh)
    group.objects.link(obj)
    obj['qcomet_indicator_source_panel'] = parent_name
    return obj


def palette_image(name, color, data=False):
    key = (tuple(round(value, 5) for value in color), data)
    if key in PALETTE:
        return PALETTE[key]
    image = bpy.data.images.new('qcomet_palette_' + str(len(PALETTE)).zfill(3), width=8, height=8, alpha=True)
    image.generated_color = color
    if data:
        image.colorspace_settings.name = 'Non-Color'
    image.pixels.foreach_set(list(color) * 64)
    image.pack()
    PALETTE[key] = image
    return image


def export_material(original, object_name):
    glass = object_name.startswith(('window_', 'windscreen', 'glass_', 'panoramic_glass'))
    shader = next((node for node in original.node_tree.nodes if node.type == 'BSDF_PRINCIPLED'), None) if original and original.use_nodes else None
    color = tuple(shader.inputs['Base Color'].default_value) if shader else tuple(original.diffuse_color) if original else (.2, .2, .2, 1)
    strength = shader.inputs['Emission Strength'].default_value if shader else 0
    emitting = strength > 0 or object_name.startswith('indicator_') or object_name in ['reverse_dside', 'reverse_pside']
    filename = 'vehicle_vehglass.sps' if glass else 'vehicle_lightsemissive.sps' if emitting else 'vehicle_paint3.sps' if original and original.name == 'Paint_Primary' else 'vehicle_mesh.sps'
    key = (original.name if original else 'fallback', filename)
    if key in MATERIALS:
        return MATERIALS[key]
    result = SHADERS.create_shader(filename)
    result.name = 'qcomet_export_' + str(len(MATERIALS)).zfill(3)
    result['source_authoring_material'] = key[0]
    result['qcomet_texture_status'] = 'Authored palette proxy; production UV/texturing and procedural bakes pending.'
    if emitting and shader:
        color = tuple(shader.inputs['Emission Color'].default_value)
        if object_name in ['reverse_dside', 'reverse_pside']:
            color = (.82, .86, .87, 1)
    for node in result.node_tree.nodes:
        if node.type != 'TEX_IMAGE':
            continue
        lower = node.name.lower()
        data = any(token in lower for token in ['bump', 'normal', 'spec', 'dirt', 'damage'])
        sampled = (.5, .5, 1, 1) if 'bump' in lower or 'normal' in lower else (.20, .20, .20, 1) if 'spec' in lower else (0, 0, 0, 1) if 'dirt' in lower or 'damage' in lower else (*color[:3], .28 if glass else 1)
        node.image = palette_image(node.name, sampled, data)
        node.texture_properties.embedded = True
    MATERIALS[key] = result
    return result


def attributes(mesh, source_name):
    for layer in list(mesh.color_attributes):
        mesh.color_attributes.remove(layer)
    # Sollumz 2.9 names vertex-color layers via tools.meshhelper.get_color_attr_name
    # ('Color 1' for Colour0, 'Color 2' for Colour1); the old 'Colour0' names were
    # silently ignored (482 audit warnings) and broke vehglass shattermap export.
    primary = mesh.color_attributes.new(name='Color 1', type='BYTE_COLOR', domain='CORNER')
    secondary = mesh.color_attributes.new(name='Color 2', type='BYTE_COLOR', domain='CORNER')
    ids = set()
    for polygon in mesh.polygons:
        horizontal = sum(mesh.vertices[index].co.x for index in polygon.vertices) / len(polygon.vertices)
        channel = light_id(source_name, horizontal)
        ids.add(channel)
        face_material = mesh.materials[polygon.material_index]
        emissive = face_material.shader_properties.filename == 'vehicle_lightsemissive.sps'
        for loop_index in polygon.loop_indices:
            primary.data[loop_index].color = (1, 1, 1, channel / 255 if emissive else 1)
            secondary.data[loop_index].color = (1, 1, 1, 1)
    if ids != {0}:
        REPORT['light_ids'][source_name] = sorted(ids)
    if not mesh.uv_layers:
        mesh.uv_layers.new(name='UVMap 0')
    if len(mesh.uv_layers) < 2:
        mesh.uv_layers.new(name='UVMap 1')
    for polygon in mesh.polygons:
        major = max(range(3), key=lambda axis: abs(polygon.normal[axis]))
        axes = [axis for axis in range(3) if axis != major]
        for loop_index in polygon.loop_indices:
            point = mesh.vertices[mesh.loops[loop_index].vertex_index].co
            for layer in mesh.uv_layers:
                layer.data[loop_index].uv = (point[axes[0]], point[axes[1]])


def lod_mesh(obj, ratio):
    if len(obj.data.polygons) < 48:
        return obj.data.copy()
    modifier = obj.modifiers.new('qcomet_lod_candidate', 'DECIMATE')
    modifier.ratio = ratio
    modifier.use_collapse_triangulate = True
    dependency_graph = bpy.context.evaluated_depsgraph_get()
    mesh = bpy.data.meshes.new_from_object(obj.evaluated_get(dependency_graph), preserve_all_data_layers=True, depsgraph=dependency_graph)
    obj.modifiers.remove(modifier)
    if not mesh.polygons:
        bpy.data.meshes.remove(mesh)
        return obj.data.copy()
    return mesh


def collision_material(name):
    if name not in COLLISION_MATERIALS:
        index = next(index for index, item in enumerate(COLLISIONS.collisionmats) if item.name == name)
        COLLISION_MATERIALS[name] = COLLISIONS.create_collision_material_from_index(index)
    return COLLISION_MATERIALS[name]


def hull(name, points, bone_name, material_name, mass, rig, composite, group, box=False):
    edit = bmesh.new()
    for point in points:
        edit.verts.new(point)
    result = bmesh.ops.convex_hull(edit, input=list(edit.verts), use_existing_faces=False)
    # A vertex can appear in both geom_interior and geom_unused; bmesh.ops.delete rejects duplicates.
    discarded = list(dict.fromkeys(element for element in result.get('geom_interior', []) + result.get('geom_unused', []) if isinstance(element, bmesh.types.BMVert) and element.is_valid and not element.link_faces))
    if discarded:
        bmesh.ops.delete(edit, geom=discarded, context='VERTS')
    bmesh.ops.recalc_face_normals(edit, faces=list(edit.faces))
    mesh = bpy.data.meshes.new(name)
    edit.to_mesh(mesh)
    edit.free()
    mesh.transform(rig.data.bones[bone_name].matrix_local.inverted())
    mesh.materials.append(collision_material(material_name))
    obj = bpy.data.objects.new(name, mesh)
    group.objects.link(obj)
    obj.parent = composite
    obj.sollum_type = SOLLUM.BOUND_BOX if box else SOLLUM.BOUND_GEOMETRY
    HELPERS.add_child_of_bone_constraint(obj, rig, bone_name)
    obj.child_properties.mass = mass
    obj.child_properties.shattermap_mode = 'AUTO' if material_name.startswith('CAR_GLASS') else 'NO'
    for flags in [obj.composite_flags1, obj.composite_flags2]:
        for flag in ['map_vehicle', 'vehicle_not_bvh', 'vehicle_bvh', 'ped', 'object', 'test_weapon', 'test_camera']:
            if hasattr(flags, flag):
                setattr(flags, flag, True)
    obj.display_type = 'WIRE'
    obj.hide_render = True
    obj.hide_set(True)
    REPORT['collision'][name] = {'bone': bone_name, 'material': material_name, 'mass_kg_provisional': mass, 'vertices': len(mesh.vertices)}
    return obj


def box_points(minimum, maximum):
    return [Vector((horizontal, longitudinal, height)) for horizontal in [minimum[0], maximum[0]] for longitudinal in [minimum[1], maximum[1]] for height in [minimum[2], maximum[2]]]


WINDOW_RENAMES = {'glass_dside_f': 'window_lf', 'glass_pside_f': 'window_rf', 'glass_dside_r': 'window_lr', 'glass_pside_r': 'window_rr', 'glass_rear': 'windscreen_r'}


def preflight():
    """Verify every object this script looks up by literal name actually
    exists before any mutation happens, and fail with one complete list
    instead of an opaque KeyError partway through a destructive rebuild.

    qcomet_vehicle_v013.blend and qcomet_cabin_v014.blend do not share one
    naming scheme (confirmed from their review_v013/review_v014 completion
    reports, not by inspecting the live scene, since blender-mcp was not
    reachable when this check was written) - e.g. v013's own object dump
    already has windows named window_lf/rf/lr/rr rather than the pre-rename
    glass_dside_f/pside_f/... names this script expects, and has no
    tail_bar_running object at all (only tail_bar_brake). Do not guess a
    substitute for a missing name here: report it and stop.
    """
    missing = []
    for old, new in WINDOW_RENAMES.items():
        if old not in bpy.data.objects and new not in bpy.data.objects:
            missing.append(f'{old} (or already-renamed {new})')
    for side in ('dside', 'pside'):
        for name in (f'headlight_{side}_blade_2', f'mirror_{side}'):
            if name not in bpy.data.objects:
                missing.append(name)
    if 'tail_bar_running' not in bpy.data.objects:
        missing.append('tail_bar_running (rear indicator anchor mesh; do not substitute tail_bar_brake, it is a different mesh/position)')
    for name in ('door_dside_f', 'door_pside_f', 'door_dside_r', 'door_pside_r', 'bonnet', 'boot',
                 'wheel_lf', 'wheel_rf', 'wheel_lr', 'wheel_rr', 'windscreen'):
        if name not in bpy.data.objects:
            missing.append(name)
    for side in ('dside', 'pside'):
        for end in ('f', 'r'):
            for name in (f'door_{side}_{end}', f'door_card_{side}_{end}'):
                if name not in bpy.data.objects:
                    missing.append(name)
    if missing:
        raise RuntimeError(
            'Preflight failed: ' + str(len(missing)) + ' object(s) this script indexes by literal '
            'name are missing from the active file. No changes were made. Missing: '
            + '; '.join(sorted(set(missing)))
        )


def main():
    active = Path(bpy.data.filepath).name
    if active not in ACCEPTED_INPUTS:
        raise RuntimeError(
            'The active input must be one of ' + ', '.join(ACCEPTED_INPUTS)
            + f' (active file is {active!r}).'
        )
    REVIEW.mkdir(exist_ok=True)
    window = bpy.context.window_manager.windows[0]
    with bpy.context.temp_override(window=window):
        input_version = Path(active).stem.rsplit('_v', 1)[-1]
        checkpoint = OUTPUT / f'qcomet_checkpoint_v{input_version}.blend'
        # Only write a safety copy when the live session holds unsaved edits;
        # a clean on-disk source is already its own checkpoint, and the only
        # new .blend this build should produce is qcomet_sollumz_v015.blend.
        checkpoint_written = False
        if bpy.data.is_dirty and not checkpoint.exists():
            bpy.ops.wm.save_as_mainfile(filepath=str(checkpoint), copy=True)
            checkpoint_written = True
        REPORT['phases']['0_input'] = {'active_source_file': active, 'accepted_inputs': list(ACCEPTED_INPUTS), 'source_was_dirty': bpy.data.is_dirty, 'checkpoint_copy_written': checkpoint_written}
        build()


def build():
    scene = bpy.context.scene
    staging = collection('QCOMET_SOLLUMZ_EXPORT')
    rig_collection = collection('QCOMET_RIG')
    collision_collection = collection('QCOMET_COLLISION')
    archive = collection('QCOMET_AUTHORING_ARCHIVE')
    archive.hide_viewport = True
    archive.hide_render = True
    REPORT['phases']['1_discovery'] = {'source': bpy.data.filepath, 'sollumz': '2.9.0', 'sollumz_shader_config_shim_applied': SHADER_CONFIG_SHIMMED, 'port': getattr(scene, 'blendermcp_port', None), 'lights_corrected': '0 is always-on; headlight 1/2, tail 3/4, indicators 5-8, brakes 9-11, reverse 12/13.', 'collision_corrected': 'Native fragment-embedded bounds, using CAR_METAL and CAR_GLASS_MEDIUM/STRONG; no standalone YBN is required for this checkpoint.'}
    REPORT['phases']['2_plan'] = ['Preserve original authoring look and separate components.', 'Build native Fragment/Drawable and skinned export geometry.', 'Create rigid detachable child meshes, windows, real light alpha IDs and collision.', 'Generate candidate LODs and run native in-memory export conversion.']
    preflight()
    repair_door_cards()
    for old, new in WINDOW_RENAMES.items():
        if old in bpy.data.objects:
            bpy.data.objects[old].name = new
        # else: already named `new` in this source file (verified by preflight).
    lighting = collection('QCOMET_LIGHTS')
    for side, sign in [('dside', -1), ('pside', 1)]:
        lamp = bpy.data.objects['headlight_' + side + '_blade_2']
        lamp_points = world_points(lamp)
        center = min(lamp_points, key=lambda point: abs(abs(point.x) - .78)).copy()
        center.y += .003
        center.z -= .014
        add_indicator('indicator_front_' + side, center, (sign * .052, 0, .017), (0, 1, 0), lamp.name, lighting)
        bar_points = world_points(bpy.data.objects['tail_bar_running'])
        center = min(bar_points, key=lambda point: abs(point.x - sign * .79)).copy()
        center.y -= .003
        center.z -= .012
        add_indicator('indicator_rear_' + side, center, (sign * .055, 0, .009), (0, -1, 0), 'tail_bar_running', lighting)
        mirror = bpy.data.objects['mirror_' + side]
        minimum, maximum = extents(world_points(mirror))
        center = (minimum + maximum) / 2
        center.y = maximum.y + .0015
        add_indicator('indicator_mirror_' + side, center, (sign * .035, 0, 0), (0, 1, 0), mirror.name, lighting)
    sources = [obj for obj in scene.objects if obj.type in {'MESH', 'FONT', 'CURVE'} and obj.visible_get() and not obj.hide_render and not obj.name.startswith(('COL_', 'qcomet_review_', 'PIVOT_'))]
    meshes = {obj.name: baked_mesh(obj) for obj in sources}
    origins = {obj.name: obj.matrix_world.translation.copy() for obj in sources}
    bone_specs = {'chassis': (Vector(), None), 'bodyshell': (Vector(), 'chassis')}
    moving = ['door_dside_f', 'door_pside_f', 'door_dside_r', 'door_pside_r', 'bonnet', 'boot', 'wheel_lf', 'wheel_rf', 'wheel_lr', 'wheel_rr', 'steeringwheel']
    for name in moving:
        if name == 'steeringwheel':
            continue
        pivot = bpy.data.objects.get('PIVOT_' + name)
        position = pivot.matrix_world.translation.copy() if pivot else origins[name]
        bone_specs[name] = (position, 'chassis')
    bone_specs['steering'] = (Vector((-.38, .46, 1.02)), 'chassis')
    bone_specs['steeringwheel'] = (Vector((-.38, .46, 1.02)), 'steering')
    for side, horizontal in [('dside', -.38), ('pside', .38)]:
        for end, longitudinal in [('f', .12), ('r', -.78)]:
            bone_specs['seat_' + side + '_' + end] = (Vector((horizontal, longitudinal, .44)), 'chassis')
    windows = {'window_lf': 'door_dside_f', 'window_rf': 'door_pside_f', 'window_lr': 'door_dside_r', 'window_rr': 'door_pside_r', 'windscreen': 'chassis', 'windscreen_r': 'chassis'}
    for name, parent in windows.items():
        minimum, maximum = extents([vertex.co for vertex in meshes[name].vertices])
        position = (minimum + maximum) / 2
        position.z = minimum.z
        bone_specs[name] = (position, parent)
    armature = bpy.data.armatures.new('qcomet_fragment_skeleton')
    input_stem = Path(bpy.data.filepath).stem
    if bpy.data.objects.get('qcomet'):
        bpy.data.objects['qcomet'].name = input_stem + '_legacy_qcomet_root'
    rig = bpy.data.objects.new('qcomet', armature)
    rig_collection.objects.link(rig)
    rig.sollum_type = SOLLUM.FRAGMENT
    rig['qcomet_rig_revision'] = 15
    for obj in bpy.context.selected_objects:
        obj.select_set(False)
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    for name, (position, parent) in bone_specs.items():
        bone = armature.edit_bones.new(name)
        bone.head = position
        direction = Vector((0, -.94, .342)).normalized() if name in ['steering', 'steeringwheel'] else Vector((0, 1, 0))
        bone.tail = position + direction * .08
        if parent:
            bone.parent = armature.edit_bones[parent]
        bone.use_connect = False
    bpy.ops.object.mode_set(mode='OBJECT')
    physical = set(moving) - {'steeringwheel'} | set(windows) | {'chassis'}
    for bone in armature.bones:
        DRAWABLE.set_recommended_bone_properties(bone)
        bone.sollumz_use_physics = bone.name in physical
        bone['qcomet_pivot_source'] = 'Existing provisional PIVOT guide' if bpy.data.objects.get('PIVOT_' + bone.name) else 'Explicit cabin or wheel center'
        if bone.name.startswith('window_'):
            if not any(flag.name == 'TransZ' for flag in bone.bone_properties.flags):
                bone.bone_properties.flags.add().name = 'TransZ'
            limit = rig.pose.bones[bone.name].constraints.new('LIMIT_LOCATION')
            limit.owner_space = 'LOCAL'
            limit.use_min_z = limit.use_max_z = True
            limit.min_z, limit.max_z = -.40, 0
        if bone.name.startswith('door_') or bone.name in ['bonnet', 'boot']:
            pose = rig.pose.bones[bone.name]
            pose.rotation_mode = 'XYZ'
            limit = pose.constraints.new('LIMIT_ROTATION')
            limit.owner_space = 'LOCAL'
            axis = 'z' if bone.name.startswith('door_') else 'x'
            setattr(limit, 'use_limit_' + axis, True)
            negative = 'dside' in bone.name or bone.name == 'boot'
            setattr(limit, 'min_' + axis, math.radians(-75) if negative else 0)
            setattr(limit, 'max_' + axis, 0 if negative else math.radians(75))
    drawable = empty('qcomet.drawable', staging, SOLLUM.DRAWABLE)
    drawable.parent = rig
    for name, value in [('lod_dist_high', 35), ('lod_dist_med', 85), ('lod_dist_low', 170), ('lod_dist_vlow', 350)]:
        setattr(drawable.drawable_properties, name, value)
    composite = empty('qcomet.bound_composite', collision_collection, SOLLUM.BOUND_COMPOSITE)
    composite.parent = rig
    authoring = {}
    for original in sources:
        name = original.name
        mesh = meshes[name]
        if original.type != 'MESH':
            groups = list(original.users_collection)
            original.name = input_stem + '_authoring_' + name
            for group in groups:
                group.objects.unlink(original)
            archive.objects.link(original)
            original.hide_render = True
            obj = bpy.data.objects.new(name, mesh)
            for group in groups:
                group.objects.link(obj)
        else:
            obj = original
            obj.data = mesh
        obj.parent = None
        obj.matrix_world = Matrix.Identity(4)
        obj.modifiers.clear()
        obj.constraints.clear()
        bone_name = bone_assignment(name)
        obj.data.transform(armature.bones[bone_name].matrix_local.inverted())
        constraint = obj.constraints.new('COPY_TRANSFORMS')
        constraint.target = rig
        constraint.subtarget = bone_name
        constraint.target_space = 'WORLD'
        constraint.owner_space = 'WORLD'
        constraint.mix_mode = 'REPLACE'
        bind_group(obj, bone_name)
        obj['qcomet_rig_bone'] = bone_name
        authoring[name] = obj
        REPORT['bindings'][name] = bone_name
    for name, obj in authoring.items():
        bone_name = REPORT['bindings'][name]
        parent_name = windows.get(name) if name.startswith('window_') else bone_name if bone_name.startswith(('door_', 'seat_')) and name != bone_name else None
        if parent_name in authoring:
            obj.parent = authoring[parent_name]
    bpy.context.view_layer.update()
    proxy_by_name = {}
    for name, source in authoring.items():
        bone_name = REPORT['bindings'][name]
        high = source.data.copy()
        high.transform(armature.bones[bone_name].matrix_local)
        old_materials = list(high.materials)
        high.materials.clear()
        for original in old_materials:
            high.materials.append(export_material(original, name))
        if not high.materials:
            high.materials.append(export_material(None, name))
        high.update()
        attributes(high, name)
        model = bpy.data.objects.new('exp_' + name, high)
        staging.objects.link(model)
        model.parent = drawable
        DRAWABLE.convert_obj_to_model(model)
        levels = [(LOD.HIGH, high)]
        for level, ratio in [(LOD.MEDIUM, .50), (LOD.LOW, .18), (LOD.VERYLOW, .07)]:
            reduced = lod_mesh(model, ratio)
            reduced.name = name + '_' + level.value
            levels.append((level, reduced))
            model.sz_lods.get_lod(level).mesh = reduced
        skin(model, rig, bone_name)
        model['qcomet_source_object'] = name
        model.hide_render = True
        model.hide_set(True)
        proxy_by_name[name] = model
        REPORT['lods'][name] = {level.value: len(mesh.polygons) for level, mesh in levels}
        if bone_name in physical and bone_name != 'chassis':
            child = bpy.data.objects.new('phys_' + name, high.copy())
            staging.objects.link(child)
            child.parent = drawable
            child.data.transform(armature.bones[bone_name].matrix_local.inverted())
            DRAWABLE.convert_obj_to_model(child)
            for level, mesh in levels[1:]:
                local = mesh.copy()
                local.transform(armature.bones[bone_name].matrix_local.inverted())
                child.sz_lods.get_lod(level).mesh = local
            child.sollumz_is_physics_child_mesh = True
            HELPERS.add_child_of_bone_constraint(child, rig, bone_name)
            child.hide_render = True
            child.hide_set(True)
    roof_max = max(vertex.co.z for name, model in proxy_by_name.items() if 'glass' in name or 'windscreen' in name for vertex in model.data.vertices)
    static_bounds = [
        ('COL_skateboard', (-.72, -1.18, .115), (.72, 1.18, .205), 'CAR_METAL', 1100),
        ('COL_floor_pan', (-.76, -1.65, .205), (.76, 1.65, .275), 'CAR_METAL', 380),
        ('COL_roof_cap', (-.59, -.65, roof_max - .043), (.59, .40, roof_max - .006), 'CAR_METAL', 25),
        ('COL_bumper_front', (-.79, 2.24, .30), (.79, 2.39, .49), 'CAR_PLASTIC', 12),
        ('COL_bumper_rear', (-.80, -2.38, .34), (.80, -2.21, .49), 'CAR_PLASTIC', 12),
    ]
    for name, minimum, maximum, material_name, mass in static_bounds:
        hull(name, box_points(minimum, maximum), 'chassis', material_name, mass, rig, composite, collision_collection, box=True)
    for name in moving:
        if name == 'steeringwheel':
            continue
        wheel = name.startswith('wheel_')
        source_name = 'rim_' + name[-2:] if wheel and 'rim_' + name[-2:] in proxy_by_name else name
        points = [vertex.co.copy() for vertex in proxy_by_name[source_name].data.vertices]
        hull('COL_' + name, points, name, 'RUBBER' if wheel else 'CAR_METAL', 24 if wheel else 25 if name.startswith('door_') else 14, rig, composite, collision_collection)
    for name in windows:
        points = [vertex.co.copy() for vertex in proxy_by_name[name].data.vertices]
        hull('COL_' + name, points, name, 'CAR_GLASS_MEDIUM' if name.startswith('window_') else 'CAR_GLASS_STRONG', 5, rig, composite, collision_collection)
    REPORT['phases']['3_implementation'] = {'bones': len(armature.bones), 'moving_controls': moving, 'models': len(proxy_by_name), 'native_collision_bounds': len(REPORT['collision']), 'palette_textures': len(PALETTE), 'shader_materials': len(MATERIALS), 'authoring_look_preserved': True, 'lod_ratios_provisional': [1, .50, .18, .07]}
    audit(rig, drawable, composite, authoring, proxy_by_name, moving, bone_specs)
    REPORT['warnings'].extend(['Existing hinge guides remain provisional; opening sweeps and entry clearance require human/in-game review.', 'Palette textures and generated projection UVs are structural export proxies, not final production texture bakes.', 'LOD meshes are automatic candidates and require silhouette, material and performance review.', 'No handling/meta, suspension setup, damage test or clean-server spawn test has been certified.'])
    scene['qcomet_sollumz_revision'] = 15
    scene['qcomet_game_ready'] = False
    scene['qcomet_native_export_audit'] = REPORT['phases']['4_verification'].get('native_asset_constructed', False)
    scene['qcomet_export_instructions'] = 'Export Fragment qcomet with Sollumz. Hidden exp_/phys_ meshes are export data; visible authoring meshes preserve the original look. See review_v015/readiness.md before any export/release.'
    rig.hide_set(True)
    for obj in bpy.context.selected_objects:
        obj.select_set(False)
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                area.spaces.active.shading.type = 'MATERIAL'
                area.spaces.active.shading.use_scene_lights = False
                area.spaces.active.shading.use_scene_world = False
                area.tag_redraw()
    (REVIEW / 'rig_validation.json').write_text(json.dumps(REPORT, indent=2), encoding='utf-8')
    notes = '# Q Comet v015 native Sollumz checkpoint\n\n'
    notes += f"All four workflow phases ran on {REPORT['phases']['0_input']['active_source_file']} (see review_v015/rig_validation.json phase 0_input). The source file on disk is preserved unmodified (a checkpoint copy is only written when the live session held unsaved edits; see phase 0_input). No GTA binary was written.\n\n"
    notes += '## Verification\n\n' + json.dumps(REPORT['phases']['4_verification'], indent=2) + '\n\n'
    notes += '## Remaining gates\n\n' + '\n'.join('- ' + message for message in REPORT['blockers'] + REPORT['warnings']) + '\n'
    notes += '\nExport Fragment `qcomet`, not the visible authoring meshes. The native Drawable and physical child models use real Sollumz shader/material, bone, LOD and collision properties. The Fragment embeds collision; a standalone YBN was not fabricated. Hidden export objects remain evaluation-enabled.\n'
    (REVIEW / 'readiness.md').write_text(notes, encoding='utf-8')
    text = bpy.data.texts.get(Path(__file__).name) or bpy.data.texts.new(Path(__file__).name)
    text.clear()
    text.write(Path(__file__).read_text(encoding='utf-8'))
    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT / 'qcomet_sollumz_v015.blend'))
    bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)
    status = {'saved': True, 'file': 'qcomet_sollumz_v015.blend', 'bones': len(armature.bones), 'collision_bounds': len(REPORT['collision']), 'native_audit': REPORT['phases']['4_verification'].get('native_asset_constructed', False), 'blocker_count': len(REPORT['blockers']), 'game_ready': False}
    (REVIEW / 'job_status.json').write_text(json.dumps(status), encoding='utf-8')
    print(json.dumps(status))


def audit(rig, drawable, composite, authoring, proxies, moving, bone_specs):
    bpy.context.view_layer.update()
    rest_error = 0.0
    for name, source in authoring.items():
        high = proxies[name].data
        for index in {0, len(high.vertices) // 2, len(high.vertices) - 1}:
            rest_error = max(rest_error, (source.matrix_world @ source.data.vertices[index].co - high.vertices[index].co).length)
    assert rest_error < .00002, 'Rest-pose attachment drift exceeds tolerance.'
    pivot_errors = {}
    for name in moving:
        pose = rig.pose.bones[name]
        expected = bone_specs[name][0]
        pose.rotation_mode = 'XYZ'
        axis = 2 if name.startswith('door_') else 1 if name == 'steeringwheel' else 0
        negative = 'dside' in name or name == 'boot'
        pose.rotation_euler[axis] = math.radians(-25 if negative else 25)
        bpy.context.view_layer.update()
        pivot_errors[name] = (pose.head - expected).length
        pose.rotation_euler = (0, 0, 0)
    bpy.context.view_layer.update()
    assert all(error < .00002 for error in pivot_errors.values()), 'A moving bone drifts off its pivot.'
    wheel_errors = {name: (rig.data.bones[name].head_local - Vector((-.845 if name[-2] == 'l' else .845, 1.5 if name[-1] == 'f' else -1.5, .39))).length for name in ['wheel_lf', 'wheel_rf', 'wheel_lr', 'wheel_rr']}
    assert max(wheel_errors.values()) < .000001, 'Wheel center mismatch.'
    tags = [bone.bone_properties.tag for bone in rig.data.bones]
    assert len(tags) == len(set(tags)), 'Duplicate bone tags.'
    verification = {'rest_pose_max_error_m': rest_error, 'moving_pivot_count': len(pivot_errors), 'max_moving_pivot_error_m': max(pivot_errors.values()), 'wheel_center_max_error_m': max(wheel_errors.values()), 'unique_bone_tags': True, 'native_fragment': rig.sollum_type == SOLLUM.FRAGMENT, 'native_drawable': drawable.sollum_type == SOLLUM.DRAWABLE, 'native_bound_composite': composite.sollum_type == SOLLUM.BOUND_COMPOSITE, 'native_asset_constructed': False, 'in_game_spawn_verified': False, 'hinge_clipping_certified': False}
    LOGGER = importlib.import_module(PACKAGE + '.logger')
    class AuditLogger(LOGGER.LoggerBase):
        def do_log(self, message, level):
            REPORT['warnings' if level != 'ERROR' else 'blockers'].append(str(message))
    context = importlib.import_module(PACKAGE + '.iecontext')
    gta = importlib.import_module('szio.gta5')
    exporter = importlib.import_module(PACKAGE + '.yft.yftexport')
    settings = context.ExportSettings(targets=(gta.AssetTarget(gta.AssetFormat.CWXML, gta.AssetVersion.GEN8),), apply_transforms=False)
    buffer = io.StringIO()
    try:
        with LOGGER.use_logger(AuditLogger()), context.export_context_scope(context.ExportContext('qcomet', settings)), contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
            asset, high_asset = exporter.create_fragment_asset(rig, out_embedded_textures=[], out_hd_textures={})
        verification['native_asset_constructed'] = asset is not None and asset.drawable is not None
        if asset is None:
            REPORT['blockers'].append('Sollumz could not construct the fragment asset.')
        else:
            verification['exported_skeleton_bones'] = len(asset.drawable.skeleton.bones)
            verification['exported_models_by_lod'] = {str(level): len(models) for level, models in asset.drawable.models.items()}
            verification['physics_children'] = len(asset.physics.lod1.children) if asset.physics else 0
            verification['generated_vehicle_windows'] = len(getattr(asset, 'vehicle_windows', []) or [])
            verification['native_asset_constructed'] = bool(asset.drawable.models) and verification['physics_children'] >= 21
            if not verification['native_asset_constructed']:
                REPORT['blockers'].append('Native asset lacks expected drawable models or physical bounds.')
    except Exception:
        REPORT['blockers'].append('Native export audit raised an exception; see native_export_audit.log.')
        buffer.write(traceback.format_exc())
    finally:
        rig.data.pose_position = 'POSE'
        for obj in proxies.values():
            obj.sz_lods.active_lod_level = LOD.HIGH
            obj.hide_set(True)
    (REVIEW / 'native_export_audit.log').write_text(buffer.getvalue(), encoding='utf-8')
    REPORT['phases']['4_verification'] = verification


if __name__ == '__main__':
    main()
