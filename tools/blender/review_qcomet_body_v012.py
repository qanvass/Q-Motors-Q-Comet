import json
import runpy
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[2]
REVIEW = ROOT / 'vehicles/qcomet/source/blender/review_v012'
VIEWS = {
    'front_three_quarter': ((6.2, 8.4, 3.6), (0, 0, .73), 5.9),
    'rear_three_quarter': ((-6.3, -8.2, 3.5), (0, 0, .73), 5.9),
    'side': ((8, 0, .75), (0, 0, .75), 5.55),
    'front': ((0, 8, .76), (0, 0, .76), 2.7),
    'rear': ((0, -8, .76), (0, 0, .76), 2.7),
    'top': ((0, 0, 9), (0, 0, 0), 5.55),
    'front_detail': ((0, 8, 1.1), (0, 2.28, .53), 2.22),
    'rear_detail': ((0, -8, 1.12), (0, -2.28, .58), 2.22),
    'grille_unlit': ((1.0, 7, 1.30), (0, 2.36, .414), 1.70),
}


def setup():
    base = runpy.run_path(str(ROOT / 'tools/blender/review_qcomet_body_v011.py'), run_name='qcomet_review_library')
    camera = base['setup']()
    scene = bpy.context.scene
    scene.cycles.samples = 40
    scene.view_settings.exposure = -.4
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .20
    for name, strength in [('key', 1050), ('side', 700), ('rim', 1100), ('front', 240)]:
        bpy.data.objects['qcomet_review_' + name].data.energy = strength
    return camera


def aim(name):
    location, target, scale = VIEWS[name]
    camera = bpy.context.scene.camera
    camera.location = location
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = scale
    return camera


def render_view(name):
    scene = bpy.context.scene
    aim(name)
    scene.render.resolution_x = 1500 if 'detail' in name or name == 'grille_unlit' else 1200
    scene.render.resolution_y = 850 if 'detail' in name or name == 'grille_unlit' else 780
    if name == 'top':
        scene.render.resolution_x, scene.render.resolution_y = 780, 1200
    scene.render.filepath = str(REVIEW / ('qcomet_v012_' + name + '.png'))
    prior_emissions = []
    if name == 'grille_unlit':
        for material in bpy.data.materials:
            if not material.use_nodes:
                continue
            for node in material.node_tree.nodes:
                if node.type == 'BSDF_PRINCIPLED':
                    socket = node.inputs['Emission Strength']
                    if socket.default_value:
                        prior_emissions.append((socket, socket.default_value))
                        socket.default_value = 0
    try:
        bpy.ops.render.render(write_still=True)
    finally:
        for socket, strength in prior_emissions:
            socket.default_value = strength
    return scene.render.filepath


def viewport():
    camera = aim('front_three_quarter')
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type != 'VIEW_3D':
                continue
            space = area.spaces.active
            space.shading.type = 'MATERIAL'
            space.shading.use_scene_lights = True
            space.shading.use_scene_world = True
            space.overlay.show_overlays = False
            region = space.region_3d
            region.view_rotation = camera.rotation_euler.to_quaternion()
            region.view_location = (0, 0, .73)
            region.view_distance = 7.6
            region.view_perspective = 'ORTHO'
            area.tag_redraw()


def main():
    setup()
    rendered = {name: render_view(name) for name in VIEWS}
    (REVIEW / 'render_manifest.json').write_text(json.dumps(rendered, indent=2), encoding='utf-8')
    viewport()


if __name__ == '__main__':
    main()
