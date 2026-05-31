"""
Local MCP server for LexiFlow damage detection.

This dependency-free stdio server exposes one learning-focused MCP tool:
- inspect_product_damage

Run:
    python mcp_server.py
"""

import json
import sys
import traceback
from typing import Any, Callable, Dict

from damage_detection_agent import inspect_product_image


SERVER_INFO = {"name": "lexiflow-damage-detection", "version": "0.2.0"}


def json_text(data: Any) -> Dict:
    return {"content": [{"type": "text", "text": json.dumps(data, indent=2)}]}


def tool_inspect_product_damage(args: Dict) -> Dict:
    return inspect_product_image(
        image_path=args["image_path"],
        image_url=args.get("image_url"),
    )


TOOLS: Dict[str, Dict[str, Any]] = {
    "inspect_product_damage": {
        "description": "Inspect a customer-uploaded product image for visible damage.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "image_path": {"type": "string"},
                "image_url": {"type": "string"},
                "order_id": {"type": "string"},
            },
            "required": ["image_path"],
        },
        "handler": tool_inspect_product_damage,
    }
}


def list_tools() -> Dict:
    return {
        "tools": [
            {
                "name": name,
                "description": spec["description"],
                "inputSchema": spec["inputSchema"],
            }
            for name, spec in TOOLS.items()
        ]
    }


def call_tool(name: str, arguments: Dict) -> Dict:
    if name not in TOOLS:
        raise ValueError(f"Unknown tool: {name}")

    handler: Callable[[Dict], Dict] = TOOLS[name]["handler"]
    return json_text(handler(arguments or {}))


def handle_request(request: Dict) -> Dict:
    method = request.get("method")
    request_id = request.get("id")
    params = request.get("params") or {}

    try:
        if method == "initialize":
            result = {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": SERVER_INFO,
            }
        elif method == "tools/list":
            result = list_tools()
        elif method == "tools/call":
            result = call_tool(params["name"], params.get("arguments") or {})
        elif method in {"notifications/initialized", "initialized"}:
            return {}
        else:
            raise ValueError(f"Unsupported method: {method}")

        return {"jsonrpc": "2.0", "id": request_id, "result": result}
    except Exception as exc:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32000,
                "message": str(exc),
                "data": traceback.format_exc(),
            },
        }


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        response = handle_request(json.loads(line))
        if response:
            print(json.dumps(response), flush=True)


if __name__ == "__main__":
    main()
