import json
import math
import runpy
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.kdtree import KDTree


ROOT = Path(__file__).resolve().parents[2]
REVIEW = ROOT / 'vehicles/qcomet/source/blender/review_v011'
VIEWS = {
    'front_three_quarter': ((6.2, 8.4, 4.0), (0, 0, .73), 5.9),
    'rear_three_quarter': ((-6.3, -8.2, 3.7), (0, 0, .73), 5.9),
    'side': ((8, 0, .75), (0, 0, .75), 5.55),
    'front': ((0, 8, .76), (0, 0, .76), 2.7),
    'rear': ((0, -8, .76), (0, 0, .76), 2.7),
    'top': ((0, 0, 9), (0, 0, 0), 5.55),
}


def setup():
    group = bpy.data.collections.get('QCOMET_V011_REVIEW_STUDIO')
    if group is None:
        group = bpy.data.collections.new('QCOMET_V011_REVIEW_STUDIO')
        bpy.context.scene.collection.children.link(group)
    for name, location, energy, size, width in [
        ('key', (1, 2, 6), 1300, 6.0, 2.3),
        ('side', (-4, 0, 3.5), 950, 5.0, 1.5),
        ('rim', (2, -4, 4.0), 1600, 5.0, 1.4),
        ('front', (0, 5, 2), 400, 3.0, 2.0),
    ]:
        obj = bpy.data.objects.get('qcomet_review_' + name)
        if obj is None:
            data = bpy.data.lights.new('qcomet_review_' + name, 'AREA')
            obj = bpy.data.objects.new(data.name, data)
            group.objects.link(obj)
        obj.location = location
        obj.rotation_euler = (Vector((0, 0, .7)) - obj.location).to_track_quat('-Z', 'Y').to_euler()
        obj.data.energy = energy
        obj.data.shape = 'RECTANGLE'
        obj.data.size = size
        obj.data.size_y = width
    original_sun = bpy.data.objects.get('QCOMET_REVIEW_SUN')
    if original_sun:
        original_sun.hide_render = True
    if bpy.data.objects.get('qcomet_review_floor') is None:
        mesh = bpy.data.meshes.new('qcomet_review_floor')
        mesh.from_pydata([(-200, -200, -.012), (200, -200, -.012), (200, 200, -.012), (-200, 200, -.012)], [], [(0, 1, 2, 3)])
        floor = bpy.data.objects.new('qcomet_review_floor', mesh)
        group.objects.link(floor)
        material = bpy.data.materials.new('qcomet_review_floor')
        material.diffuse_color = (.11, .12, .13, 1)
        material.use_nodes = True
        shader = material.node_tree.nodes.get('Principled BSDF')
        shader.inputs['Base Color'].default_value = (.11, .12, .13, 1)
        shader.inputs['Roughness'].default_value = .65
        mesh.materials.append(material)
    camera = bpy.data.objects.get('qcomet_review_camera_v011')
    if camera is None:
        camera_data = bpy.data.cameras.new('qcomet_review_camera_v011')
        camera = bpy.data.objects.new(camera_data.name, camera_data)
        group.objects.link(camera)
    scene = bpy.context.scene
    scene.camera = camera
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 24
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 8
    scene.cycles.transmission_bounces = 6
    scene.render.resolution_x = 1100
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.use_stamp = False
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes.get('Background')
    background.inputs['Color'].default_value = (.35, .39, .45, 1)
    background.inputs['Strength'].default_value = .35
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.exposure = 0
    for name in ['QCOMET_CONCEPT_REFERENCES', 'QCOMET_CONSTRUCTION_GUIDES', 'QCOMET_DIMENSION_GUIDES', 'QCOMET_INTERIOR_GUIDES']:
        group = bpy.data.collections.get(name)
        if group:
            group.hide_render = True
    return camera


def render_view(name):
    scene = bpy.context.scene
    location, target, scale = VIEWS[name]
    camera = scene.camera
    camera.location = location
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = scale
    if name == 'top':
        scene.render.resolution_x = 720
        scene.render.resolution_y = 1100
    else:
        scene.render.resolution_x = 1100
        scene.render.resolution_y = 720
    scene.render.filepath = str(REVIEW / ('qcomet_v011_' + name + '.png'))
    bpy.ops.render.render(write_still=True)
    print(scene.render.filepath)


