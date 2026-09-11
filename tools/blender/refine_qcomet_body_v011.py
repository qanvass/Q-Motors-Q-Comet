from __future__ import annotations

import json
import math
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'vehicles/qcomet/source/blender'
REVIEW = OUTPUT / 'review_v011'
GAP = 0.004
CHANGED = []


class Profile:
    def __init__(self, points):
        self.positions = np.array([point[0] for point in points], dtype=float)
        self.values = np.array([point[1] for point in points], dtype=float)
        count = len(points)
        spans = np.diff(self.positions)
        system = np.zeros((count, count))
        target = np.zeros(count)
        system[0, 0] = system[-1, -1] = 1
        for index in range(1, count - 1):
            system[index, index - 1:index + 2] = (spans[index - 1], 2 * (spans[index - 1] + spans[index]), spans[index])
            target[index] = 6 * ((self.values[index + 1] - self.values[index]) / spans[index] - (self.values[index] - self.values[index - 1]) / spans[index - 1])
        self.second = np.linalg.solve(system, target)

    def __call__(self, position):
        position = float(np.clip(position, self.positions[0], self.positions[-1]))
        index = min(max(int(np.searchsorted(self.positions, position)) - 1, 0), len(self.positions) - 2)
        span = self.positions[index + 1] - self.positions[index]
        lower = (self.positions[index + 1] - position) / span
        upper = (position - self.positions[index]) / span
        return float(lower * self.values[index] + upper * self.values[index + 1] + ((lower ** 3 - lower) * self.second[index] + (upper ** 3 - upper) * self.second[index + 1]) * span ** 2 / 6)


WIDTH = Profile([(-2.4, .90), (-2.13, .947), (-1.5, .982), (-.8, .925), (0, .923), (.85, .951), (1.5, .982), (2.07, .951), (2.4, .92)])
BELT = Profile([(-2.4, .875), (-2.13, .96), (-1.55, 1.035), (-.8, 1.035), (0, 1.04), (.9, 1.042), (1.175, 1.035), (1.5, 1.025), (2.07, .86), (2.4, .765)])
CROWN = Profile([(-1.55, 1.053), (-1.30, 1.18), (-.96, 1.354), (-.58, 1.424), (-.20, 1.44), (.18, 1.418), (.45, 1.353), (.70, 1.221), (.975, BELT(.975) + .018)])
SECTION = Profile([(0, -.066), (.13, -.053), (.32, -.044), (.58, -.015), (.79, .002), (.91, -.006), (1, -.034)])


def collection(name):
    result = bpy.data.collections.get(name)
    if result is None:
        result = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(result)
    return result


def material(name, color, roughness, metallic=0, transmission=0):
    result = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    result.use_nodes = True
    shader = next(node for node in result.node_tree.nodes if node.type == 'BSDF_PRINCIPLED')
    for key, value in [('Base Color', (*color, 1)), ('Roughness', roughness), ('Metallic', metallic), ('Transmission Weight', transmission), ('Alpha', 1)]:
        shader.inputs[key].default_value = value
    result.diffuse_color = (*color, 1)
    return result


def archive(name):
    original = bpy.data.objects.get(name)
    if original is None or original.get('qcomet_revision') == 11:
        return
    group = collection('QCOMET_V010_SURFACING_ARCHIVE')
    group.hide_render = True
    group.hide_viewport = True
    if bpy.data.objects.get('v010_' + name) is None:
        backup = original.copy()
        if original.data:
            backup.data = original.data.copy()
        backup.name = 'v010_' + name
        group.objects.link(backup)
        backup.hide_render = True
    original['qcomet_revision'] = 11


def retire(name):
    original = bpy.data.objects.get(name)
    if original:
        archive(name)
        original.hide_render = True
        original.hide_set(True)
        original['qcomet_retired_reason'] = 'Superseded overlapping v010 surfacing'


