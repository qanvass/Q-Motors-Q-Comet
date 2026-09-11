"""Structural checks for the Q Comet v003 photo-matched body pass."""

import bpy

REQUIRED_OBJECTS = {
    "chassis",
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
    "steeringwheel",
    "seat_dside_f",
    "seat_pside_f",
    "seat_dside_r",
    "seat_pside_r",
    "front_splitter",
    "rear_diffuser",
    "badge_front",
    "badge_rear",
    "headlight_dside_blade_1",
    "headlight_pside_blade_1",
    "tail_bar_running",
    "drl_dside",
    "drl_pside",
}

FORBIDDEN = {
    "Lucid",
    "Taycan",
    "Tesla",
    "etron",
    "e-tron",
    "NoPixel",
}


def main():
    if bpy.context.scene.get("qcomet_status") != "BODY_SURFACING_V003":
        raise AssertionError("Scene is not marked BODY_SURFACING_V003")
    missing = REQUIRED_OBJECTS - set(bpy.data.objects.keys())
    if missing:
        raise AssertionError(f"Missing objects: {sorted(missing)}")
    for obj in bpy.data.objects:
        lowered = obj.name.lower()
        for token in FORBIDDEN:
            if token.lower() in lowered:
                raise AssertionError(f"Forbidden name on {obj.name}")
    if not os_v002_untouched():
        raise AssertionError("v002 blockout file is missing")
    print("QCOMET_V003_VALIDATION_OK")
    print(f"OBJECT_COUNT={len(bpy.data.objects)}")
    print(f"STATUS={bpy.context.scene.get('qcomet_status')}")


def os_v002_untouched():
    import os

    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    return os.path.isfile(
        os.path.join(root, "vehicles", "qcomet", "source", "blender", "qcomet_blockout_v002.blend")
    )


if __name__ == "__main__":
    main()
