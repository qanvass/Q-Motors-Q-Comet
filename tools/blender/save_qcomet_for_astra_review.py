"""Save a COPY of the live unsaved Q Comet scene for Astra review.

Run once in the already-open Blender window (Scripting > Run Script).
Uses bpy.ops.wm.save_as_mainfile(..., copy=True). Does not change geometry.
Does not retarget the working file. Does not overwrite v001–v005 or an
existing qcomet_for_astra_review.blend (timestamp is appended instead).
"""

from __future__ import annotations

import json
import os
from datetime import datetime

import bpy

FOLDER = r"C:\Users\Qanva\Desktop\Gaming GTA\Q-Motors-Q-Comet\vehicles\qcomet\source\blender"
BASE_NAME = "qcomet_for_astra_review.blend"
PROTECTED = {
    "qcomet_blockout_v001.blend",
    "qcomet_blockout_v002.blend",
    "qcomet_body_v003.blend",
    "qcomet_body_v004.blend",
    "qcomet_body_v005.blend",
}


def log(msg):
    print(msg, flush=True)
    try:
        bpy.context.workspace.status_text_set(msg[:255])
    except Exception:
        pass


def unique_copy_path():
    os.makedirs(FOLDER, exist_ok=True)
    path = os.path.join(FOLDER, BASE_NAME)
    if os.path.exists(path):
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(FOLDER, f"qcomet_for_astra_review_{stamp}.blend")
    name = os.path.basename(path)
    if name in PROTECTED or os.path.exists(path):
        raise RuntimeError(f"Refusing to write {path}")
    return path


def main():
    if bpy.app.background:
        raise RuntimeError("Refusing background Blender. Use the open qcomet_body_v004 window.")

    before = bpy.data.filepath or ""
    dest = unique_copy_path()
    result = bpy.ops.wm.save_as_mainfile(
        filepath=dest,
        copy=True,
        check_existing=False,
    )
    after = bpy.data.filepath or ""

    if not os.path.isfile(dest):
        raise RuntimeError(f"Copy was not written: {dest}")
    size = os.path.getsize(dest)
    if size < 10000:
        raise RuntimeError(f"Copy too small ({size} bytes): {dest}")

    before_n = os.path.normcase(os.path.abspath(before)) if before else ""
    after_n = os.path.normcase(os.path.abspath(after)) if after else ""
    dest_n = os.path.normcase(os.path.abspath(dest))
    if after_n == dest_n:
        raise RuntimeError("copy=True retargeted the session onto the review copy; abort")
    if before and after_n and before_n != after_n:
        raise RuntimeError(f"Working file changed from {before} to {after}")
    if os.path.basename(after or before).replace("\\", "/") in PROTECTED:
        pass  # expected: session stays on v004

    report = {
        "ok": True,
        "copy_path": dest,
        "copy_bytes": size,
        "working_file_before": before,
        "working_file_after": after,
        "save_operator": str(result),
        "geometry_changed": False,
        "time": datetime.now().isoformat(),
    }
    sidecar = dest + ".verify.json"
    tmp = sidecar + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    os.replace(tmp, sidecar)
    log(f"Astra copy OK: {dest} ({size} bytes). Working file still {after or before}")
    return report


if __name__ == "__main__":
    main()