def audit():
    report = {'scope': 'Surfacing geometry; not a game-readiness certification', 'objects': {}, 'symmetry': {}, 'required_parts': {}}
    dependency_graph = bpy.context.evaluated_depsgraph_get()
    for obj in bpy.context.scene.objects:
        if obj.type != 'MESH' or obj.get('qcomet_revision') != 11 or not obj.visible_get() or obj.hide_render:
            continue
        evaluated = obj.evaluated_get(dependency_graph)
        mesh = evaluated.to_mesh()
        edit = bmesh.new()
        edit.from_mesh(mesh)
        report['objects'][obj.name] = {
            'generated_surface': any(modifier.name == 'surface_inner_return' for modifier in obj.modifiers),
            'base_vertices': len(obj.data.vertices),
            'evaluated_faces': len(mesh.polygons),
            'zero_area_faces': sum(face.calc_area() < 1e-12 for face in edit.faces),
            'nonmanifold_edges': sum(not edge.is_manifold for edge in edit.edges),
            'loose_vertices': sum(not vertex.link_edges for vertex in edit.verts),
        }
        edit.free()
        evaluated.to_mesh_clear()
    for name in report['objects']:
        if 'dside' not in name:
            continue
        counterpart = bpy.data.objects.get(name.replace('dside', 'pside'))
        if counterpart is None:
            continue
        obj = bpy.data.objects[name]
        tree = KDTree(len(counterpart.data.vertices))
        for index, vertex in enumerate(counterpart.data.vertices):
            tree.insert(counterpart.matrix_world @ vertex.co, index)
        tree.balance()
        distances = []
        for vertex in obj.data.vertices:
            position = obj.matrix_world @ vertex.co
            position.x = -position.x
            distances.append(tree.find(position)[2])
        report['symmetry'][name] = max(distances)
    for stem in ['door', 'seat']:
        for side in ['dside', 'pside']:
            for end in ['f', 'r']:
                name = '_'.join([stem, side, end])
                report['required_parts'][name] = bpy.data.objects.get(name) is not None
    report['wheel_centers'] = {name: list(bpy.data.objects[name].location) for name in ['wheel_lf', 'wheel_rf', 'wheel_lr', 'wheel_rr']}
    report['all_new_surfaces_nondegenerate'] = all(value['zero_area_faces'] == 0 for value in report['objects'].values())
    report['all_new_surfaces_closed_after_solidify'] = all(value['nonmanifold_edges'] == 0 for value in report['objects'].values() if value['generated_surface'])
    report['legacy_detail_open_edges'] = {name: value['nonmanifold_edges'] for name, value in report['objects'].items() if not value['generated_surface'] and value['nonmanifold_edges']}
    report['bilateral_symmetry_pass'] = all(value < .0001 for value in report['symmetry'].values())
    recipe = runpy.run_path(str(ROOT / 'tools/blender/refine_qcomet_body_v011.py'), run_name='qcomet_audit_recipe')
    join_errors = []
    for rear, position in [(False, .975), (True, -1.55)]:
        for index in range(101):
            fraction = -.999 + 1.998 * index / 100
            theta = math.asin(math.copysign(abs(fraction) ** 2.5, fraction))
            join_errors.append((Vector(recipe['canopy'](theta, position)) - Vector(recipe['top_surface'](fraction, 0, rear))).length)
    report['canopy_to_cowl_deck_master_error_m'] = max(join_errors)
    report['canopy_to_cowl_deck_master_pass'] = max(join_errors) < .00001
    report['seat_head_clearance_m'] = {}
    for side in ['dside', 'pside']:
        for end in ['f', 'r']:
            name = 'seat_' + side + '_' + end
            obj = bpy.data.objects[name]
            corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
            center = sum(corners, Vector()) / len(corners)
            half_width = recipe['WIDTH'](center.y) - .034
            theta = math.asin(math.copysign(abs(center.x / half_width) ** 2.5, center.x))
            ceiling = recipe['canopy'](theta, center.y)[2] - .003
            report['seat_head_clearance_m'][name] = ceiling - max(corner.z for corner in corners)
    report['driver_sightline_probe'] = []
    eye = Vector((-.38, .12, 1.23))
    for yaw in [-15, 0, 15]:
        for pitch in [-3, 0, 5]:
            direction = Vector((math.sin(math.radians(yaw)), math.cos(math.radians(yaw)), math.tan(math.radians(pitch)))).normalized()
            origin = eye.copy()
            obstruction = None
            traversed_glass = []
            for iteration in range(16):
                hit, location, normal, face_index, obj, transform = bpy.context.scene.ray_cast(dependency_graph, origin, direction, distance=3)
                if not hit or (location - eye).length > 3:
                    break
                if obj.name == 'windscreen' or obj.name.startswith('glass_'):
                    traversed_glass.append(obj.name)
                    origin = location + direction * .005
                else:
                    obstruction = obj.name
                    break
            report['driver_sightline_probe'].append({'yaw_degrees': yaw, 'pitch_degrees': pitch, 'obstruction': obstruction, 'glass': sorted(set(traversed_glass))})
    report['driver_sightline_probe_note'] = 'Nine static rays from an assumed eye point only; not a first-person gameplay test.'
    (REVIEW / 'geometry_validation.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({key: value for key, value in report.items() if key not in ['objects', 'symmetry']}, indent=2))
    return report
