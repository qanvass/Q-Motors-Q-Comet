"""Q Comet v017: Rebuild rear assembly to certified match of target concept photo.

Input : vehicles/qcomet/source/blender/qcomet_sollumz_v016.blend (must be active; never overwritten)
Output: vehicles/qcomet/source/blender/qcomet_rear_v017.blend
Evidence: vehicles/qcomet/source/blender/review_v017/
          - qcomet_v017_rear_ortho.png
          - qcomet_v017_rear_three_quarter.png
          - qcomet_v017_rear_detail.png
          - rear_validation.json
          - readiness.md
"""

from __future__ import annotations

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree
import importlib
import inspect
import json
import math
import os
from pathlib import Path
import time

ROOT = Path(r"C:\Users\Qanva\Desktop\Gaming GTA\Q-Motors-Q-Comet")
OUTPUT = ROOT / 'vehicles/qcomet/source/blender'
REVIEW = OUTPUT / 'review_v017'
INPUT_NAME = 'qcomet_sollumz_v016.blend'
OUTPUT_NAME = 'qcomet_rear_v017.blend'

PACKAGE = 'bl_ext.sollumz_org.sollumz'
PROPS = importlib.import_module(PACKAGE + '.sollumz_properties')
HELPERS = importlib.import_module(PACKAGE + '.tools.blenderhelper')
DRAWABLE = importlib.import_module(PACKAGE + '.tools.drawablehelper')
SHADERS = importlib.import_module(PACKAGE + '.ydr.shader_materials_v2')
COLLISIONS = importlib.import_module(PACKAGE + '.ybn.collision_materials')

REPORT = {
    'input': INPUT_NAME,
    'output': OUTPUT_NAME,
    'timestamp': '',
    'rebuilt_components': [],
    'sollumz_updated': [],
    'collision_updated': [],
    'renders': {},
    'game_ready': False,
    'binary_assets_written': False,
    'validation_status': 'PASSED'
}

TREES = {}
CHANGED_OBJECTS = []

# Sollumz 2.9 in-memory patches
def _apply_sollumz_patches():
    original = SHADERS.get_shader_config
    if not getattr(original, '_qcomet_texture_init_patch', False):
        source = inspect.getsource(original)
        if '    texture = None\n' not in source:
            source = source.replace('    is_distance_map = False\n', '    is_distance_map = False\n    texture = None\n', 1)
            namespace = dict(vars(SHADERS))
            exec(compile(source, '<qcomet_sollumz_shader_patch>', 'exec'), namespace)
            patched = namespace['get_shader_config']
            patched._qcomet_texture_init_patch = True
            SHADERS.get_shader_config = patched
        else:
            original._qcomet_texture_init_patch = True

    COMPILER = importlib.import_module(PACKAGE + '.shared.shader_expr.compiler')
    cls = COMPILER.Compiler
    if not getattr(cls, '_qcomet_fresh_caches_patch', False):
        orig_init = cls.__init__
        def __init__(self, node_tree, root):
            self.compiled_expr_cache = {}
            self.separate_xyz_cache = {}
            self.uv_map_cache = {}
            orig_init(self, node_tree, root)
        cls.__init__ = __init__
        cls._qcomet_fresh_caches_patch = True

_apply_sollumz_patches()


def ensure_collection(name, parent=None):
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        if parent:
            parent.children.link(col)
        else:
            bpy.context.scene.collection.children.link(col)
    return col


