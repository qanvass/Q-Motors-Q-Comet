from __future__ import annotations

import json
import hashlib
import math
import runpy
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import tessellate_polygon


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'vehicles/qcomet/source/blender'
REVIEW = OUTPUT / 'review_v012'
BASE = runpy.run_path(str(ROOT / 'tools/blender/refine_qcomet_body_v011.py'), run_name='qcomet_v011_library')
CHANGED = set()
TREES = {}
FRONT_PANELS = ['bumper_f', 'hood_leading_band', 'hood_shoulder_dside', 'hood_shoulder_pside', 'fender_dside_f', 'fender_pside_f']
REAR_PANELS = ['rear_bumper', 'rear_deck_leading_band', 'rear_deck_shoulder_dside', 'rear_deck_shoulder_pside', 'quarter_dside_r', 'quarter_pside_r']


def collection(name):
    group = bpy.data.collections.get(name)
    if group is None:
        group = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(group)
    return group


def archive(name):
    backup = bpy.data.objects.get('v011_detail_' + name)
    if backup:
        return backup
    obj = bpy.data.objects.get(name)
    if obj is None:
        return None
    deps = bpy.context.evaluated_depsgraph_get()
    mesh = bpy.data.meshes.new_from_object(obj.evaluated_get(deps))
    backup = bpy.data.objects.new('v011_detail_' + name, mesh)
    backup.matrix_world = obj.matrix_world.copy()
    group = collection('QCOMET_V011_DETAILS_ARCHIVE')
    group.objects.link(backup)
    group.hide_render = True
    group.hide_viewport = True
    backup.hide_render = True
    return backup


def reset_panel(name):
    backup = archive(name)
    obj = bpy.data.objects[name]
    obj.data = backup.data.copy()
    obj.modifiers.clear()
    obj.matrix_world = backup.matrix_world.copy()
    obj['qcomet_revision'] = 12
    CHANGED.add(name)
    return obj


def retire(name):
    obj = bpy.data.objects.get(name)
    if obj:
        archive(name)
        obj.hide_render = True
        obj.hide_set(True)
        obj['qcomet_retired_reason'] = 'Superseded by source-fitted v012 detailing'


def material(name, color, roughness=.3, metallic=0, emission=0):
    result = BASE['material'](name, color, roughness, metallic)
    shader = next(node for node in result.node_tree.nodes if node.type == 'BSDF_PRINCIPLED')
    shader.inputs['Emission Color'].default_value = (*color, 1)
    shader.inputs['Emission Strength'].default_value = emission
    return result


def materials():
    material('qcomet_pocket_olive_v012', (.023, .030, .014), .50)
    material('qcomet_lamp_black_v012', (.006, .008, .007), .48)
    material('qcomet_led_warm_v012', (1, .80, .57), .19, emission=20)
    material('qcomet_tail_running_v012', (.64, .0015, .0006), .18, emission=25)
    material('qcomet_tail_brake_v012', (1, .002, .0007), .18, emission=25)
    material('qcomet_optics_v012', (.012, .025, .032), .07, metallic=.45)
    material('qcomet_reverse_lens_v012', (.11, .14, .15), .20)
    material('Trim_Bronze', (.30, .155, .065), .34, metallic=.83)
    carbon = material('Aero_Carbon', (.012, .015, .014), .29, metallic=.16)
    nodes = carbon.node_tree.nodes
    links = carbon.node_tree.links
    shader = next(node for node in nodes if node.type == 'BSDF_PRINCIPLED')
    texture = nodes.get('qcomet_weave') or nodes.new('ShaderNodeTexChecker')
    texture.name = 'qcomet_weave'
    texture.inputs['Scale'].default_value = 320
    texture.inputs['Color1'].default_value = (.006, .008, .007, 1)
    texture.inputs['Color2'].default_value = (.020, .026, .023, 1)
    coordinates = nodes.get('qcomet_carbon_coords') or nodes.new('ShaderNodeTexCoord')
    coordinates.name = 'qcomet_carbon_coords'
    links.new(coordinates.outputs['Object'], texture.inputs['Vector'])
    links.new(texture.outputs['Color'], shader.inputs['Base Color'])
    bump = nodes.get('qcomet_weave_bump') or nodes.new('ShaderNodeBump')
    bump.name = 'qcomet_weave_bump'
    bump.inputs['Strength'].default_value = .12
    bump.inputs['Distance'].default_value = .00012
    links.new(texture.outputs['Fac'], bump.inputs['Height'])
    links.new(bump.outputs['Normal'], shader.inputs['Normal'])


def mesh_object(name, vertices, faces, material_names, group='QCOMET_BODY_PANELS', thickness=0, face_materials=None):
    archive(name)
    obj = bpy.data.objects.get(name)
    mesh = bpy.data.meshes.new(name + '_v012')
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    if obj is None:
        obj = bpy.data.objects.new(name, mesh)
        collection(group).objects.link(obj)
    else:
        obj.data = mesh
        obj.modifiers.clear()
    obj.matrix_world = Matrix.Identity(4)
    obj.hide_render = False
    obj.hide_set(False)
    obj['qcomet_revision'] = 12
    obj['qcomet_provenance'] = 'Authored from user-supplied Q Comet concepts; no third-party vehicle assets'
    for name_material in material_names:
        mesh.materials.append(bpy.data.materials[name_material])
    if face_materials:
        for face, index in zip(mesh.polygons, face_materials):
            face.material_index = index
    edit = bmesh.new()
    edit.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(edit, faces=list(edit.faces))
    edit.to_mesh(mesh)
    edit.free()
    for face in mesh.polygons:
        face.use_smooth = True
    if thickness:
        modifier = obj.modifiers.new('closed_surface_return', 'SOLIDIFY')
        modifier.thickness = thickness
        modifier.offset = -1
    CHANGED.add(obj.name)
    return obj


def patch(name, surface, columns, rows, material_name, group='QCOMET_BODY_PANELS', thickness=.003):
    vertices = [surface(column / columns, row / rows) for row in range(rows + 1) for column in range(columns + 1)]
    faces = []
    for row in range(rows):
        for column in range(columns):
            start = row * (columns + 1) + column
            faces.append((start, start + 1, start + columns + 2, start + columns + 1))
    return mesh_object(name, vertices, faces, [material_name], group, thickness)


