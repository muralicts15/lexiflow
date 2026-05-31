"""Local MCP client for LexiFlow damage detection."""

import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional


class DamageDetectionMCPClient:
    """Small stdio JSON-RPC client for the local damage detection MCP server."""

    def __init__(self, server_path: Optional[str] = None) -> None:
        self.server_path = Path(server_path) if server_path else Path(__file__).with_name("mcp_server.py")
        self.next_id = 1
        self.process = subprocess.Popen(
            [sys.executable, str(self.server_path)],
            cwd=str(self.server_path.parent),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        self.request("initialize", {})

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def request(self, method: str, params: Dict) -> Dict:
        if not self.process.stdin or not self.process.stdout:
            raise RuntimeError("MCP server process is not available.")

        request_id = self.next_id
        self.next_id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params,
        }
        self.process.stdin.write(json.dumps(payload) + "\n")
        self.process.stdin.flush()

        line = self.process.stdout.readline()
        if not line:
            error = self.process.stderr.read() if self.process.stderr else ""
            raise RuntimeError(f"MCP server stopped without a response. {error}".strip())

        response = json.loads(line)
        if response.get("error"):
            raise RuntimeError(response["error"].get("message", "MCP request failed."))

        return response.get("result", {})

    def call_tool(self, name: str, arguments: Dict) -> Dict:
        return self.request(
            "tools/call",
            {
                "name": name,
                "arguments": arguments,
            },
        )

    def inspect_product_damage(
        self,
        image_path: str,
        image_url: Optional[str] = None,
        order_id: Optional[str] = None,
    ) -> Dict:
        result = self.call_tool(
            "inspect_product_damage",
            {
                "image_path": image_path,
                "image_url": image_url,
                "order_id": order_id,
            },
        )
        content = result.get("content") or []
        if not content:
            raise RuntimeError("MCP damage inspection returned no content.")

        return json.loads(content[0]["text"])

    def close(self) -> None:
        if self.process.poll() is not None:
            return

        self.process.terminate()
        try:
            self.process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=2)


def inspect_product_damage_via_mcp(
    image_path: str,
    image_url: Optional[str] = None,
    order_id: Optional[str] = None,
) -> Dict:
    with DamageDetectionMCPClient() as client:
        return client.inspect_product_damage(
            image_path=image_path,
            image_url=image_url,
            order_id=order_id,
        )