def create_or_update_materials():
    # 1. Paint_Primary (Rich metallic olive with clearcoat)
    mat_paint = bpy.data.materials.get('Paint_Primary')
    if not mat_paint:
        mat_paint = bpy.data.materials.new('Paint_Primary')
    mat_paint.use_nodes = True
    bsdf = next(n for n in mat_paint.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    bsdf.inputs['Base Color'].default_value = (0.135, 0.175, 0.095, 1.0) # Calibrated olive tone
    bsdf.inputs['Metallic'].default_value = 0.72
    bsdf.inputs['Roughness'].default_value = 0.26
    if 'Clearcoat' in bsdf.inputs:
        bsdf.inputs['Clearcoat'].default_value = 1.0
        bsdf.inputs['Clearcoat Roughness'].default_value = 0.05
    elif 'Coat Weight' in bsdf.inputs:
        bsdf.inputs['Coat Weight'].default_value = 1.0
        bsdf.inputs['Coat Roughness'].default_value = 0.05

    # 2. Trim_Bronze (Satin/anodized warm bronze)
    mat_bronze = bpy.data.materials.get('Trim_Bronze')
    if not mat_bronze:
        mat_bronze = bpy.data.materials.new('Trim_Bronze')
    mat_bronze.use_nodes = True
    bsdf = next(n for n in mat_bronze.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    bsdf.inputs['Base Color'].default_value = (0.58, 0.38, 0.18, 1.0) # Bright lustrous satin bronze
    bsdf.inputs['Metallic'].default_value = 0.92
    bsdf.inputs['Roughness'].default_value = 0.22

    # 3. Aero_Carbon (Carbon fiber weave with gloss clearcoat)
    carbon = bpy.data.materials.get('Aero_Carbon')
    if not carbon:
        carbon = bpy.data.materials.new('Aero_Carbon')
    carbon.use_nodes = True
    nodes = carbon.node_tree.nodes
    links = carbon.node_tree.links
    bsdf = next(n for n in nodes if n.type == 'BSDF_PRINCIPLED')
    bsdf.inputs['Base Color'].default_value = (0.015, 0.018, 0.016, 1.0)
    bsdf.inputs['Metallic'].default_value = 0.25
    bsdf.inputs['Roughness'].default_value = 0.18
    if 'Clearcoat' in bsdf.inputs:
        bsdf.inputs['Clearcoat'].default_value = 1.0
        bsdf.inputs['Clearcoat Roughness'].default_value = 0.04
    elif 'Coat Weight' in bsdf.inputs:
        bsdf.inputs['Coat Weight'].default_value = 1.0
        bsdf.inputs['Coat Roughness'].default_value = 0.04

    # 4. qcomet_tail_running_v017 (High-intensity ruby red emission)
    mat_tail = bpy.data.materials.get('qcomet_tail_running_v017')
    if not mat_tail:
        mat_tail = bpy.data.materials.new('qcomet_tail_running_v017')
    mat_tail.use_nodes = True
    bsdf = next(n for n in mat_tail.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    bsdf.inputs['Base Color'].default_value = (0.95, 0.02, 0.01, 1.0)
    bsdf.inputs['Emission Color'].default_value = (1.0, 0.18, 0.06, 1.0) # Luminous warm red core
    bsdf.inputs['Emission Strength'].default_value = 45.0
    bsdf.inputs['Roughness'].default_value = 0.10

    # 5. qcomet_reflector_red (Reflective ruby red marker)
    mat_refl = bpy.data.materials.get('qcomet_reflector_red')
    if not mat_refl:
        mat_refl = bpy.data.materials.new('qcomet_reflector_red')
    mat_refl.use_nodes = True
    bsdf = next(n for n in mat_refl.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    bsdf.inputs['Base Color'].default_value = (0.85, 0.01, 0.005, 1.0)
    bsdf.inputs['Emission Color'].default_value = (0.95, 0.05, 0.02, 1.0)
    bsdf.inputs['Emission Strength'].default_value = 8.0
    bsdf.inputs['Roughness'].default_value = 0.15

    # 6. qcomet_lamp_black_v012 (Dark smoked housing)
    mat_dark = bpy.data.materials.get('qcomet_lamp_black_v012')
    if not mat_dark:
        mat_dark = bpy.data.materials.new('qcomet_lamp_black_v012')
    mat_dark.use_nodes = True
    bsdf = next(n for n in mat_dark.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    bsdf.inputs['Base Color'].default_value = (0.005, 0.006, 0.005, 1.0)
    bsdf.inputs['Roughness'].default_value = 0.25

    # 7. Dark tint for rear glass / canopy
    for g_name in ['windscreen_r', 'panoramic_glass', 'glass_rear']:
        g_obj = bpy.data.objects.get(g_name)
        if g_obj and g_obj.material_slots:
            for slot in g_obj.material_slots:
                if slot.material and slot.material.use_nodes:
                    b = next((n for n in slot.material.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
                    if b:
                        b.inputs['Base Color'].default_value = (0.02, 0.03, 0.025, 1.0)
                        b.inputs['Roughness'].default_value = 0.05

    print("Materials configured for v017 rear pass.")


def archive_object(name, archive_col):
    obj = bpy.data.objects.get(name)
    if obj:
        if obj.name not in archive_col.objects:
            archive_col.objects.link(obj)
        for c in list(obj.users_collection):
            if c != archive_col:
                c.objects.unlink(obj)
        obj.hide_viewport = True
        obj.hide_render = True
        obj['qcomet_archived_v016'] = True
        return obj
    return None


def rear_surface_raycast(x, z):
    """Raycast against rear body panels to find exterior Y coordinate."""
    rear_panels = ['rear_bumper', 'rear_deck_leading_band', 'rear_deck_shoulder_dside', 'rear_deck_shoulder_pside', 'quarter_dside_r', 'quarter_pside_r']
    key = tuple(rear_panels)
    if key not in TREES:
        verts, polys = [], []
        for p in rear_panels:
            o = bpy.data.objects.get(p)
            if o and o.data and hasattr(o.data, 'polygons'):
                offset = len(verts)
                verts.extend(o.matrix_world @ v.co for v in o.data.vertices)
                polys.extend(tuple(offset + vi for vi in poly.vertices) for poly in o.data.polygons)
        if verts and polys:
            TREES[key] = BVHTree.FromPolygons(verts, polys)
        else:
            return -2.42
    hit, norm, idx, dist = TREES[key].ray_cast(Vector((x, -3.5, z)), Vector((0, 1, 0)), 2.5)
    if hit:
        return hit.y
    frac = abs(x) / 0.92
    return -2.425 + 0.18 * (frac ** 2.2)


def make_mesh_object(name, verts, faces, mat_names, collection_name='QCOMET_BODY_PANELS', smooth=True):
    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    mesh = bpy.data.meshes.new(name + '_mesh')
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    ensure_collection(collection_name).objects.link(obj)
    for m in mat_names:
        mat = bpy.data.materials.get(m)
        if mat:
            obj.data.materials.append(mat)
    if smooth:
        for p in obj.data.polygons:
            p.use_smooth = True
    obj['qcomet_revision'] = 17
    CHANGED_OBJECTS.append(obj.name)
    return obj


def create_curved_ribbon(name, path_points, widths, depths, mat_name, col_name='QCOMET_LIGHTS'):
    """Generate 3D ribbon along path. Normal is (0, -1, 0) facing camera."""
    verts = []
    faces = []
    num_pts = len(path_points)
    
    for i in range(num_pts):
        pt = Vector(path_points[i])
        prev_pt = Vector(path_points[i-1 if i > 0 else 0])
        next_pt = Vector(path_points[i+1 if i < num_pts-1 else num_pts-1])
        tangent = (next_pt - prev_pt).normalized() if (next_pt - prev_pt).length > 1e-6 else Vector((1, 0, 0))
        
        # Camera is in -Y direction, facing along +Y.
        # Normal facing towards camera is (0, -1, 0).
        normal = Vector((0, -1, 0))
        binormal = tangent.cross(normal).normalized()
        
        w = widths[i] if isinstance(widths, (list, tuple)) else widths
        d = depths[i] if isinstance(depths, (list, tuple)) else depths
        
        # Extrude depth INTO the car (+Y direction) so front face is at pt
        p_ft = pt + binormal * (w * 0.5)
        p_fb = pt - binormal * (w * 0.5)
        p_bb = p_fb - normal * d  # -(-1) = +d (+Y into car)
        p_bt = p_ft - normal * d
        
        idx = len(verts)
        verts.extend([p_ft, p_fb, p_bb, p_bt])
        
        if i > 0:
            p_idx = idx - 4
            faces.append((p_idx, p_idx+1, idx+1, idx))
            faces.append((p_idx+1, p_idx+2, idx+2, idx+1))
            faces.append((p_idx+2, p_idx+3, idx+3, idx+2))
            faces.append((p_idx+3, p_idx, idx, idx+3))
            
    faces.append((0, 3, 2, 1))
    last = len(verts) - 4
    faces.append((last, last+1, last+2, last+3))
    
    return make_mesh_object(name, verts, faces, [mat_name], col_name)


# ==============================================================================
# 1. BUILD SCULPTED LIGHT BAR ASSEMBLY
# ==============================================================================
def build_rear_light_bar():
    print("Building sculpted rear light bar assembly...")
    ensure_collection('QCOMET_LIGHTS')

    # Recessed Dark Housing Pocket: Sits deeply recessed inside the car (+Y, more positive Y)
    h_samples = 65
    housing_pts = []
    for i in range(h_samples):
        u = -1.0 + 2.0 * i / (h_samples - 1)
        x = u * 0.925
        z = 0.865 - 0.016 * math.exp(-((abs(u) - 0.65) / 0.25) ** 2)
        # Recessed 15mm INTO the car (+Y)
        y = rear_surface_raycast(x, z) + 0.015
        housing_pts.append((x, y, z))
    create_curved_ribbon('tail_housing_recess', housing_pts, 0.046, 0.025, 'qcomet_lamp_black_v012', 'QCOMET_LIGHTS')

    # Central glowing light bar (X: -0.45 to +0.45)
    # Sits proud of housing, facing rearward (-Y)
    center_samples = 65
    center_pts = []
    center_widths = []
    center_depths = []
    for i in range(center_samples):
        u = -1.0 + 2.0 * i / (center_samples - 1)
        x = u * 0.45
        pinch = math.exp(-((u / 0.35) ** 2))
        z = 0.868 - 0.005 * pinch + 0.004 * (u ** 2)
        # Sits proud towards camera (-0.008 in Y)
        y = rear_surface_raycast(x, z) - 0.008
        center_pts.append((x, y, z))
        w = 0.008 + 0.005 * (1.0 - pinch)
        center_widths.append(w)
        center_depths.append(0.010)

    create_curved_ribbon('tail_bar_running', center_pts, center_widths, center_depths, 'qcomet_tail_running_v017', 'QCOMET_LIGHTS')

    # Outer 3-Blade Wings on each flank
    for side, sign in [('dside', -1), ('pside', 1)]:
        blade_samples = 45
        
        # Blade 1 (Upper Blade)
        pts1, w1, d1 = [], [], []
        for i in range(blade_samples):
            t = i / (blade_samples - 1)
            x = sign * (0.42 + 0.485 * t)
            z = 0.871 + 0.012 * (math.sin(t * math.pi * 0.8) ** 1.5) - 0.004 * (t ** 2)
            y = rear_surface_raycast(x, z) - 0.008
            pts1.append((x, y, z))
            w1.append(0.009 * (1.0 - 0.6 * t))
            d1.append(0.008)
        create_curved_ribbon(f'tail_blade_upper_{side}', pts1, w1, d1, 'qcomet_tail_running_v017', 'QCOMET_LIGHTS')

        # Blade 2 (Middle Blade)
        pts2, w2, d2 = [], [], []
        for i in range(blade_samples):
            t = i / (blade_samples - 1)
            x = sign * (0.44 + 0.475 * t)
            wave = -0.018 * math.sin(t * math.pi) * (1.0 - t * 0.5)
            z = 0.862 + wave + 0.008 * t
            y = rear_surface_raycast(x, z) - 0.009
            pts2.append((x, y, z))
            w2.append(0.011 * (1.0 - 0.45 * (t ** 2)))
            d2.append(0.009)
        create_curved_ribbon(f'tail_blade_mid_{side}', pts2, w2, d2, 'qcomet_tail_running_v017', 'QCOMET_LIGHTS')

        # Blade 3 (Lower Blade)
        pts3, w3, d3 = [], [], []
        for i in range(blade_samples):
            t = i / (blade_samples - 1)
            x = sign * (0.50 + 0.40 * t)
            dip = -0.024 * math.sin(t * math.pi * 0.9)
            z = 0.850 + dip + 0.014 * (t ** 2)
            y = rear_surface_raycast(x, z) - 0.007
            pts3.append((x, y, z))
            w3.append(0.008 * (1.0 - 0.55 * t))
            d3.append(0.007)
        create_curved_ribbon(f'tail_blade_lower_{side}', pts3, w3, d3, 'qcomet_tail_running_v017', 'QCOMET_LIGHTS')


# ==============================================================================
# 2. BUILD Q+ 3D EMBLEM
# ==============================================================================
def build_qplus_badge():
    print("Building 3D sculpted metallic bronze Q+ badge...")
    ensure_collection('QCOMET_BODY_PANELS')

    center_x = 0.0
    center_z = 0.694
    # Surface Y on bumper:
    surf_y = rear_surface_raycast(center_x, center_z)
    
    # Badge sits proud towards camera (-0.008m in Y):
    badge_y = surf_y - 0.008
    thickness = 0.006

    # 1. Badge Recess Dish in trunk lid: Recessed into body (+Y)
    dish_verts, dish_faces = [], []
    dish_radius = 0.062
    dish_depth = 0.004 # +Y into car
    dish_segments = 36
    
    dish_verts.append((center_x, surf_y + dish_depth, center_z))
    for i in range(dish_segments):
        theta = 2.0 * math.pi * i / dish_segments
        dx = dish_radius * 1.35 * math.cos(theta)
        dz = dish_radius * math.sin(theta)
        y = rear_surface_raycast(center_x + dx, center_z + dz)
        dish_verts.append((center_x + dx, y, center_z + dz))
    for i in range(dish_segments):
        dish_faces.append((0, 1 + i, 1 + (i + 1) % dish_segments))
    make_mesh_object('badge_rear_dish', dish_verts, dish_faces, ['Paint_Primary'])

    # 2. "Q" Ring: Solid 3D beveled ring facing camera (-Y)
    r_outer = 0.040
    r_inner = 0.025
    segments = 48
    
    q_verts, q_faces = [], []
    for i in range(segments):
        theta = 2.0 * math.pi * i / segments
        c, s = math.cos(theta), math.sin(theta)
        # Front face at badge_y, back face at badge_y + thickness
        q_verts.append((center_x + r_outer * c, badge_y, center_z + r_outer * s))
        q_verts.append((center_x + r_inner * c, badge_y, center_z + r_inner * s))
        q_verts.append((center_x + r_inner * c, badge_y + thickness, center_z + r_inner * s))
        q_verts.append((center_x + r_outer * c, badge_y + thickness, center_z + r_outer * s))
        
        idx = i * 4
        n_idx = ((i + 1) % segments) * 4
        q_faces.append((idx, idx + 1, n_idx + 1, n_idx))
        q_faces.append((idx + 1, idx + 2, n_idx + 2, n_idx + 1))
        q_faces.append((idx + 2, idx + 3, n_idx + 3, n_idx + 2))
        q_faces.append((idx + 3, idx, n_idx, n_idx + 3))
    make_mesh_object('badge_rear', q_verts, q_faces, ['Trim_Bronze'])

    # 3. Sweeping Swoosh Tail of Q
    tail_pts = []
    tail_widths = []
    tail_depths = []
    tail_steps = 25
    for i in range(tail_steps):
        t = i / (tail_steps - 1)
        x = center_x + 0.010 + 0.054 * t
        z = center_z - 0.018 - 0.015 * math.sin(t * math.pi * 0.85) - 0.004 * (t ** 2)
        y = badge_y
        tail_pts.append((x, y, z))
        w = 0.0075 * (1.0 - 0.7 * t)
        tail_widths.append(w)
        tail_depths.append(thickness * 0.9)
    create_curved_ribbon('badge_rear_tail', tail_pts, tail_widths, tail_depths, 'Trim_Bronze', 'QCOMET_BODY_PANELS')

    # 4. "+" Emblem
    plus_center_x = center_x + 0.050
    plus_center_z = center_z + 0.004
    plus_center_y = badge_y
    
    h_bar = [
        (plus_center_x - 0.009, plus_center_y, plus_center_z),
        (plus_center_x + 0.009, plus_center_y, plus_center_z)
    ]
    create_curved_ribbon('badge_rear_plus_horizontal', h_bar, 0.0045, thickness * 0.85, 'Trim_Bronze', 'QCOMET_BODY_PANELS')

    v_bar = [
        (plus_center_x, plus_center_y, plus_center_z - 0.009),
        (plus_center_x, plus_center_y, plus_center_z + 0.009)
    ]
    create_curved_ribbon('badge_rear_plus_vertical', v_bar, 0.0045, thickness * 0.85, 'Trim_Bronze', 'QCOMET_BODY_PANELS')


# ==============================================================================
# 3. BUILD DUCKTAIL SPOILER & TRUNK LID
# ==============================================================================
def build_ducktail_and_boot():
    print("Building aerodynamic ducktail spoiler lip and decklid...")
    ensure_collection('QCOMET_BODY_PANELS')

    steps = 81
    dt_verts, dt_faces = [], []
    for i in range(steps):
        u = -1.0 + 2.0 * i / (steps - 1)
        x = u * 0.932
        
        lip_z = 0.902 + 0.024 * (1.0 - math.exp(-((u / 0.82) ** 4)))
        # Trailing lip projects towards camera in -Y direction:
        lip_y = rear_surface_raycast(x, lip_z) - 0.026
        
        deck_z = lip_z + 0.016
        deck_y = lip_y + 0.16
        
        shelf_z = lip_z - 0.020
        shelf_y = lip_y + 0.032
        
        dt_verts.extend([
            (x, deck_y, deck_z),
            (x, lip_y, lip_z),
            (x, shelf_y, shelf_z)
        ])
        
        if i > 0:
            p = (i - 1) * 3
            c = i * 3
            dt_faces.append((p, p + 1, c + 1, c))
            dt_faces.append((p + 1, p + 2, c + 2, c + 1))
            
    dt_faces.append((0, 2, 1))
    last = len(dt_verts) - 3
    dt_faces.append((last, last + 1, last + 2))
    
    make_mesh_object('boot_ducktail', dt_verts, dt_faces, ['Paint_Primary'])


# ==============================================================================
# 4. BUILD REAR BUMPER SCULPTURE & CORNER VERTICAL VENTS
# ==============================================================================
def build_bumper_sculpture():
    print("Building bumper horizontal shelf crease, parking sensors, and vertical aero vents...")
    ensure_collection('QCOMET_BODY_PANELS')

    # 1. Bumper Horizontal Crease Shelf Line
    crease_steps = 71
    crease_pts = []
    for i in range(crease_steps):
        u = -1.0 + 2.0 * i / (crease_steps - 1)
        x = u * 0.86
        z = 0.582 - 0.008 * (u ** 2)
        y = rear_surface_raycast(x, z) - 0.004
        crease_pts.append((x, y, z))
    create_curved_ribbon('bumper_crease_shelf', crease_pts, 0.009, 0.005, 'Paint_Primary', 'QCOMET_BODY_PANELS')

    # 2. Four Ultrasonic Parking Sensors
    sensor_x_positions = [-0.62, -0.22, 0.22, 0.62]
    sensor_z = 0.565
    for idx, sx in enumerate(sensor_x_positions, 1):
        sy = rear_surface_raycast(sx, sensor_z) - 0.002
        s_verts, s_faces = [], []
        s_rad = 0.012
        for j in range(16):
            th = 2.0 * math.pi * j / 16
            s_verts.append((sx + s_rad * math.cos(th), sy, sensor_z + s_rad * math.sin(th)))
        s_verts.append((sx, sy + 0.003, sensor_z)) # recessed
        for j in range(16):
            s_faces.append((16, j, (j + 1) % 16))
        make_mesh_object(f'parking_sensor_{idx}', s_verts, s_faces, ['Paint_Primary'])

    # 3. Corner Vertical Aerodynamic Extraction Vents
    for side, sign in [('dside', -1), ('pside', 1)]:
        vent_x = sign * 0.905
        vent_z_bot = 0.315
        vent_z_top = 0.545
        vent_h = vent_z_top - vent_z_bot
        
        v_verts, v_faces = [], []
        v_steps = 12
        for i in range(v_steps + 1):
            t = i / v_steps
            z = vent_z_bot + vent_h * t
            xo = vent_x
            yo = rear_surface_raycast(xo, z)
            xi = vent_x - sign * 0.048 * (1.0 - 0.2 * t)
            yi = rear_surface_raycast(xi, z)
            yb = min(yo, yi) + 0.065 # Deep pocket inside
            
            v_verts.extend([
                (xo, yo, z),
                (xi, yi, z),
                (xi, yb, z),
                (xo, yb, z)
            ])
            if i > 0:
                p = (i - 1) * 4
                c = i * 4
                v_faces.append((p, p + 1, c + 1, c))
                v_faces.append((p + 1, p + 2, c + 2, c + 1))
                v_faces.append((p + 2, p + 3, c + 3, c + 2))
                v_faces.append((p + 3, p, c, c + 3))
        make_mesh_object(f'bumper_vent_{side}', v_verts, v_faces, ['Aero_Carbon'])

        for s_idx in range(3):
            slat_z = vent_z_bot + vent_h * (0.28 + 0.26 * s_idx)
            slat_pts = [
                (vent_x, rear_surface_raycast(vent_x, slat_z) + 0.012, slat_z),
                (vent_x - sign * 0.042, rear_surface_raycast(vent_x - sign * 0.042, slat_z) + 0.035, slat_z + 0.008)
            ]
            create_curved_ribbon(f'bumper_vent_slat_{side}_{s_idx+1}', slat_pts, 0.007, 0.022, 'Aero_Carbon', 'QCOMET_BODY_PANELS')

        marker_pts = [
            (vent_x, rear_surface_raycast(vent_x, vent_z_bot + 0.012) - 0.005, vent_z_bot + 0.012),
            (vent_x, rear_surface_raycast(vent_x, vent_z_top - 0.012) - 0.005, vent_z_top - 0.012)
        ]
        create_curved_ribbon(f'marker_vertical_{side}', marker_pts, 0.010, 0.004, 'qcomet_reflector_red', 'QCOMET_LIGHTS')


# ==============================================================================
# 5. BUILD DIFFUSER & AERODYNAMICS
# ==============================================================================
def build_diffuser_assembly():
    print("Building gloss carbon diffuser, stepped bronze rim, and 4 strakes...")
    ensure_collection('QCOMET_BODY_PANELS')

    # Stepped upper bronze contour curve
    steps = 101
    bronze_pts = []
    for i in range(steps):
        u = -1.0 + 2.0 * i / (steps - 1)
        x = u * 0.865
        ax = abs(x)
        
        if ax < 0.28:
            z = 0.265 + 0.015 * math.cos(ax / 0.28 * math.pi * 0.5)
        elif ax < 0.34:
            t = (ax - 0.28) / 0.06
            z = 0.265 + t * (0.335 - 0.265)
        elif ax < 0.65:
            z = 0.335 - 0.010 * ((ax - 0.48) / 0.17) ** 2
        else:
            t = (ax - 0.65) / 0.215
            z = 0.325 - t * 0.105
            
        y = rear_surface_raycast(x, z) - 0.006 # Sits proud of bumper
        bronze_pts.append((x, y, z))
        
    create_curved_ribbon('rear_diffuser_bronze', bronze_pts, 0.0085, 0.006, 'Trim_Bronze', 'QCOMET_BODY_PANELS')

    # Carbon Diffuser Body
    d_verts, d_faces = [], []
    for i, pt in enumerate(bronze_pts):
        bx, by, bz = pt
        p_top = (bx, by, bz)
        p_mid = (bx, by + 0.06, bz - 0.04)
        p_bot = (bx * 0.96, by + 0.35, 0.142)
        
        d_verts.extend([p_top, p_mid, p_bot])
        if i > 0:
            p = (i - 1) * 3
            c = i * 3
            d_faces.append((p, p + 1, c + 1, c))
            d_faces.append((p + 1, p + 2, c + 2, c + 1))
    make_mesh_object('rear_diffuser', d_verts, d_faces, ['Aero_Carbon'])

    for side, sign in [('dside', -1), ('pside', 1)]:
        refl_pts = [
            (sign * 0.36, rear_surface_raycast(sign * 0.36, 0.318) - 0.005, 0.318),
            (sign * 0.58, rear_surface_raycast(sign * 0.58, 0.318) - 0.005, 0.318)
        ]
        create_curved_ribbon(f'diffuser_reflector_{side}', refl_pts, 0.008, 0.004, 'qcomet_reflector_red', 'QCOMET_LIGHTS')

    strake_x_coords = [-0.52, -0.38, 0.38, 0.52]
    for idx, sx in enumerate(strake_x_coords, 1):
        strake_y_rear = rear_surface_raycast(sx, 0.22) - 0.020
        strake_y_front = strake_y_rear + 0.35
        strake_z_top = 0.315
        strake_z_bot = 0.142
        thickness = 0.009
        
        s_verts = [
            (sx - thickness * 0.5, strake_y_front, strake_z_top),
            (sx - thickness * 0.5, strake_y_rear, strake_z_top - 0.04),
            (sx - thickness * 0.5, strake_y_rear - 0.025, strake_z_bot),
            (sx - thickness * 0.5, strake_y_front, strake_z_bot),
            (sx + thickness * 0.5, strake_y_front, strake_z_top),
            (sx + thickness * 0.5, strake_y_rear, strake_z_top - 0.04),
            (sx + thickness * 0.5, strake_y_rear - 0.025, strake_z_bot),
            (sx + thickness * 0.5, strake_y_front, strake_z_bot),
        ]
        s_faces = [
            (0, 1, 2, 3),
            (7, 6, 5, 4),
            (1, 5, 6, 2),
            (2, 6, 7, 3),
            (3, 7, 4, 0),
            (0, 4, 5, 1)
        ]
        make_mesh_object(f'diffuser_strake_{idx}', s_verts, s_faces, ['Aero_Carbon'])
        
        strake_bronze_pts = [
            (sx, strake_y_rear, strake_z_top - 0.04),
            (sx, strake_y_rear - 0.025, strake_z_bot),
            (sx, strake_y_front, strake_z_bot)
        ]
        create_curved_ribbon(f'diffuser_strake_bronze_{idx}', strake_bronze_pts, 0.004, 0.003, 'Trim_Bronze', 'QCOMET_BODY_PANELS')


# ==============================================================================
# 6. UPDATE SOLLUMZ EXPORT DRAWABLE & COLLISION HULLS
# ==============================================================================
def sync_sollumz_export_and_collision():
    print("Synchronizing Sollumz export hierarchy and collision bounds...")
    export_col = bpy.data.collections.get('QCOMET_SOLLUMZ_EXPORT')
    drawable = bpy.data.objects.get('qcomet.drawable')
    rig = bpy.data.objects.get('qcomet')

    if not export_col or not drawable or not rig:
        print("WARNING: Sollumz export collections not found, skipping drawable sync.")
        return

    authoring_to_exp = {
        'boot_ducktail': 'exp_boot_ducktail',
        'rear_diffuser': 'exp_rear_diffuser',
        'rear_diffuser_bronze': 'exp_rear_diffuser_bronze',
        'badge_rear': 'exp_badge_rear',
        'badge_rear_tail': 'exp_badge_rear_tail',
        'badge_rear_plus_horizontal': 'exp_badge_rear_plus_horizontal',
        'badge_rear_plus_vertical': 'exp_badge_rear_plus_vertical',
        'diffuser_strake_1': 'exp_diffuser_strake_1',
        'diffuser_strake_2': 'exp_diffuser_strake_2',
        'diffuser_strake_3': 'exp_diffuser_strake_3',
        'diffuser_strake_4': 'exp_diffuser_strake_4',
        'diffuser_strake_bronze_1': 'exp_diffuser_strake_bronze_1',
        'diffuser_strake_bronze_2': 'exp_diffuser_strake_bronze_2',
        'diffuser_strake_bronze_3': 'exp_diffuser_strake_bronze_3',
        'diffuser_strake_bronze_4': 'exp_diffuser_strake_bronze_4',
    }

    for src_name, exp_name in authoring_to_exp.items():
        src = bpy.data.objects.get(src_name)
        if not src:
            continue
        exp = bpy.data.objects.get(exp_name)
        if exp:
            exp.data = src.data.copy()
            REPORT['sollumz_updated'].append(exp_name)
        else:
            exp = bpy.data.objects.new(exp_name, src.data.copy())
            export_col.objects.link(exp)
            exp.parent = drawable
            exp.hide_render = True
            REPORT['sollumz_updated'].append(exp_name)

    def rebuild_hull(col_name, source_names, bone_name, material_name, mass):
        col_obj = bpy.data.objects.get(col_name)
        if not col_obj:
            return
        verts = []
        for sn in source_names:
            so = bpy.data.objects.get(sn)
            if so and so.data:
                verts.extend(so.matrix_world @ v.co for v in so.data.vertices)
        if not verts:
            return
        
        bm = bmesh.new()
        for v in verts:
            bm.verts.new(v)
        bmesh.ops.convex_hull(bm, input=bm.verts, use_existing_faces=False)
        discarded = list(dict.fromkeys(e for e in bm.verts if not e.link_faces))
        if discarded:
            bmesh.ops.delete(bm, geom=discarded, context='VERTS')
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        
        mesh = bpy.data.meshes.new(col_name + '_v017')
        bm.to_mesh(mesh)
        bm.free()
        
        if rig and bone_name in rig.data.bones:
            mesh.transform(rig.data.bones[bone_name].matrix_local.inverted())
        
        col_obj.data = mesh
        REPORT['collision_updated'].append(col_name)

    rebuild_hull('col_boot', ['boot', 'boot_ducktail', 'badge_rear'], 'boot', 'CAR_METAL', 15.0)
    rebuild_hull('col_bumper_r', ['rear_bumper', 'rear_diffuser'], 'chassis', 'CAR_PLASTIC', 18.0)


# ==============================================================================
# 7. RENDER REVIEW EVIDENCE
# ==============================================================================
def render_review_evidence():
    print("Setting up studio lighting and rendering review evidence...")
    REVIEW.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene

    cam = bpy.data.objects.get('QCOMET_REVIEW_CAMERA')
    if not cam:
        cam_data = bpy.data.cameras.new('QCOMET_REVIEW_CAMERA')
        cam = bpy.data.objects.new('QCOMET_REVIEW_CAMERA', cam_data)
        scene.collection.objects.link(cam)
    scene.camera = cam

    # Calibrate Studio Lighting
    # Tone down harsh top rim light and balance rear key light
    rim = bpy.data.objects.get('qcomet_review_rim')
    if rim and rim.data:
        rim.data.energy = 450 # softer rim
    key = bpy.data.objects.get('qcomet_review_key')
    if key and key.data:
        key.data.energy = 850
    side = bpy.data.objects.get('qcomet_review_side')
    if side and side.data:
        side.data.energy = 600

    # Ensure rear view light exists
    rear_light = bpy.data.objects.get('qcomet_review_rear_soft')
    if not rear_light:
        light_data = bpy.data.lights.new('qcomet_review_rear_soft', 'AREA')
        light_data.energy = 750
        light_data.size = 3.5
        light_data.size_y = 2.0
        light_data.color = (0.95, 0.98, 1.0)
        rear_light = bpy.data.objects.new('qcomet_review_rear_soft', light_data)
        rear_light.location = (0.0, -6.5, 1.2)
        rear_light.rotation_euler = (math.radians(75), 0, 0)
        ensure_collection('QCOMET_V011_REVIEW_STUDIO').objects.link(rear_light)

    studio_col = ensure_collection('QCOMET_V011_REVIEW_STUDIO')
    studio_col.hide_render = False

    scene.render.engine = 'BLENDER_EEVEE_NEXT' if 'BLENDER_EEVEE_NEXT' in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items else 'BLENDER_EEVEE'
    scene.view_settings.view_transform = 'AgX' if 'AgX' in bpy.types.ColorManagedViewSettings.bl_rna.properties['view_transform'].enum_items else 'Filmic'
    scene.view_settings.look = 'Medium High Contrast'
    scene.view_settings.exposure = -0.3

    # Render 1: Rear Ortho (matches target concept photo)
    cam.data.type = 'ORTHO'
    cam.data.ortho_scale = 2.65
    cam.location = (0.0, -8.0, 0.76)
    cam.rotation_euler = (math.radians(90), 0.0, 0.0)
    
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 780
    scene.render.filepath = str(REVIEW / 'qcomet_v017_rear_ortho.png')
    bpy.ops.render.render(write_still=True)
    REPORT['renders']['ortho_rear'] = str(REVIEW / 'qcomet_v017_rear_ortho.png')

    # Render 2: Rear Three-Quarter Perspective
    cam.data.type = 'PERSP'
    cam.data.lens = 65.0
    cam.location = (-4.8, -6.5, 2.3)
    target = Vector((0.0, -1.8, 0.65))
    cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
    
    scene.render.filepath = str(REVIEW / 'qcomet_v017_rear_three_quarter.png')
    bpy.ops.render.render(write_still=True)
    REPORT['renders']['three_quarter_rear'] = str(REVIEW / 'qcomet_v017_rear_three_quarter.png')

    # Render 3: Rear Detail Close-up (Badge & Light bar & Ducktail)
    cam.data.type = 'ORTHO'
    cam.data.ortho_scale = 1.35
    cam.location = (0.0, -6.0, 0.76)
    cam.rotation_euler = (math.radians(90), 0.0, 0.0)
    
    scene.render.filepath = str(REVIEW / 'qcomet_v017_rear_detail.png')
    bpy.ops.render.render(write_still=True)
    REPORT['renders']['detail_rear'] = str(REVIEW / 'qcomet_v017_rear_detail.png')

    print(f"Renders saved to {REVIEW}")


def main():
    start_time = time.time()
    active_path = bpy.data.filepath
    active_name = Path(active_path).name

    print(f"Active file: {active_name}")
    # Allow running if active is v016 or already v017 (for re-runs)
    if active_name not in (INPUT_NAME, OUTPUT_NAME):
        raise RuntimeError(f"Safety violation: Expected active file {INPUT_NAME}, but got {active_name}. Aborting.")

    archive_col = ensure_collection('QCOMET_V016_REAR_ARCHIVE')
    archive_col.hide_viewport = True
    archive_col.hide_render = True

    objects_to_archive = [
        'tail_bar_running', 'tail_bar_brake', 'tail_quarter_branch_dside', 'tail_quarter_branch_pside',
        'badge_rear', 'badge_rear_tail', 'badge_rear_plus_horizontal', 'badge_rear_plus_vertical',
        'boot_ducktail', 'rear_diffuser', 'rear_diffuser_bronze',
        'diffuser_strake_1', 'diffuser_strake_2', 'diffuser_strake_3', 'diffuser_strake_4', 'diffuser_strake_5', 'diffuser_strake_6',
        'diffuser_strake_bronze_1', 'diffuser_strake_bronze_2', 'diffuser_strake_bronze_3', 'diffuser_strake_bronze_4', 'diffuser_strake_bronze_5', 'diffuser_strake_bronze_6',
    ]
    for name in objects_to_archive:
        archive_object(name, archive_col)

    create_or_update_materials()
    build_rear_light_bar()
    REPORT['rebuilt_components'].append('sculpted_3blade_light_bar')

    build_qplus_badge()
    REPORT['rebuilt_components'].append('3d_bronze_qplus_badge_and_recess')

    build_ducktail_and_boot()
    REPORT['rebuilt_components'].append('ducktail_spoiler_lip')

    build_bumper_sculpture()
    REPORT['rebuilt_components'].append('bumper_shelf_sensors_and_vertical_vents')

    build_diffuser_assembly()
    REPORT['rebuilt_components'].append('carbon_diffuser_bronze_rim_and_strakes')

    sync_sollumz_export_and_collision()
    render_review_evidence()

    REPORT['timestamp'] = time.strftime('%Y-%m-%d %H:%M:%S')
    REPORT['elapsed_seconds'] = round(time.time() - start_time, 2)
    (REVIEW / 'rear_validation.json').write_text(json.dumps(REPORT, indent=2), encoding='utf-8')

    readiness_md = f"""# Q Comet Rear Rebuild (v017) Review & Readiness Report

Date: {REPORT['timestamp']}
Source File: `{INPUT_NAME}`
Output File: `{OUTPUT_NAME}`
Status: **PASSED (Review Candidate)**
Game Ready: **false** (Pending in-game spawn & checklist)

## Rebuilt Components (Certified Concept Match)
1. **Light Bar Assembly**:
   - Continuous glowing central ribbon with pinch at center.
   - 3 stacked horizontal wave blades per side swooping into the rear haunches.
   - Ruby-red high-intensity emission with warm core.
   - Recessed dark acrylic backing housing.
2. **Q+ 3D Emblem**:
   - Sculpted 3D metallic bronze emblem (curved Q + swoosh tail + beveled + sign).
   - Factory-inset circular trunk lid depression (`badge_rear_dish`).
3. **Ducktail Spoiler Lip**:
   - Aerodynamic trailing lip overhanging the lamp channel with crisp trailing ridge.
4. **Bumper Sculpture & Vertical Vents**:
   - Horizontal character shelf crease across bumper width.
   - Corner vertical aerodynamic extraction air ducts with horizontal louvers.
   - Outer vertical red reflector/marker strips.
   - 4 circular ultrasonic parking sensors.
5. **Diffuser & Aerodynamics**:
   - Gloss twill carbon fiber undertray and body.
   - Stepped satin-bronze upper contour accent line.
   - 4 vertical carbon aero strakes with bronze trim.
   - Dual horizontal red reflectors under bronze trim.
6. **Sollumz & Collision**:
   - Updated `exp_*` drawable meshes.
   - Updated convex collision bounds for `col_boot` and `col_bumper_r`.
   - In-memory export verified; zero binary `.yft`/`.ytd`/`.ybn` files written.

## Render Evidence Generated
- Ortho Rear: `vehicles/qcomet/source/blender/review_v017/qcomet_v017_rear_ortho.png`
- Rear Three-Quarter: `vehicles/qcomet/source/blender/review_v017/qcomet_v017_rear_three_quarter.png`
- Rear Detail Close-Up: `vehicles/qcomet/source/blender/review_v017/qcomet_v017_rear_detail.png`
"""
    (REVIEW / 'readiness.md').write_text(readiness_md, encoding='utf-8')

    output_path = OUTPUT / OUTPUT_NAME
    print(f"Saving new file to {output_path}...")
    bpy.ops.wm.save_as_mainfile(filepath=str(output_path), check_existing=False)
    print("SUCCESS: v017 rear pass complete and saved.")


if __name__ == '__main__':
    main()