def mesh_object(name, vertices, faces, material_name, group='QCOMET_BODY_PANELS', thickness=.012, outward=(0, 0, 1)):
    archive(name)
    obj = bpy.data.objects.get(name)
    mesh = bpy.data.meshes.new(name + '_v011_surface')
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
    obj['qcomet_revision'] = 11
    obj['qcomet_provenance'] = 'Original surfacing fitted to supplied Q Comet concepts; no imported assets'
    mesh.materials.append(bpy.data.materials[material_name])
    edit = bmesh.new()
    edit.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(edit, faces=list(edit.faces))
    average = sum((face.normal * face.calc_area() for face in edit.faces), Vector())
    if average.dot(Vector(outward)) < 0:
        bmesh.ops.reverse_faces(edit, faces=list(edit.faces))
    edit.to_mesh(mesh)
    edit.free()
    for polygon in mesh.polygons:
        polygon.use_smooth = True
    if thickness:
        modifier = obj.modifiers.new('surface_inner_return', 'SOLIDIFY')
        modifier.thickness = thickness
        modifier.offset = -1
        modifier.use_even_offset = True
    CHANGED.append(name)
    return obj


def patch(name, surface, columns, rows, material_name, group='QCOMET_BODY_PANELS', thickness=.012, outward=(0, 0, 1)):
    vertices = [surface(column / columns, row / rows) for row in range(rows + 1) for column in range(columns + 1)]
    faces = []
    for row in range(rows):
        for column in range(columns):
            start = row * (columns + 1) + column
            faces.append((start, start + 1, start + columns + 2, start + columns + 1))
    return mesh_object(name, vertices, faces, material_name, group, thickness, outward)


def canopy(theta, position):
    sine = math.sin(theta)
    fraction = math.copysign(abs(sine) ** .4, sine)
    height = max(0, math.cos(theta)) ** .4
    return ((WIDTH(position) - .034) * fraction, position, BELT(position) + (CROWN(position) - BELT(position)) * height)


def front_header(theta):
    ratio = max(0, (abs(theta) - .66) / (math.pi / 2 - .66))
    return .23 + .70 * ratio


def rear_header(theta):
    ratio = max(0, (abs(theta) - .66) / (math.pi / 2 - .66))
    return -.83 - .65 * ratio


def rear_divider(theta):
    ratio = max(0, (abs(theta) - .71) / (math.pi / 2 - .71))
    return -.72 - .30 * ratio


def canopy_strip(name, theta_start, theta_end, lower, upper, material_name, columns=20, rows=48, outward=(0, 0, 1)):
    def surface(horizontal, vertical):
        theta = theta_start + (theta_end - theta_start) * horizontal
        start = lower(theta) if callable(lower) else lower
        end = upper(theta) if callable(upper) else upper
        return canopy(theta, start + (end - start) * vertical)
    return patch(name, surface, columns, rows, material_name, 'QCOMET_GLASS', .003, outward)


