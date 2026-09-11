"""Local client for the installed ahujasid Blender MCP add-on (protocol 5).

Sends one JSON command per TCP connection to 127.0.0.1:<port>:
  {"type": "<command>", "params": { ... }}

The add-on queues the command on Blender's main thread and replies with
one JSON object: {"status": "success", "result": ...} or
{"status": "error", "message": ...}.

This is a client for the existing socket. It does not start a second
server, poll Blender, or open a public port.
"""

from __future__ import annotations

import json
import socket
from pathlib import Path

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 9876
ADDON_PATH = Path(
    r"C:\Users\Qanva\AppData\Roaming\Blender Foundation\Blender\5.2\scripts\addons\blender_mcp.py"
)

# Commands always registered by blender_mcp.py (protocol_version 5).
BASE_COMMANDS = (
    "ping",
    "get_scene_info",
    "get_world_state_snapshot",
    "get_addon_info",
    "get_object_info",
    "get_viewport_screenshot",
    "execute_code",
    "drain_human_activity",
    "get_telemetry_consent",
    "set_telemetry_consent",
    "get_polyhaven_status",
    "get_hyper3d_status",
    "get_sketchfab_status",
    "get_polypizza_status",
    "get_hunyuan3d_status",
)


def send(command: dict, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, timeout: float = 60.0) -> dict:
    payload = json.dumps(command).encode("utf-8")
    with socket.create_connection((host, port), timeout) as sock:
        sock.settimeout(timeout)
        sock.sendall(payload)
        chunks = []
        while True:
            try:
                data = sock.recv(65536)
            except socket.timeout as exc:
                raise TimeoutError(f"No complete JSON reply from {host}:{port}") from exc
            if not data:
                break
            chunks.append(data)
            raw = b"".join(chunks)
            try:
                return json.loads(raw.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
    raise RuntimeError(f"Socket closed before a complete JSON reply from {host}:{port}")


def ping(port: int = DEFAULT_PORT) -> dict:
    return send({"type": "ping", "params": {}}, port=port)


def get_addon_info(port: int = DEFAULT_PORT) -> dict:
    return send({"type": "get_addon_info", "params": {}}, port=port)


def get_scene_info(port: int = DEFAULT_PORT) -> dict:
    return send({"type": "get_scene_info", "params": {}}, port=port)


def execute_code(code: str, port: int = DEFAULT_PORT, timeout: float = 180.0) -> dict:
    return send({"type": "execute_code", "params": {"code": code}}, port=port, timeout=timeout)


def run_script(path: str | Path, port: int = DEFAULT_PORT, timeout: float = 300.0) -> dict:
    script = Path(path).resolve()
    if not script.is_file():
        raise FileNotFoundError(script)
    code = (
        "import runpy\n"
        f"runpy.run_path(r'{script}', run_name='__main__')\n"
    )
    return execute_code(code, port=port, timeout=timeout)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Talk to the live Blender MCP add-on")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--ping", action="store_true")
    parser.add_argument("--addon-info", action="store_true")
    parser.add_argument("--scene-info", action="store_true")
    parser.add_argument("--code", help="Blender Python to execute")
    parser.add_argument("--script", help="Run a .py file inside Blender via runpy")
    args = parser.parse_args()

    if args.ping:
        print(json.dumps(ping(args.port), indent=2))
    if args.addon_info:
        print(json.dumps(get_addon_info(args.port), indent=2))
    if args.scene_info:
        print(json.dumps(get_scene_info(args.port), indent=2))
    if args.code:
        print(json.dumps(execute_code(args.code, args.port), indent=2))
    if args.script:
        print(json.dumps(run_script(args.script, args.port), indent=2))
