# LexiFlow Damage Detection MCP

LexiFlow now keeps MCP focused on one learning use case: product image damage
inspection.

The customer database, ticket creation, email drafts, and audit logs remain
normal local application functions. Only the Damage Detection Agent is exposed
through the MCP server and called by the MCP client.

## Server

Run the server from the project root:

```bash
.venv/bin/python mcp_server.py
```

Available tool:

- `inspect_product_damage`: inspects a customer-uploaded product image and
  returns a structured damage report.

## Client

The Streamlit app calls the MCP client in `mcp_client.py` when a customer image
is uploaded:

```python
from mcp_client import inspect_product_damage_via_mcp

report = inspect_product_damage_via_mcp(
    image_path="uploads/ORD-1001_photo.png",
    image_url="uploads/ORD-1001_photo.png",
    order_id="ORD-1001",
)
```

## Smoke Test

List MCP tools:

```bash
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' \
  | .venv/bin/python mcp_server.py
```

Expected result: only `inspect_product_damage` should be listed.

For local plumbing tests without calling a vision API, set:

```bash
export DAMAGE_DETECTION_USE_MOCK=1
```