def build_canopy():
    material('qcomet_glass_clear_v011', (.28, .32, .30), .065, transmission=1)
    material('qcomet_glass_roof_v011', (.016, .021, .019), .105, transmission=.35)
    material('qcomet_blackout_v011', (.009, .012, .011), .23, metallic=.20)
    for name in ['greenhouse_blackout', 'glass_side_dside', 'glass_side_pside']:
        retire(name)
    canopy_strip('panoramic_glass_greenhouse', -.66, .66, -.819, .219, 'qcomet_glass_roof_v011', 40, 52)
    canopy_strip('windscreen', -math.pi / 2, math.pi / 2, lambda theta: front_header(theta) + (.010 if abs(theta) < .71 else .023), .970, 'qcomet_glass_clear_v011', 72, 28)
    canopy_strip('glass_rear', -math.pi / 2, math.pi / 2, -1.545, lambda theta: rear_header(theta) - (.010 if abs(theta) < .71 else .023), 'qcomet_glass_clear_v011', 72, 26)
    canopy_strip('canopy_front_header', -.71, .71, lambda theta: front_header(theta) - .009, lambda theta: front_header(theta) + .009, 'qcomet_blackout_v011', 40, 2)
    canopy_strip('canopy_rear_header', -.71, .71, lambda theta: rear_header(theta) - .009, lambda theta: rear_header(theta) + .009, 'qcomet_blackout_v011', 40, 2)
    canopy_strip('canopy_cowl_seal', -math.pi / 2, math.pi / 2, .970, .975, 'qcomet_blackout_v011', 72, 1)
    canopy_strip('canopy_rear_seal', -math.pi / 2, math.pi / 2, -1.55, -1.545, 'qcomet_blackout_v011', 72, 1)
    for side, sign in [('dside', -1), ('pside', 1)]:
        outward = (sign, 0, .15)
        canopy_strip('canopy_rail_' + side, sign * .66, sign * .71, rear_header, front_header, 'qcomet_blackout_v011', 3, 60, outward)
        canopy_strip('glass_' + side + '_f', sign * .716, sign * 1.57065, -.090, lambda theta: front_header(theta) - .023, 'qcomet_glass_clear_v011', 28, 40, outward)
        canopy_strip('pillar_b_' + side, sign * .71, sign * (math.pi / 2), -.145, -.095, 'qcomet_blackout_v011', 28, 2, outward)
        canopy_strip('glass_' + side + '_r', sign * .716, sign * 1.57065, lambda theta: rear_divider(theta) + .010, -.150, 'qcomet_glass_clear_v011', 28, 38, outward)
        canopy_strip('glass_quarter_' + side, sign * .716, sign * 1.57065, lambda theta: rear_header(theta) + .023, lambda theta: rear_divider(theta) - .010, 'qcomet_glass_clear_v011', 28, 18, outward)
        canopy_strip('quarter_divider_' + side, sign * .71, sign * (math.pi / 2), lambda theta: rear_divider(theta) - .008, lambda theta: rear_divider(theta) + .008, 'qcomet_blackout_v011', 28, 2, outward)
        canopy_strip('canopy_belt_seal_' + side, sign * 1.57068, sign * (math.pi / 2), rear_header, front_header, 'qcomet_blackout_v011', 3, 64, outward)
        for prefix, boundary in [('pillar_a_', front_header), ('pillar_c_', rear_header)]:
            canopy_strip(prefix + side, sign * .71, sign * (math.pi / 2), lambda theta, boundary=boundary: boundary(theta) - .020, lambda theta, boundary=boundary: boundary(theta) + .020, 'qcomet_blackout_v011', 28, 3, outward)
    print('CANOPY: shared C2 longitudinal profile and continuous superellipse cross-sections')


def arch_bottom(position):
    distance = min(abs(position - 1.5), abs(position + 1.5))
    if distance < .447:
        return .39 + math.sqrt(max(0, .447 ** 2 - distance ** 2))
    return .265


def side_surface(position, vertical, sign):
    bottom = arch_bottom(position)
    height = bottom + (BELT(position) - bottom) * vertical
    global_fraction = (height - .265) / (BELT(position) - .265)
    return (sign * (WIDTH(position) + SECTION(global_fraction)), position, height)


def top_surface(fraction, progression, rear=False):
    start = -1.55 if rear else .975
    corner = 1 - math.sqrt(max(0, 1 - fraction ** 2))
    end = -2.4 + .27 * corner if rear else 2.4 - .33 * corner
    position = start + (end - start) * progression
    crown = .018 * max(0, 1 - abs(fraction) ** 5) ** .2 * (1 - progression) ** 2
    dish = -.030 * math.sin(math.pi * progression) ** 2 * (1 - fraction ** 2)
    ridge = .026 * math.exp(-((abs(fraction) - .64) / .095) ** 2) * math.sin(math.pi * progression) ** 2
    return (fraction * (WIDTH(position) - .034), position, BELT(position) + crown + dish + ridge)


def hood_width(progression, rear=False):
    return .77 if rear else .77 - .16 * math.sin(math.pi * progression / 2) ** 1.2


