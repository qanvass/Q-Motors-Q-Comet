"""Execute a ChatGPT/Astra-supplied Blender script through the existing MCP socket.

Usage:
  python collaboration/scripts/run_astra_task.py --task-id T001 --script path/to/script.py

Steps: review preconditions, checkpoint, execute, record result.
Does not blindly retry after a timeout.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_mcp_client import execute_code, ping, run_script  # noqa: E402

LOG = ROOT / "collaboration" / "local" / "task_log.jsonl"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--script", required=True)
    parser.add_argument("--port", type=int, default=9876)
    parser.add_argument("--timeout", type=float, default=300)
    args = parser.parse_args()

    script = Path(args.script).resolve()
    alive = ping(args.port)
    if alive.get("status") != "success":
        raise SystemExit(f"Blender MCP not reachable: {alive}")

    probe = execute_code(
        "import bpy, json; print(json.dumps({'file': bpy.data.filepath, 'dirty': bpy.data.is_dirty, 'objects': len(bpy.context.scene.objects)}))",
        port=args.port,
    )
    print("PRECONDITION", probe)
    checkpoint = run_script(ROOT / "collaboration" / "scripts" / "save_live_checkpoint.py", port=args.port)
    print("CHECKPOINT", checkpoint)
    result = run_script(script, port=args.port, timeout=args.timeout)
    record = {
        "task_id": args.task_id,
        "utc": datetime.now(timezone.utc).isoformat(),
        "script": str(script),
        "script_sha256": sha256(script),
        "precondition": probe,
        "checkpoint": checkpoint,
        "result_status": result.get("status"),
        "result": result.get("result") if result.get("status") == "success" else result,
    }
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")
    print(json.dumps({"logged": str(LOG), "status": result.get("status")}, indent=2))
    if result.get("status") != "success":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