def baseline_tree(names):
    key = tuple(names)
    if key not in TREES:
        vertices, polygons = [], []
        for name in names:
            obj = archive(name)
            offset = len(vertices)
            vertices.extend(obj.matrix_world @ vertex.co for vertex in obj.data.vertices)
            polygons.extend(tuple(offset + index for index in face.vertices) for face in obj.data.polygons)
        TREES[key] = BVHTree.FromPolygons(vertices, polygons)
    return TREES[key]


def front_surface(horizontal, height):
    point, normal, index, distance = baseline_tree(FRONT_PANELS).ray_cast(Vector((horizontal, 3.2, height)), Vector((0, -1, 0)), 2.4)
    if point is not None:
        return point.y
    return BASE['fascia_position'](horizontal, height)


def rear_surface(horizontal, height):
    point, normal, index, distance = baseline_tree(REAR_PANELS).ray_cast(Vector((horizontal, -3.2, height)), Vector((0, 1, 0)), 2.4)
    if point is not None:
        return point.y
    return BASE['fascia_position'](horizontal, height, True)


def side_surface(position, height, sign):
    names = ['fender_pside_f', 'door_pside_f', 'door_pside_r', 'quarter_pside_r'] if sign > 0 else ['fender_dside_f', 'door_dside_f', 'door_dside_r', 'quarter_dside_r']
    point, normal, index, distance = baseline_tree(names).ray_cast(Vector((sign * 2, position, height)), Vector((-sign, 0, 0)), 2)
    if point is not None:
        return point.x
    fraction = (height - .265) / (BASE['BELT'](position) - .265)
    return sign * (BASE['WIDTH'](position) + BASE['SECTION'](fraction))


def capsule(center_horizontal, center_height, half_width, half_height, segments=20):
    points = []
    run = half_width - half_height
    for endpoint in [1, -1]:
        start = -math.pi / 2 if endpoint == 1 else math.pi / 2
        for index in range(segments + 1):
            angle = start + math.pi * index / segments
            points.append((center_horizontal + endpoint * run + half_height * math.cos(angle), center_height + half_height * math.sin(angle)))
    return points


def smooth_outline(points, samples=5):
    result = []
    for index in range(len(points)):
        previous = Vector(points[(index - 1) % len(points)])
        current = Vector(points[index])
        following = Vector(points[(index + 1) % len(points)])
        after = Vector(points[(index + 2) % len(points)])
        for sample in range(samples):
            fraction = sample / samples
            point = .5 * ((2 * current) + (-previous + following) * fraction + (2 * previous - 5 * current + 4 * following - after) * fraction ** 2 + (-previous + 3 * current - 3 * following + after) * fraction ** 3)
            result.append(tuple(point))
    return result


def volume_loops(name, outlines, mapper, layers, material_names, bottom_material=0, group='QCOMET_V012_CONSTRUCTION'):
    vertices, faces, assignments = [], [], []
    for outline in outlines:
        center = sum((Vector(point) for point in outline), Vector((0, 0))) / len(outline)
        offset = len(vertices)
        count = len(outline)
        for scale, depth in layers:
            for point in outline:
                coordinate = center + (Vector(point) - center) * scale
                vertices.append(mapper(coordinate.x, coordinate.y, depth))
        projected = [Vector((point[0], point[1], 0)) for point in outline]
        lookup = {tuple(point): index for index, point in enumerate(projected)}
        triangles = [tuple(point if isinstance(point, int) else lookup[tuple(point)] for point in triangle) for triangle in tessellate_polygon([projected])]
        for triangle in triangles:
            faces.append(tuple(offset + index for index in reversed(triangle)))
            assignments.append(0)
        for layer in range(len(layers) - 1):
            for index in range(count):
                next_index = (index + 1) % count
                faces.append((offset + layer * count + index, offset + layer * count + next_index, offset + (layer + 1) * count + next_index, offset + (layer + 1) * count + index))
                assignments.append(0)
        for triangle in triangles:
            faces.append(tuple(offset + (len(layers) - 1) * count + index for index in triangle))
            assignments.append(bottom_material)
    return mesh_object(name, vertices, faces, material_names, group, face_materials=assignments)


def boolean_cut(target_names, cutter, solver='MANIFOLD'):
    for name in target_names:
        obj = bpy.data.objects[name]
        previous_mesh = obj.data.copy()
        previous_vertex_count = len(previous_mesh.vertices)
        if bpy.data.materials['qcomet_pocket_olive_v012'].name not in [slot.material.name for slot in obj.material_slots if slot.material]:
            obj.data.materials.append(bpy.data.materials['qcomet_pocket_olive_v012'])
        for selected in bpy.context.selected_objects:
            selected.select_set(False)
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        modifier = obj.modifiers.new('v012_recess', 'BOOLEAN')
        modifier.operation = 'DIFFERENCE'
        modifier.solver = solver
        modifier.object = cutter
        bpy.ops.object.modifier_apply(modifier=modifier.name)
        if len(obj.data.vertices) < max(4, previous_vertex_count * .35):
            obj.data = previous_mesh
            raise RuntimeError('Rejected destructive aperture cut on ' + name)
        bpy.data.meshes.remove(previous_mesh)
        obj['qcomet_revision'] = 12
        CHANGED.add(name)
    cutter.hide_render = True
    cutter.hide_set(True)
    cutter['qcomet_construction_only'] = True


def aperture(name, outline, rear=False):
    mapper = lambda horizontal, height, depth: (horizontal, depth, height)
    layers = [(1, -3.1), (1, -1.8)] if rear else [(1, 3.1), (1, 1.35)]
    return volume_loops(name, [outline], mapper, layers, ['Paint_Primary'])


def pocket(name, outline, mapper, depth=.04, material_name='Aero_Carbon', group='QCOMET_BODY_PANELS'):
    center = sum((Vector(point) for point in outline), Vector((0, 0))) / len(outline)
    vertices = [mapper(point[0], point[1], .0002) for point in outline]
    for point in outline:
        inside = center + (Vector(point) - center) * .94
        vertices.append(mapper(inside.x, inside.y, -depth))
    count = len(outline)
    faces = [(index, (index + 1) % count, (index + 1) % count + count, index + count) for index in range(count)]
    projected = [Vector((point[0], point[1], 0)) for point in outline]
    lookup = {tuple(point): index for index, point in enumerate(projected)}
    faces.extend(tuple(count + (point if isinstance(point, int) else lookup[tuple(point)]) for point in triangle) for triangle in tessellate_polygon([projected]))
    return mesh_object(name, vertices, faces, [material_name], group, thickness=.003)