def build_body():
    material('Paint_Primary', (.10, .125, .058), .36, metallic=.30)
    material('qcomet_wheelwell_v011', (.009, .010, .009), .8)
    for name in ['front_dimple_intake', 'front_splitter_bronze', 'skirt_kickup_l', 'skirt_kickup_r', 'boot_ducktail']:
        retire(name)
    for side, sign in [('dside', -1), ('pside', 1)]:
        boundaries = [
            ('quarter_' + side + '_r', lambda vertical: -2.13, lambda vertical: -1.02 - GAP / 2, 160),
            ('door_' + side + '_r', lambda vertical: -1.02 + GAP / 2, lambda vertical: -.13 - GAP / 2, 44),
            ('door_' + side + '_f', lambda vertical: -.13 + GAP / 2, lambda vertical: .95 - GAP / 2, 44),
            ('fender_' + side + '_f', lambda vertical: .95 + GAP / 2, lambda vertical: 2.07, 160),
        ]
        for name, lower, upper, columns in boundaries:
            patch(name, lambda horizontal, vertical, lower=lower, upper=upper, sign=sign: side_surface(lower(vertical) + (upper(vertical) - lower(vertical)) * horizontal, vertical, sign), columns, 24, 'Paint_Primary', outward=(sign, 0, 0))
        for label, center in [('f', 1.5), ('r', -1.5)]:
            def lip(horizontal, vertical, sign=sign, center=center):
                angle = math.radians(-17 + 214 * horizontal)
                radius = .445
                position = center + radius * math.cos(angle)
                height = .39 + radius * math.sin(angle)
                fraction = (height - .265) / (BELT(position) - .265)
                half_width = WIDTH(position) + SECTION(fraction)
                return (sign * (.68 + (half_width - .68) * vertical), position, height)
            patch('arch_return_' + side + '_' + label, lip, 100, 4, 'qcomet_wheelwell_v011', thickness=.003, outward=(sign, 0, 0))
        patch('skirt_' + side, lambda horizontal, vertical, sign=sign: (sign * (.904 + .045 * math.sin(math.pi * vertical / 2)), -1.04 + 2.08 * horizontal, .18 + .080 * vertical + .028 * math.sin(math.pi * horizontal) ** 4), 48, 6, 'Aero_Carbon', thickness=.014, outward=(sign, 0, 0))
        for label, position in [('f', .20), ('r', -.72)]:
            obj = bpy.data.objects.get('handle_' + side + '_' + label)
            if obj:
                archive(obj.name)
                center = sum((vertex.co for vertex in obj.data.vertices), Vector()) / len(obj.data.vertices)
                height = .925
                fraction = (height - .265) / (BELT(position) - .265)
                target = Vector((sign * (WIDTH(position) + SECTION(fraction) + .003), position, height))
                for vertex in obj.data.vertices:
                    vertex.co += target - center
                obj.data.materials.clear()
                obj.data.materials.append(bpy.data.materials['Trim_Bronze'])
    for rear, name in [(False, 'bonnet'), (True, 'boot')]:
        patch(name, lambda horizontal, vertical, rear=rear: top_surface((-1 + 2 * horizontal) * (hood_width(.008 + .865 * vertical, rear) - .002), .008 + .865 * vertical, rear), 40, 42, 'Paint_Primary')
        prefix = 'rear_deck' if rear else 'hood'
        for side, sign in [('dside', -1), ('pside', 1)]:
            patch(prefix + '_shoulder_' + side, lambda horizontal, vertical, rear=rear, sign=sign: top_surface(sign * (hood_width(vertical, rear) + .002 + (1 - hood_width(vertical, rear) - .002) * horizontal), vertical, rear), 20, 64, 'Paint_Primary')
        patch(prefix + '_leading_band', lambda horizontal, vertical, rear=rear: top_surface((-1 + 2 * horizontal) * (hood_width(.878 + .122 * vertical, rear) + .002), .878 + .122 * vertical, rear), 48, 8, 'Paint_Primary')
        patch(prefix + '_cowl_band', lambda horizontal, vertical, rear=rear: top_surface((-1 + 2 * horizontal) * (hood_width(.004 * vertical, rear) + .002), .004 * vertical, rear), 48, 1, 'Paint_Primary')
    for rear, name in [(False, 'bumper_f'), (True, 'rear_bumper')]:
        def bumper(horizontal, vertical, rear=rear):
            fraction = -1 + 2 * horizontal
            upper = top_surface(fraction, 1, rear)
            height = .265 + (upper[2] - .265) * vertical
            half_width = WIDTH(upper[1]) + SECTION(vertical)
            bulge = .025 * math.sin(math.pi * vertical) * (1 - fraction ** 2)
            return (fraction * half_width, upper[1] + (-bulge if rear else bulge), height)
        patch(name, bumper, 72, 26, 'Paint_Primary', outward=(0, -1 if rear else 1, 0))
    vertices = [(-.83, -1.95, .18), (.83, -1.95, .18), (.83, 1.95, .18), (-.83, 1.95, .18)]
    mesh_object('chassis', vertices, [(0, 1, 2, 3)], 'Aero_Carbon', thickness=.025, outward=(0, 0, -1))
    print('BODY: four independent door skins, four wheel quarters, matched hood/deck/fascia profiles')


