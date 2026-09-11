"""Save a copy of the in-memory Blender scene without changing the active path."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import bpy

ROOT = Path(r"C:\Users\Qanva\Desktop\Gaming GTA\Q-Motors-Q-Comet")
OUT_DIR = ROOT / "collaboration" / "local" / "checkpoints"
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
DEST = OUT_DIR / f"qcomet_live_checkpoint_{STAMP}.blend"


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    window = bpy.context.window_manager.windows[0]
    with bpy.context.temp_override(window=window):
        bpy.ops.wm.save_as_mainfile(filepath=str(DEST), copy=True)
    report = {
        "checkpoint": str(DEST),
        "exists": DEST.is_file(),
        "bytes": DEST.stat().st_size if DEST.is_file() else 0,
        "active_filepath_after": bpy.data.filepath,
        "active_still_dirty": bpy.data.is_dirty,
        "object_count": len(bpy.context.scene.objects),
    }
    (ROOT / "collaboration" / "local" / "last_checkpoint.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report))


if __name__ == "__main__":
    main()