def stroke(name, points, width, material_name, depth=.003, group='QCOMET_BODY_PANELS', facing=(0, 1, 0), closed=False):
    points = [Vector(point) for point in points]
    vertices, faces = [], []
    normal = Vector(facing).normalized()
    for index, point in enumerate(points):
        previous = points[(index - 1) % len(points)] if index or closed else point
        following = points[(index + 1) % len(points)] if index < len(points) - 1 or closed else point
        tangent = (following - previous).normalized()
        transverse = tangent.cross(normal).normalized()
        half_width = width(index / max(1, len(points) - 1)) if callable(width) else width
        vertices.extend([point - transverse * half_width + normal * depth / 2, point + transverse * half_width + normal * depth / 2, point + transverse * half_width - normal * depth / 2, point - transverse * half_width - normal * depth / 2])
    for index in range(len(points) if closed else len(points) - 1):
        following = (index + 1) % len(points)
        for corner in range(4):
            faces.append((index * 4 + corner, index * 4 + (corner + 1) % 4, following * 4 + (corner + 1) % 4, following * 4 + corner))
    if not closed:
        faces.extend([(3, 2, 1, 0), tuple((len(points) - 1) * 4 + corner for corner in range(4))])
    return mesh_object(name, vertices, faces, [material_name], group)