def record_manifest():
    REVIEW.mkdir(parents=True, exist_ok=True)
    manifest = {
        'source_files': ['q comet all four sides.png', 'q comet front rear top.png', 'Q Comet Front view showroom.png'],
        'primary_view': 'side silhouette for canopy; front/rear/top for continuity',
        'source_policy': 'Concept illustrations, not calibrated CAD; no exact pixel-fit claim.',
        'structural_parts': ['four doors', 'four fender/quarter skins', 'bonnet', 'boot', 'windshield', 'panoramic roof', 'rear glass', 'four door windows', 'four unchanged seat placeholders'],
        'expected_primary_parts': {'doors': 4, 'seats': 4, 'wheels': 4},
        'decorative_parts': ['existing original Q+ badges', 'existing lamps and wheels', 'black canopy seals'],
        'texture_regions': [],
        'validation_thresholds': {'symmetry_error_m_max': .0001, 'canopy_master_boundary_error_m_max': .00001, 'degenerate_faces': 0, 'dimensions_approved': False},
        'dimensions_policy': 'Retain scene wheel centers and provisional package; project.json unchanged.',
        'scope': 'Exterior surfacing review; no game export, rigging, collision, production UV or seat certification',
    }
    (REVIEW / 'reference_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')


def fascia_position(horizontal, height, rear=False):
    fraction = horizontal / .91
    for iteration in range(5):
        corner = 1 - math.sqrt(max(0, 1 - fraction ** 2))
        position = -2.4 + .27 * corner if rear else 2.4 - .33 * corner
        vertical = float(np.clip((height - .265) / (BELT(position) - .265), 0, 1))
        fraction = horizontal / (WIDTH(position) + SECTION(vertical))
    bulge = .025 * math.sin(math.pi * vertical) * (1 - fraction ** 2)
    return position + (-bulge if rear else bulge)


def original_vertices(obj):
    archive(obj.name)
    baseline = bpy.data.objects.get('v010_' + obj.name)
    return [vertex.co.copy() for vertex in (baseline or obj).data.vertices]


