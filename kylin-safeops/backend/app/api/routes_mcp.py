from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from backend.app.mcp_runtime import (
    call_mcp_tool,
    get_mcp_prompt,
    list_mcp_prompts,
    list_mcp_resources,
    read_mcp_resource,
    tools_list_payload,
)

router = APIRouter()


class ToolCallRequest(BaseModel):
    name: str
    arguments: dict[str, Any] = {}
    human_confirmed: bool = False
    source: dict[str, Any] | None = None


class ResourceReadRequest(BaseModel):
    uri: str
    source: dict[str, Any] | None = None


class JsonRpcRequest(BaseModel):
    jsonrpc: str = "2.0"
    id: str | int | None = None
    method: str
    params: dict[str, Any] | None = None


@router.get("/tools/list")
def rest_list_tools() -> dict:
    return tools_list_payload()


@router.post("/tools/call")
def rest_call_tool(request: ToolCallRequest) -> dict:
    return call_mcp_tool(request.name, request.arguments, request.human_confirmed, request.source)


@router.get("/resources/list")
def rest_list_resources() -> dict:
    return list_mcp_resources()


@router.post("/resources/read")
def rest_read_resource(request: ResourceReadRequest) -> dict:
    return read_mcp_resource(request.uri, request.source)


@router.get("/prompts/list")
def rest_list_prompts() -> dict:
    return list_mcp_prompts()


@router.get("/prompts/{name}")
def rest_get_prompt(name: str) -> dict:
    return get_mcp_prompt(name)


@router.post("")
def jsonrpc_endpoint(request: JsonRpcRequest) -> dict:
    params = request.params or {}

    if request.method in {"initialize", "mcp.initialize"}:
        return _jsonrpc_result(request.id, {
            "protocolVersion": "2024-11-05",
            "serverInfo": {"name": "kylin-safeops-mcp", "version": "0.2.0"},
            "capabilities": {
                "tools": {"listChanged": False},
                "resources": {"subscribe": False, "listChanged": False},
                "prompts": {"listChanged": False},
            },
        })

    if request.method in {"tools/list", "mcp.tools.list"}:
        return _jsonrpc_result(request.id, tools_list_payload())

    if request.method in {"tools/call", "mcp.tools.call"}:
        result = call_mcp_tool(
            str(params.get("name", "")),
            dict(params.get("arguments") or {}),
            bool(params.get("human_confirmed", False)),
            dict(params.get("source") or {}),
        )
        return _jsonrpc_result(request.id, {
            "content": [{"type": "text", "text": result["summary"]}],
            "structuredContent": result,
            "isError": not result.get("ok", False),
        })

    if request.method in {"resources/list", "mcp.resources.list"}:
        return _jsonrpc_result(request.id, list_mcp_resources())

    if request.method in {"resources/read", "mcp.resources.read"}:
        uri = str(params.get("uri", ""))
        result = read_mcp_resource(uri, dict(params.get("source") or {}))
        return _jsonrpc_result(request.id, {
            "contents": [{
                "uri": uri,
                "mimeType": "application/json",
                "text": result.get("content", ""),
            }],
            "structuredContent": result,
            "isError": not result.get("ok", False),
        })

    if request.method in {"prompts/list", "mcp.prompts.list"}:
        return _jsonrpc_result(request.id, list_mcp_prompts())

    if request.method in {"prompts/get", "mcp.prompts.get"}:
        return _jsonrpc_result(request.id, get_mcp_prompt(str(params.get("name", ""))))

    return _jsonrpc_error(request.id, -32601, f"Method not found: {request.method}")


def _jsonrpc_result(request_id: str | int | None, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _jsonrpc_error(request_id: str | int | None, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}