def prepare():
    if Path(bpy.data.filepath).stem not in {'qcomet_body_v011', 'qcomet_body_v012'}:
        raise RuntimeError('Open the active Q Comet v011 or v012 scene first.')
    REVIEW.mkdir(exist_ok=True)
    collection('QCOMET_V012_CONSTRUCTION').hide_viewport = False
    manifest = {
        'sources': [r'C:\Users\Qanva\Desktop\Gaming GTA\Q Comet Front view showroom.png', r'C:\Users\Qanva\Desktop\Gaming GTA\q comet all four sides.png', 'docs/qcomet-art-brief.md'],
        'priority': 'Latest explicit forensic dimensions, then front showroom/four-side visual shapes; original body package remains provisional.',
        'primary_features': {'grille_rows': 9, 'headlight_blades_per_side': 3, 'vertical_drls': 2, 'lower_intake_louvers': 9, 'tail_tiers': 2, 'wheel_centers_unchanged': True},
        'geometry_gates': {'nonmanifold_edges': 0, 'loose_vertices': 0, 'zero_area_faces': 0, 'headlight_emission': 20.0, 'tail_emission': 25.0},
        'reference_registration': 'Front X/Z outlines traced from supplied images and depth-fitted by raycasting against the preserved body, not replacement primitive housings.',
        'exact_pixel_fit_certified': False,
        'limitation': 'Concept illustrations and the existing provisional body are not a calibrated exact 3D reconstruction; no full-vehicle 1:1 claim.',
    }
    (REVIEW / 'reference_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    materials()
    for name in FRONT_PANELS + REAR_PANELS + ['door_dside_f', 'door_dside_r', 'door_pside_f', 'door_pside_r']:
        reset_panel(name)
    for name in ['front_dimple_intake', 'front_lower_intake_return', 'tail_lens']:
        retire(name)
    baseline_tree(FRONT_PANELS)
    baseline_tree(REAR_PANELS)
    print('v012 baseline panels prepared without altering v011 source file')


def grille():
    accepted = []
    collisions = 0
    for row in range(9):
        height = .305 + .240 * row / 8
        positive = []
        offset = .014 if row % 2 else 0
        for column in range(27):
            horizontal = column * .028 + offset
            weight = max(0, min(1, 1 - (.55 * (abs(horizontal) / .55) ** 1.6 + .85 * ((height - .305) / .24) ** 1.35)))
            if weight < .12 or math.hypot(horizontal, height - .62) < .11:
                continue
            half_width = .020 * weight
            if horizontal > 0 and horizontal < half_width + .001:
                collisions += 2
                continue
            if positive and horizontal - positive[-1]['horizontal'] < half_width + positive[-1]['half_width'] + .0015:
                collisions += 2
                continue
            cell = {'row': row, 'horizontal': horizontal, 'height': height, 'weight': weight, 'half_width': half_width, 'half_height': .0065 * weight, 'depth': .007 * weight}
            positive.append(cell)
        for cell in positive:
            accepted.append(cell)
            if cell['horizontal'] > 0:
                accepted.append(dict(cell, horizontal=-cell['horizontal']))
    vertices, faces, assignments = [], [], []
    for cell in accepted:
        outline = capsule(cell['horizontal'], cell['height'], cell['half_width'], cell['half_height'])
        count = len(outline)
        center = Vector((cell['horizontal'], cell['height']))
        offset = len(vertices)
        for scale, depth in [(1, .015), (1, 0), (.80, -cell['depth'])]:
            for point in outline:
                position = center + (Vector(point) - center) * scale
                vertices.append((position.x, front_surface(position.x, position.y) + depth, position.y))
        faces.append(tuple(offset + index for index in reversed(range(count))))
        assignments.append(0)
        for layer in range(2):
            for index in range(count):
                faces.append((offset + layer * count + index, offset + layer * count + (index + 1) % count, offset + (layer + 1) * count + (index + 1) % count, offset + (layer + 1) * count + index))
                assignments.append(0)
        faces.append(tuple(offset + 2 * count + index for index in range(count)))
        assignments.append(1)
    cutter = mesh_object('qcomet_pill_recess_cutters_v012', vertices, faces, ['Paint_Primary', 'qcomet_pocket_olive_v012'], 'QCOMET_V012_CONSTRUCTION', face_materials=assignments)
    boolean_cut(['bumper_f'], cutter, solver='EXACT')
    obj = bpy.data.objects['bumper_f']
    obj['qcomet_recess_rows'] = 9
    obj['qcomet_recess_count'] = len(accepted)
    obj['qcomet_recess_max_depth'] = .007
    report = {'rows': 9, 'pitch_m': .028, 'stagger_m': .014, 'requested_max_half_width_m': .020, 'requested_max_half_height_m': .0065, 'max_depth_m': .007, 'count': len(accepted), 'collision_candidates_omitted': collisions, 'occupancy_policy': 'Preserve exact pitch lattice, specified dimensions, weight and depth; omit colliding cells symmetrically because full width 40 mm exceeds pitch 28 mm.', 'cells': accepted}
    (REVIEW / 'grille_specification.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('Integrated', len(accepted), 'actual recessed pill pockets in nine rows; no floating overlay tiles')


HEADLIGHT_OUTLINE = [(.428, .589), (.460, .620), (.552, .657), (.659, .719), (.748, .778), (.788, .842), (.842, .897), (.882, .947), (.902, .945), (.912, .855), (.903, .765), (.884, .714), (.820, .660), (.769, .638), (.686, .621), (.575, .597), (.452, .581)]
HEADLIGHT_PATHS = [
    [(.448, .602), (.552, .637), (.659, .698), (.748, .756), (.788, .821), (.842, .875), (.873, .925)],
    [(.449, .597), (.573, .627), (.676, .652), (.746, .703), (.790, .757), (.854, .791), (.882, .845)],
    [(.452, .593), (.575, .613), (.686, .636), (.769, .653), (.820, .678), (.873, .726)],
]


def front_lights():
    for side, sign in [('dside', -1), ('pside', 1)]:
        outline = smooth_outline([(sign * horizontal, height) for horizontal, height in HEADLIGHT_OUTLINE], 6)
        mapper = lambda horizontal, height, depth: (horizontal, front_surface(horizontal, height) + depth, height)
        cutter = aperture('qcomet_headlight_cut_' + side, outline)
        boolean_cut(['bumper_f', 'hood_leading_band', 'hood_shoulder_' + side, 'fender_' + side + '_f'], cutter)
        pocket('headlight_' + side + '_housing', outline, mapper, .048, 'qcomet_lamp_black_v012', 'QCOMET_LIGHTS')
        for index, anchors in enumerate(HEADLIGHT_PATHS, 1):
            profile = BASE['Profile'](anchors)
            points = []
            for sample in range(101):
                fraction = sample / 100
                horizontal = anchors[0][0] + (anchors[-1][0] - anchors[0][0]) * fraction
                height = profile(horizontal)
                horizontal *= sign
                points.append((horizontal, front_surface(horizontal, height) - .008, height))
            stroke('headlight_' + side + '_blade_' + str(index), points, lambda fraction: .00045 + .0046 * math.sin(math.pi * fraction) ** .7, 'qcomet_led_warm_v012', .003, 'QCOMET_LIGHTS')
        outline = smooth_outline([(sign * horizontal, height) for horizontal, height in [(.736, .304), (.790, .546), (.855, .631), (.900, .608), (.891, .250), (.875, .163), (.811, .180), (.740, .239)]], 5)
        cutter = aperture('qcomet_scoop_cut_' + side, outline)
        boolean_cut(['bumper_f', 'fender_' + side + '_f'], cutter)
        pocket('front_intake_pocket_' + side, outline, mapper, .066, 'Aero_Carbon')
        anchors = [(.856, .578), (.843, .525), (.825, .435), (.807, .345), (.827, .266), (.807, .222)]
        points = []
        for index in range(len(anchors) - 1):
            for sample in range(12):
                fraction = sample / 12
                horizontal = sign * (anchors[index][0] * (1 - fraction) + anchors[index + 1][0] * fraction)
                height = anchors[index][1] * (1 - fraction) + anchors[index + 1][1] * fraction
                points.append((horizontal, front_surface(horizontal, height) - .007, height))
        horizontal, height = sign * anchors[-1][0], anchors[-1][1]
        points.append((horizontal, front_surface(horizontal, height) - .007, height))
        stroke('drl_' + side, points, .0037, 'qcomet_led_warm_v012', .003, 'QCOMET_LIGHTS')
        for index in range(7):
            height = .275 + .043 * index
            points = []
            for sample in range(9):
                horizontal = sign * (.843 + .033 * sample / 8)
                points.append((horizontal, front_surface(horizontal, height) - .039, height))
            stroke('front_scoop_louver_' + side + '_' + str(index + 1), points, .0022, 'Aero_Carbon', .014)
    (REVIEW / 'headlight_trace.json').write_text(json.dumps({'outline_xz_m': HEADLIGHT_OUTLINE, 'three_blade_paths_xz_m': HEADLIGHT_PATHS, 'fit_method': 'Front-view source contour with preserved-body BVH depth projection', 'emission_strength': 20.0}, indent=2), encoding='utf-8')
    print('Three tapered LED blades per side and recessed outer DRL scoops rebuilt')


def lower_intake():
    outline = smooth_outline([(-.680, .261), (.680, .261), (.669, .215), (.625, .148), (-.625, .148), (-.669, .215)], 7)
    mapper = lambda horizontal, height, depth: (horizontal, front_surface(horizontal, .265) + depth, height)
    pocket('front_lower_intake_cavity', outline, mapper, .085, 'Aero_Carbon')
    for index in range(9):
        height = .156 + index * .0116
        half_width = .620 + .039 * index / 8
        points = []
        for sample in range(65):
            horizontal = -half_width + 2 * half_width * sample / 64
            points.append((horizontal, front_surface(horizontal, .265) - .025, height))
        obj = stroke('front_lower_louver_' + str(index + 1).zfill(2), points, .0019, 'Aero_Carbon', .025)
        obj['qcomet_louver_index'] = index + 1
    for lateral in [-.39, 0, .39]:
        points = [(lateral, front_surface(lateral, .265) - .042, .15), (lateral, front_surface(lateral, .265) - .042, .253)]
        stroke('front_intake_support_' + str(lateral).replace('.', '_').replace('-', 'minus'), points, .0018, 'Aero_Carbon', .004)
    upper = [(horizontal, front_surface(horizontal, .265) + .0006, .263) for horizontal in [(-.69 + 1.38 * index / 100) for index in range(101)]]
    stroke('front_intake_bronze_mouth', upper, .0020, 'Trim_Bronze', .0025)
    patch('front_mouth_upper_return', lambda horizontal, vertical: (-.69 + 1.38 * horizontal, front_surface(-.69 + 1.38 * horizontal, .265), .265 + .010 * vertical), 80, 2, 'Paint_Primary', thickness=.006)
    def splitter(horizontal, vertical):
        lateral = -.953 + 1.906 * horizontal
        position = front_surface(lateral * .945, .265)
        return (lateral, position + .069 - .099 * vertical, .129 + .011 * vertical)
    patch('front_splitter', splitter, 100, 6, 'Aero_Carbon', thickness=.010)
    points = [(-.946 + 1.892 * index / 120, front_surface((-.946 + 1.892 * index / 120) * .945, .265) + .071, .131) for index in range(121)]
    stroke('front_splitter_bronze', points, .0016, 'Trim_Bronze', .002)
    for side, sign in [('dside', -1), ('pside', 1)]:
        def wing(horizontal, vertical, sign=sign):
            lateral = sign * (.65 + .28 * horizontal)
            height = .146 + (.16 * (1 - horizontal) ** 1.3 + .022) * vertical
            position = front_surface(lateral, .265) + .020 * (1 - vertical)
            return (lateral, position, height)
        patch('front_aero_wing_' + side, wing, 24, 8, 'Aero_Carbon', thickness=.008)
        anchors = [(sign * .65, .297), (sign * .765, .190), (sign * .865, .157), (sign * .925, .172)]
        points = [(horizontal, front_surface(horizontal, .265) + .003, height) for horizontal, height in anchors]
        stroke('front_wing_bronze_' + side, points, .0024, 'Trim_Bronze', .003)
    print('Nine recessed horizontal carbon louvers and satin-bronze upper intake mouth installed')


def running_height(horizontal):
    fraction = abs(horizontal) / .91
    return .860 - .040 * math.exp(-((fraction - .72) / .14) ** 2) + .016 * math.exp(-((fraction - .98) / .16) ** 2)


def brake_height(horizontal):
    fraction = abs(horizontal) / .91
    return .878 - .014 * math.exp(-((fraction - .72) / .17) ** 2) + .012 * math.exp(-((fraction - .97) / .18) ** 2)


def rear_details():
    horizontal_values = [-.917 + 1.834 * index / 160 for index in range(161)]
    outline = [(horizontal, brake_height(horizontal) + .012) for horizontal in horizontal_values]
    outline.extend((horizontal, running_height(horizontal) - .015) for horizontal in reversed(horizontal_values))
    mapper = lambda horizontal, height, depth: (horizontal, rear_surface(horizontal, height) - depth, height)
    cutter = aperture('qcomet_tail_channel_cut', outline, rear=True)
    boolean_cut(REAR_PANELS, cutter)
    pocket('tail_lens', outline, mapper, .032, 'qcomet_lamp_black_v012', 'QCOMET_LIGHTS')
    running = []
    braking = []
    for index in range(321):
        horizontal = -.903 + 1.806 * index / 320
        height = running_height(horizontal)
        running.append((horizontal, rear_surface(horizontal, height) + .007, height))
        height = brake_height(horizontal)
        braking.append((horizontal, rear_surface(horizontal, height) + .006, height))
    stroke('tail_bar_running', running, .0028, 'qcomet_tail_running_v012', .003, 'QCOMET_LIGHTS', (0, -1, 0))
    stroke('tail_bar_brake', braking, lambda fraction: .0013 + .0048 * math.exp(-((abs(2 * fraction - 1) - .75) / .26) ** 4), 'qcomet_tail_brake_v012', .0035, 'QCOMET_LIGHTS', (0, -1, 0))
    for side, sign in [('dside', -1), ('pside', 1)]:
        points = []
        for index in range(81):
            fraction = index / 80
            horizontal = sign * (.51 + .39 * fraction)
            blend = math.sin(math.pi * fraction) ** 2
            height = brake_height(horizontal) * (1 - blend) + running_height(horizontal) * blend
            points.append((horizontal, rear_surface(horizontal, height) + .008, height))
        stroke('tail_quarter_branch_' + side, points, lambda fraction: .00065 + .0017 * math.sin(math.pi * fraction), 'qcomet_tail_running_v012', .002, 'QCOMET_LIGHTS', (0, -1, 0))
    vertices, faces = [], []
    for index in range(121):
        horizontal = -.932 + 1.864 * index / 120
        baseline = .905 + .020 * (abs(horizontal) / .932) ** 2
        position = rear_surface(horizontal, baseline)
        vertices.extend([(horizontal, position + .105, baseline - .020), (horizontal, position - .018, baseline + .015), (horizontal, position - .020, baseline + .004), (horizontal, position + .096, baseline - .025)])
    for index in range(120):
        for corner in range(4):
            faces.append((index * 4 + corner, index * 4 + (corner + 1) % 4, (index + 1) * 4 + (corner + 1) % 4, (index + 1) * 4 + corner))
    faces.extend([(3, 2, 1, 0), (480, 481, 482, 483)])
    mesh_object('boot_ducktail', vertices, faces, ['Paint_Primary'])
    upper_curve = []
    for index in range(121):
        horizontal = -.855 + 1.71 * index / 120
        height = .303 + .122 * math.exp(-((abs(horizontal) - .53) / .19) ** 6)
        upper_curve.append((horizontal, height))
    outline = upper_curve + [(horizontal, .151) for horizontal, height in reversed(upper_curve)]
    cutter = aperture('qcomet_diffuser_aperture_cut', outline, rear=True)
    boolean_cut(['rear_bumper'], cutter)
    pocket('rear_diffuser', outline, mapper, .064, 'Aero_Carbon')
    points = [(horizontal, rear_surface(horizontal, height) - .0025, height + .002) for horizontal, height in upper_curve]
    stroke('rear_diffuser_bronze', points, .0025, 'Trim_Bronze', .003, facing=(0, -1, 0))
    for index, horizontal in enumerate([-.66, -.43, -.20, .20, .43, .66], 1):
        profile = [(-2.15, .192), (-2.16, .330), (-2.42, .281), (-2.475, .146), (-2.34, .139)]
        vertices = []
        for sign in [-1, 1]:
            for position, height in profile:
                width = .006 + .003 * (position + 2.475) / .325
                toe = math.copysign(.012 * (position + 2.475) / .325, horizontal)
                vertices.append((horizontal + toe + sign * width, position, height))
        faces = [(4, 3, 2, 1, 0), (5, 6, 7, 8, 9)]
        faces.extend((corner, (corner + 1) % 5, (corner + 1) % 5 + 5, corner + 5) for corner in range(5))
        mesh_object('diffuser_strake_' + str(index), vertices, faces, ['Aero_Carbon'])
        points = [(horizontal, -2.16, .330), (horizontal, -2.42, .281), (horizontal, -2.475, .146)]
        stroke('diffuser_strake_bronze_' + str(index), points, .0014, 'Trim_Bronze', .002, facing=(1, 0, 0))
    print('Arterial running/brake tiers, integrated ducktail and six tapered carbon strakes completed')
    reverse_inners()


def reverse_inners():
    for side, sign in [('dside', -1), ('pside', 1)]:
        points = []
        for index in range(25):
            horizontal = sign * (.095 + .075 * index / 24)
            points.append((horizontal, rear_surface(horizontal, .237) + .060, .237))
        stroke('reverse_' + side + '_housing', points, .0075, 'qcomet_lamp_black_v012', .008, 'QCOMET_LIGHTS', (0, -1, 0))
        points = [(horizontal, position - .005, height) for horizontal, position, height in points]
        obj = stroke('reverse_' + side, points, .0028, 'qcomet_reverse_lens_v012', .002, 'QCOMET_LIGHTS', (0, -1, 0))
        obj['qcomet_light_function'] = 'Reverse; unlit in the running/brake exterior review. Game wiring pending.'


def side_details():
    for side, sign in [('dside', -1), ('pside', 1)]:
        mapper = lambda position, height, depth, sign=sign: (side_surface(position, height, sign) + sign * depth, position, height)
        outline = smooth_outline([(.959, .565), (1.025, .596), (1.145, .750), (1.150, .793), (.959, .806)], 6)
        cutter = volume_loops('qcomet_fender_duct_cut_' + side, [outline], mapper, [(1, .020), (.92, -.040)], ['Paint_Primary'])
        boolean_cut(['fender_' + side + '_f'], cutter)
        pocket('fender_vent_' + side, outline, mapper, .035, 'Aero_Carbon')
        points = []
        for index in range(33):
            position = .970 + .172 * index / 32
            points.append((side_surface(position, .775, sign) + sign * .0004, position, .775))
        stroke('fender_vent_bronze_' + side, points, .0032, 'Trim_Bronze', .003, facing=(sign, 0, 0))
        for index in range(3):
            height = .648 + .037 * index
            length = .072 + .025 * index
            points = [(side_surface(position, height, sign) - sign * .018, position, height) for position in [.975 + length * sample / 12 for sample in range(13)]]
            stroke('fender_duct_louver_' + side + '_' + str(index + 1), points, .0018, 'Aero_Carbon', .013, facing=(sign, 0, 0))
        for end, position in [('f', .20), ('r', -.72)]:
            outline = capsule(position, .925, .079, .013, 18)
            cutter = volume_loops('qcomet_handle_cut_' + side + '_' + end, [outline], mapper, [(1, .012), (.96, -.006)], ['Paint_Primary'])
            boolean_cut(['door_' + side + '_' + end], cutter)
            pocket('handle_recess_' + side + '_' + end, outline, mapper, .005, 'qcomet_pocket_olive_v012')
            cap = capsule(position, .925, .073, .0085, 18)
            volume_loops('handle_' + side + '_' + end, [cap], mapper, [(1, -.0010), (1, -.0035)], ['Paint_Primary'], group='QCOMET_BODY_PANELS')
            points = [mapper(coordinate[0], coordinate[1], -.0008) for coordinate in capsule(position, .925, .074, .0093, 18)]
            stroke('handle_bronze_cap_' + side + '_' + end, points, .00065, 'Trim_Bronze', .0010, facing=(sign, 0, 0), closed=True)
    print('Recessed vertical fender ducts and genuinely flush bronze-edged handles fitted')


def ellipsoid(name, center, scale, material_name, group='QCOMET_BODY_PANELS'):
    longitude_count, latitude_count = 40, 16
    vertices = [(center[0], center[1], center[2] + scale[2])]
    for latitude in range(1, latitude_count):
        angle = math.pi * latitude / latitude_count
        for longitude in range(longitude_count):
            spin = math.tau * longitude / longitude_count
            vertices.append((center[0] + scale[0] * math.sin(angle) * math.cos(spin), center[1] + scale[1] * math.sin(angle) * math.sin(spin), center[2] + scale[2] * math.cos(angle)))
    vertices.append((center[0], center[1], center[2] - scale[2]))
    faces = []
    for longitude in range(longitude_count):
        faces.append((0, 1 + longitude, 1 + (longitude + 1) % longitude_count))
    for latitude in range(latitude_count - 2):
        for longitude in range(longitude_count):
            start = 1 + latitude * longitude_count
            following = (longitude + 1) % longitude_count
            faces.append((start + longitude, start + following, start + longitude_count + following, start + longitude_count + longitude))
    for longitude in range(longitude_count):
        start = 1 + (latitude_count - 2) * longitude_count
        faces.append((len(vertices) - 1, start + (longitude + 1) % longitude_count, start + longitude))
    return mesh_object(name, vertices, faces, [material_name], group)


def mirrors():
    for side, sign in [('dside', -1), ('pside', 1)]:
        center = (sign * 1.055, .915, 1.077)
        ellipsoid('mirror_' + side, center, (.067, .049, .018), 'Aero_Carbon')
        ellipsoid('mirror_' + side + '_bronze', (sign * 1.055, .915, 1.062), (.062, .044, .005), 'Trim_Bronze')
        ellipsoid('mirror_' + side + '_camera_lens', (sign * 1.075, .962, 1.077), (.010, .003, .008), 'qcomet_optics_v012')
        attachment = side_surface(.913, 1.041, sign)
        points = [(attachment, .913, 1.041), (sign * .988, .909, 1.061), (sign * 1.035, .915, 1.070)]
        stroke('mirror_' + side + '_stalk', points, .011, 'Aero_Carbon', .010, facing=(0, 0, 1))
        retire('mirror_' + side + '_indicator')
    print('Ultra-slim digital camera pods and satin bronze lower caps detailed')


def qplus(name, center, normal, radius, group='QCOMET_BODY_PANELS'):
    center = Vector(center)
    normal = Vector(normal).normalized()
    horizontal = Vector((0, 0, 1)).cross(normal).normalized()
    vertical = Vector((0, 0, 1))
    points = [center + horizontal * (radius * math.cos(math.tau * index / 80) - radius * .18) + vertical * radius * math.sin(math.tau * index / 80) for index in range(80)]
    stroke(name, points, radius * .072, 'Trim_Bronze', radius * .11, group, normal, closed=True)
    points = [center + horizontal * radius * .27 - vertical * radius * .49, center + horizontal * radius * .90 - vertical * radius * .96]
    stroke(name + '_tail', points, radius * .078, 'Trim_Bronze', radius * .115, group, normal)
    plus_center = center + horizontal * radius * 1.38 - vertical * radius * .35
    for label, direction in [('horizontal', horizontal), ('vertical', vertical)]:
        stroke(name + '_plus_' + label, [plus_center - direction * radius * .23, plus_center + direction * radius * .23], radius * .055, 'Trim_Bronze', radius * .10, group, normal)


def wheel_and_badge_integrity():
    records = {}
    for end in ['lf', 'rf', 'lr', 'rr']:
        name = 'wheel_' + end
        obj = bpy.data.objects[name]
        archive(name)
        before = list(obj.location)
        edit = bmesh.new()
        edit.from_mesh(obj.data)
        bmesh.ops.remove_doubles(edit, verts=list(edit.verts), dist=.000005)
        loose = [vertex for vertex in edit.verts if not vertex.link_faces]
        loose_count = len(loose)
        bmesh.ops.delete(edit, geom=loose, context='VERTS')
        boundary = [edge for edge in edit.edges if edge.is_boundary]
        result = bmesh.ops.holes_fill(edit, edges=boundary, sides=0)
        for face in result['faces']:
            face.material_index = 0
        bmesh.ops.recalc_face_normals(edit, faces=list(edit.faces))
        obj.data = obj.data.copy()
        edit.to_mesh(obj.data)
        edit.free()
        obj.modifiers.clear()
        obj['qcomet_revision'] = 12
        obj['qcomet_wheel_center_locked'] = True
        CHANGED.add(name)
        records[name] = {'location_before': before, 'location_after': list(obj.location), 'removed_loose_vertices': loose_count, 'boundary_faces_added': len(result['faces']), 'spoke_geometry_preserved': True}
        sign = 1 if obj.location.x > 0 else -1
        center = (obj.location.x + sign * .096, obj.location.y, obj.location.z)
        outlines = [[(center[1] + .043 * math.cos(math.tau * index / 64), center[2] + .043 * math.sin(math.tau * index / 64)) for index in range(64)]]
        mapper = lambda position, height, depth, center=center, sign=sign: (center[0] + sign * depth, position, height)
        volume_loops('hub_' + end, outlines, mapper, [(1, .004), (1, -.010)], ['qcomet_lamp_black_v012'], group='QCOMET_RUNNING_GEAR')
        qplus('wheelcap_qplus_' + end, (center[0] + sign * .006, center[1], center[2]), (sign, 0, 0), .020, 'QCOMET_RUNNING_GEAR')
    qplus('badge_front', (0, front_surface(0, .622) + .003, .622), (0, 1, 0), .037)
    qplus('badge_rear', (0, rear_surface(0, .694) - .003, .694), (0, -1, 0), .037)
    (REVIEW / 'wheel_integrity_repairs.json').write_text(json.dumps(records, indent=2), encoding='utf-8')
    print('Original directional turbine geometry retained; loose wheel vertices removed, boundaries capped, Q+ center caps authored')


def finish_geometry():
    construction = collection('QCOMET_V012_CONSTRUCTION')
    construction.hide_render = True
    construction.hide_viewport = True
    for obj in bpy.context.scene.objects:
        if obj.type != 'MESH' or not obj.visible_get() or obj.hide_render or obj.get('qcomet_revision') != 12:
            continue
        if obj.name in FRONT_PANELS + REAR_PANELS or obj.name.startswith('door_'):
            edit = bmesh.new()
            edit.from_mesh(obj.data)
            bmesh.ops.dissolve_degenerate(edit, edges=list(edit.edges), dist=.000001)
            bmesh.ops.dissolve_degenerate(edit, edges=list(edit.edges), dist=.000005)
            bmesh.ops.recalc_face_normals(edit, faces=list(edit.faces))
            edit.to_mesh(obj.data)
            edit.free()
        obj.data.set_sharp_from_angle(angle=math.radians(35))
    for obj in bpy.context.selected_objects:
        obj.select_set(False)
    bpy.context.view_layer.update()


def audit():
    report = {'scope': 'All visible render-enabled vehicle meshes; excludes archived sources, cutters and review studio.', 'objects': {}, 'emission': {}, 'wheel_centers': {}, 'pocket_depth_probes': [], 'dimensions_approved': False, 'game_ready': False, 'exact_reference_match_certified': False}
    sources = [ROOT.parent / 'Q Comet Front view showroom.png', ROOT.parent / 'q comet all four sides.png', ROOT / 'docs/qcomet-art-brief.md', OUTPUT / 'qcomet_body_v011.blend', OUTPUT / 'qcomet_checkpoint_v011.blend']
    report['source_sha256'] = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources}
    dependency_graph = bpy.context.evaluated_depsgraph_get()
    for obj in bpy.context.scene.objects:
        if obj.type != 'MESH' or not obj.visible_get() or obj.hide_render or obj.name.startswith('qcomet_review'):
            continue
        evaluated = obj.evaluated_get(dependency_graph)
        edit = bmesh.new()
        edit.from_mesh(evaluated.to_mesh())
        report['objects'][obj.name] = {
            'vertices': len(edit.verts), 'faces': len(edit.faces),
            'nonmanifold_edges': sum(not edge.is_manifold for edge in edit.edges),
            'loose_vertices': sum(not vertex.link_faces for vertex in edit.verts),
            'zero_area_faces': sum(face.calc_area() < 1e-12 for face in edit.faces),
            'volume_m3': abs(edit.calc_volume(signed=True)),
        }
        edit.free()
        evaluated.to_mesh_clear()
    report['geometry_pass'] = all(value['vertices'] > 3 and value['volume_m3'] > 1e-13 and not (value['nonmanifold_edges'] or value['loose_vertices'] or value['zero_area_faces']) for value in report['objects'].values())
    for name, expected in [('qcomet_led_warm_v012', 20.0), ('qcomet_tail_running_v012', 25.0), ('qcomet_tail_brake_v012', 25.0)]:
        shader = next(node for node in bpy.data.materials[name].node_tree.nodes if node.type == 'BSDF_PRINCIPLED')
        actual = shader.inputs['Emission Strength'].default_value
        report['emission'][name] = {'expected': expected, 'actual': actual, 'pass': abs(actual - expected) < .00001}
    expected_centers = {'wheel_lf': (-.845, 1.5, .39), 'wheel_rf': (.845, 1.5, .39), 'wheel_lr': (-.845, -1.5, .39), 'wheel_rr': (.845, -1.5, .39)}
    for name, expected in expected_centers.items():
        actual = bpy.data.objects[name].location
        report['wheel_centers'][name] = {'actual': list(actual), 'expected': expected, 'pass': (actual - Vector(expected)).length < .000001}
    grille_specification = json.loads((REVIEW / 'grille_specification.json').read_text())
    tree = BVHTree.FromObject(bpy.data.objects['bumper_f'], dependency_graph)
    for cell in grille_specification['cells']:
        horizontal, height, weight = cell['horizontal'], cell['height'], cell['weight']
        point, normal, face_index, distance = tree.ray_cast(Vector((horizontal, 3.2, height)), Vector((0, -1, 0)), 2)
        actual = front_surface(horizontal, height) - point.y if point is not None else None
        expected = .007 * weight
        report['pocket_depth_probes'].append({'x': horizontal, 'z': height, 'expected_m': expected, 'actual_m': actual, 'pass': actual is not None and actual > .0002 and abs(actual - expected) < .0004})
    report['recess_depth_pass'] = all(probe['pass'] for probe in report['pocket_depth_probes'])
    report['feature_counts'] = {'pill_pockets': len(grille_specification['cells']), 'grille_rows': len(set(cell['height'] for cell in grille_specification['cells'])), 'lower_louvers': sum(obj.name.startswith('front_lower_louver_') for obj in bpy.context.scene.objects), 'headlight_blades': sum(obj.name.startswith('headlight_') and '_blade_' in obj.name and not obj.hide_render for obj in bpy.context.scene.objects), 'diffuser_strakes': sum(obj.name.startswith('diffuser_strake_') and 'bronze' not in obj.name and not obj.hide_render for obj in bpy.context.scene.objects)}
    report['four_doors_four_seats_present'] = all(bpy.data.objects.get(stem + '_' + side + '_' + end) is not None for stem in ['door', 'seat'] for side in ['dside', 'pside'] for end in ['f', 'r'])
    report['feature_counts_pass'] = all(report['feature_counts'][name] == expected for name, expected in [('grille_rows', 9), ('lower_louvers', 9), ('headlight_blades', 6), ('diffuser_strakes', 6)])
    report['light_visibility'] = {}
    light_names = ['headlight_' + side + '_blade_' + str(index) for side in ['dside', 'pside'] for index in [1, 2, 3]] + ['drl_dside', 'drl_pside', 'tail_bar_running', 'tail_bar_brake']
    for name in light_names:
        obj = bpy.data.objects[name]
        rear = name.startswith('tail_')
        rings = len(obj.data.vertices) // 4
        probes = []
        for index in range(3, rings - 3, 3):
            point = sum((obj.matrix_world @ obj.data.vertices[index * 4 + corner].co for corner in range(4)), Vector()) / 4
            origin = Vector((point.x, -3.2 if rear else 3.2, point.z))
            direction = Vector((0, 1 if rear else -1, 0))
            hit, location, normal, face_index, hit_object, matrix = bpy.context.scene.ray_cast(dependency_graph, origin, direction, distance=2)
            hit_name = hit_object.name if hit else 'nothing'
            visible = hit and (hit_name.startswith('tail_bar_') or hit_name.startswith('tail_quarter_branch_') if rear else (hit_name.startswith('headlight_') and '_blade_' in hit_name) or hit_name.startswith('drl_'))
            probes.append({'sample': index, 'hit': hit_name, 'pass': bool(visible)})
        report['light_visibility'][name] = {'pass': all(probe['pass'] for probe in probes), 'probes': probes}
    join_errors = []
    for rear, position in [(False, .975), (True, -1.55)]:
        for index in range(101):
            fraction = -.999 + 1.998 * index / 100
            angle = math.asin(math.copysign(abs(fraction) ** 2.5, fraction))
            join_errors.append((Vector(BASE['canopy'](angle, position)) - Vector(BASE['top_surface'](fraction, 0, rear))).length)
    report['inherited_canopy_master_join_error_m'] = max(join_errors)
    report['light_visibility_pass'] = all(value['pass'] for value in report['light_visibility'].values())
    report['pass'] = report['geometry_pass'] and report['recess_depth_pass'] and report['light_visibility_pass'] and report['feature_counts_pass'] and all(item['pass'] for item in report['emission'].values()) and all(item['pass'] for item in report['wheel_centers'].values()) and report['four_doors_four_seats_present']
    (REVIEW / 'geometry_validation.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({key: value for key, value in report.items() if key not in ['objects', 'pocket_depth_probes', 'light_visibility']}, indent=2))
    return report


def save():
    report = audit()
    if not report['pass']:
        raise RuntimeError('v012 save gate failed: inspect review_v012/geometry_validation.json')
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                area.spaces.active.shading.type = 'MATERIAL'
                area.spaces.active.overlay.show_overlays = False
                area.tag_redraw()
    recipe_name = Path(__file__).name
    text = bpy.data.texts.get(recipe_name) or bpy.data.texts.new(recipe_name)
    text.clear()
    text.write(Path(__file__).read_text(encoding='utf-8'))
    scene = bpy.context.scene
    scene['qcomet_exterior_revision'] = 12
    scene['qcomet_v012_validation'] = 'All active vehicle meshes closed; no loose vertices; emissive values and measured recess depths verified.'
    scene['qcomet_v012_limitations'] = 'Provisional package, not pixel-exact concept reconstruction or game-ready. See review_v012/reference_manifest.json.'
    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT / 'qcomet_body_v012.blend'))
    bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)


def main():
    prepare()
    grille()
    front_lights()
    lower_intake()
    rear_details()
    side_details()
    mirrors()
    wheel_and_badge_integrity()
    finish_geometry()
    save()


if __name__ == '__main__':
    main()
