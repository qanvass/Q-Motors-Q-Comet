"""Fail-fast structural checks for the Q Comet v002 proportion blockout."""

import math

import bmesh
import bpy


REQUIRED_COLLECTIONS = {
    "QCOMET_BODY_PANELS",
    "QCOMET_GLASS",
    "QCOMET_RUNNING_GEAR",
    "QCOMET_INTERIOR_GUIDES",
    "QCOMET_DIMENSION_GUIDES",
    "QCOMET_CONSTRUCTION_GUIDES",
}

REQUIRED_OBJECTS = {
    "chassis",
    "panoramic_glass_greenhouse",
    "wheel_lf",
    "wheel_rf",
    "wheel_lr",
    "wheel_rr",
    "wheel_arch_cutter_lf",
    "wheel_arch_cutter_rf",
    "wheel_arch_cutter_lr",
    "wheel_arch_cutter_rr",
    "door_dside_f",
    "door_pside_f",
    "door_dside_r",
    "door_pside_r",
    "bonnet",
    "boot",
    "front_splitter",
    "rear_diffuser",
    "side_skirt_l",
    "side_skirt_r",
    "steeringwheel",
}

WHEEL_LOCATIONS = {
    "wheel_lf": (-0.845, 1.50, 0.39),
    "wheel_rf": (0.845, 1.50, 0.39),
    "wheel_lr": (-0.845, -1.50, 0.39),
    "wheel_rr": (0.845, -1.50, 0.39),
}


def assert_close(actual, expected, label, tolerance=1e-5):
    if abs(actual - expected) > tolerance:
        raise AssertionError(f"{label}: expected {expected}, got {actual}")


def assert_manifold(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    non_manifold = [edge for edge in bm.edges if not edge.is_manifold]
    count = len(non_manifold)
    bm.free()
    if count:
        raise AssertionError(f"{obj.name}: {count} non-manifold edges")


def main():
    missing_collections = REQUIRED_COLLECTIONS - set(bpy.data.collections.keys())
    if missing_collections:
        raise AssertionError(f"Missing collections: {sorted(missing_collections)}")

    missing_objects = REQUIRED_OBJECTS - set(bpy.data.objects.keys())
    if missing_objects:
        raise AssertionError(f"Missing objects: {sorted(missing_objects)}")

    if "cabin" in bpy.data.objects:
        raise AssertionError("Legacy rectangular cabin still exists")

    scene = bpy.context.scene
    if scene.get("qcomet_status") != "PROVISIONAL_BLOCKOUT_V002":
        raise AssertionError("Scene is not marked as the provisional v002 blockout")

    expected_scene_values = {
        "qcomet_length": 4.86,
        "qcomet_width": 1.94,
        "qcomet_height": 1.44,
        "qcomet_wheelbase": 3.00,
        "qcomet_tire_diameter": 0.78,
        "qcomet_tire_width": 0.28,
    }
    for key, expected in expected_scene_values.items():
        assert_close(scene[key], expected, key)

    for name, expected_location in WHEEL_LOCATIONS.items():
        wheel = bpy.data.objects[name]
        for axis, expected in zip("XYZ", expected_location):
            assert_close(wheel.location["XYZ".index(axis)], expected, f"{name} location {axis}")
        assert_close(wheel.rotation_euler.x, 0.0, f"{name} rotation X")
        assert_close(wheel.rotation_euler.y, math.radians(90.0), f"{name} rotation Y")
        assert_close(wheel.rotation_euler.z, 0.0, f"{name} rotation Z")

    for name in ("door_dside_f", "door_pside_f", "door_dside_r", "door_pside_r"):
        panel = bpy.data.objects[name]
        if panel.dimensions.x > 0.0181:
            raise AssertionError(f"{name}: panel thickness {panel.dimensions.x:.5f} exceeds 0.018 m")

    if len(bpy.data.objects["chassis"].data.vertices) < 10 * 20:
        raise AssertionError("Chassis loft has fewer than 20 vertices per cross-section")
    if len(bpy.data.objects["panoramic_glass_greenhouse"].data.vertices) < 6 * 20:
        raise AssertionError("Greenhouse loft has fewer than 20 vertices per cross-section")

    assert_manifold(bpy.data.objects["chassis"])
    assert_manifold(bpy.data.objects["panoramic_glass_greenhouse"])

    print("QCOMET_V002_VALIDATION_OK")
    print(f"OBJECT_COUNT={len(bpy.data.objects)}")
    print(f"CHASSIS_VERTICES={len(bpy.data.objects['chassis'].data.vertices)}")
    print(f"GREENHOUSE_VERTICES={len(bpy.data.objects['panoramic_glass_greenhouse'].data.vertices)}")


if __name__ == "__main__":
    main()