def fit_details():
    for obj in list(bpy.context.scene.objects):
        if obj.name.startswith('door_card_'):
            coordinates = original_vertices(obj)
            sign = -1 if 'dside' in obj.name else 1
            for vertex, coordinate in zip(obj.data.vertices, coordinates):
                fraction = (coordinate.z - .265) / (BELT(coordinate.y) - .265)
                limit = WIDTH(coordinate.y) + SECTION(fraction) - .018
                vertex.co = (sign * min(abs(coordinate.x) - .05, limit), coordinate.y, coordinate.z)
        if obj.name.startswith('mirror_') and obj.name.endswith('_stalk'):
            sign = -1 if 'dside' in obj.name else 1
            for vertex, coordinate in zip(obj.data.vertices, original_vertices(obj)):
                attachment = WIDTH(coordinate.y) - .034
                fraction = (abs(coordinate.x) - .97) / .05
                vertex.co = (sign * (attachment + (1.02 - attachment) * fraction), coordinate.y, coordinate.z)
        if obj.name.startswith('headlight_') and '_blade_' in obj.name:
            for vertex, coordinate in zip(obj.data.vertices, original_vertices(obj)):
                horizontal = coordinate.x
                progression = (abs(horizontal) - .48) / .38
                height = .681 + .062 * progression + (coordinate.z - .66) * (.20 + .50 * progression)
                residual = coordinate.y - (2.345 - .48 * (abs(horizontal) - .48))
                vertex.co = (horizontal, fascia_position(horizontal, height) + .012 + residual * .25, height)
        if obj.name in ['tail_bar_running', 'tail_bar_brake']:
            for vertex, coordinate in zip(obj.data.vertices, original_vertices(obj)):
                vertex.co = (coordinate.x, fascia_position(coordinate.x, coordinate.z, True) - .012 + (coordinate.y + 2.29) * .3, coordinate.z)
        if obj.name.startswith('badge_'):
            rear = obj.name == 'badge_rear'
            coordinates = original_vertices(obj)
            center = sum((coordinate.y for coordinate in coordinates)) / len(coordinates)
            target = fascia_position(0, .65, rear) + (-.012 if rear else .012)
            for vertex, coordinate in zip(obj.data.vertices, coordinates):
                vertex.co = (coordinate.x, coordinate.y - center + target, coordinate.z)
    for side, sign in [('dside', -1), ('pside', 1)]:
        def lamp(horizontal, vertical, sign=sign):
            lateral = sign * (.46 + .415 * horizontal)
            height = .650 + .020 * horizontal + (.059 + .075 * horizontal) * vertical
            return (lateral, fascia_position(lateral, height) + .004, height)
        patch('headlight_' + side + '_housing', lamp, 32, 8, 'qcomet_blackout_v011', 'QCOMET_LIGHTS', .005, (0, 1, 0))
        def pocket(horizontal, vertical, sign=sign):
            lateral = sign * (.772 + .125 * horizontal)
            height = .265 + .320 * vertical
            return (lateral, fascia_position(lateral, height) + .004, height)
        patch('front_intake_pocket_' + side, pocket, 10, 16, 'Aero_Carbon', thickness=.004, outward=(0, 1, 0))
        obj = bpy.data.objects.get('drl_' + side)
        for vertex, coordinate in zip(obj.data.vertices, original_vertices(obj)):
            vertex.co = (coordinate.x, fascia_position(coordinate.x, coordinate.z) + .011 + (coordinate.y - 2.308) * .4, coordinate.z)
        for trim in [False, True]:
            name = ('fender_vent_bronze_' if trim else 'fender_vent_') + side
            def vent(horizontal, vertical, sign=sign, trim=trim):
                position = .978 + .182 * horizontal
                height = .710 + (.005 if trim else .030) * vertical
                fraction = (height - .265) / (BELT(position) - .265)
                return (sign * (WIDTH(position) + SECTION(fraction) + .003), position, height)
            patch(name, vent, 12, 2, 'Trim_Bronze' if trim else 'Aero_Carbon', thickness=.003, outward=(sign, 0, 0))
    patch('tail_lens', lambda horizontal, vertical: (-.86 + 1.72 * horizontal, fascia_position(-.86 + 1.72 * horizontal, .731 + .131 * vertical, True) - .004, .731 + .131 * vertical), 80, 8, 'qcomet_blackout_v011', 'QCOMET_LIGHTS', .004, (0, -1, 0))
    for rear, name in [(False, 'front_splitter'), (True, 'rear_diffuser')]:
        def aero(horizontal, vertical, rear=rear):
            lateral = -.936 + 1.872 * horizontal
            height = .193 + (.145 if rear else .033) * vertical
            position = fascia_position(lateral * .96, .265, rear)
            reach = .025 + .065 * (1 - vertical)
            return (lateral, position + (-reach if rear else reach), height)
        patch(name, aero, 72, 8, 'Aero_Carbon', thickness=.015, outward=(0, -1 if rear else 1, .4))
        def bronze(horizontal, vertical, rear=rear):
            lateral = -.928 + 1.856 * horizontal
            height = .190 + .005 * vertical
            position = fascia_position(lateral * .96, .265, rear)
            return (lateral, position + (-.093 if rear else .093), height)
        patch('rear_diffuser_bronze' if rear else 'front_splitter_bronze', bronze, 72, 1, 'Trim_Bronze', thickness=.004, outward=(0, -1 if rear else 1, .4))
    for obj in list(bpy.context.scene.objects):
        if obj.name.startswith('diffuser_strake_'):
            coordinates = original_vertices(obj)
            for vertex, coordinate in zip(obj.data.vertices, coordinates):
                vertex.co = (coordinate.x, -2.30 + (coordinate.y + 2.3) * .30, .14 + (coordinate.z - .14) * .45)
            obj.data.materials.clear()
            obj.data.materials.append(bpy.data.materials['Aero_Carbon'])
    def lower_intake(horizontal, vertical):
        fraction = -1 + 2 * horizontal
        lateral = .936 * fraction
        lower = Vector((lateral, fascia_position(lateral * .96, .265) + .025, .226))
        position = 2.4 - .33 * (1 - math.sqrt(max(0, 1 - fraction ** 2)))
        upper = Vector((fraction * (WIDTH(position) + SECTION(0)), position, .267))
        return lower.lerp(upper, vertical)
    patch('front_lower_intake_return', lower_intake, 72, 6, 'Aero_Carbon', thickness=.006, outward=(0, 1, .2))
    vertices, faces = [], []
    for row in range(5):
        for column in range(33):
            horizontal = (column - 16) * .035 + (row % 2) * .012
            height = .421 + row * .027 + .018 * (horizontal / .6) ** 2
            if abs(horizontal) > .585 - .023 * row:
                continue
            start = len(vertices)
            for corner in range(8):
                angle = math.tau * corner / 8
                lateral = horizontal + .010 * math.cos(angle)
                elevation = height + .006 * math.sin(angle)
                vertices.append((lateral, fascia_position(lateral, elevation) + .002, elevation))
            faces.append(tuple(range(start, start + 8)))
    mesh_object('front_dimple_intake', vertices, faces, 'qcomet_blackout_v011', thickness=.001, outward=(0, 1, 0))
    print('DETAILS: door cards inset; original light blades and badges fitted to curved fascia')


def save_work():
    scene = bpy.context.scene
    scene['qcomet_status'] = 'BODY_V011_SURFACING_REVIEW_NOT_GAME_READY'
    scene['qcomet_working_file'] = str(OUTPUT / 'qcomet_body_v011.blend')
    scene['qcomet_source_body'] = 'qcomet_body_v010.blend'
    scene['qcomet_canopy_method'] = 'Cubic longitudinal crown with shared superellipse transverse master'
    scene['qcomet_dimension_approval'] = 'PENDING_QUASAR'
    scene['qcomet_changed_objects'] = json.dumps(sorted(set(CHANGED)))
    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT / 'qcomet_body_v011.blend'))


def main(stage='all'):
    if Path(bpy.data.filepath).stem not in {'qcomet_body_v010', 'qcomet_body_v011', 'qcomet_checkpoint_v010'}:
        raise RuntimeError('Open the preserved Q Comet v010 or v011 scene before running this recipe.')
    record_manifest()
    if stage in ('canopy', 'all'):
        build_canopy()
    if stage in ('body', 'all'):
        build_body()
    if stage in ('details', 'all'):
        fit_details()
    if stage == 'save':
        save_work()
    bpy.context.view_layer.update()


if __name__ == '__main__':
    main()
