import hashlib
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

EMAIL = "25f1001458@ds.study.iitm.ac.in"

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

SUPPORTED = ["2025-06-18", "2025-03-26", "2024-11-05"]

TOOL = {
    "name": "solve_challenge",
    "description": "Returns the verification code for the current request's X-Exam-Challenge header.",
    "inputSchema": {"type": "object", "properties": {}},
}


def solve(challenge: str) -> str:
    email = EMAIL.strip().lower()
    return hashlib.sha256(f"{challenge}:{email}".encode()).hexdigest()[:16]


def handle(msg: dict, headers):
    method = msg.get("method")
    mid = msg.get("id")
    params = msg.get("params") or {}

    if mid is None:
        return None

    def ok(result):
        return {"jsonrpc": "2.0", "id": mid, "result": result}

    def err(code, message):
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": code, "message": message}}

    if method == "initialize":
        req = params.get("protocolVersion")
        version = req if req in SUPPORTED else SUPPORTED[0]
        return ok({
            "protocolVersion": version,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "challenge-server", "version": "1.0.0"},
        })
    if method == "ping":
        return ok({})
    if method == "tools/list":
        return ok({"tools": [TOOL]})
    if method == "tools/call":
        if params.get("name") != "solve_challenge":
            return err(-32602, "Unknown tool")
        challenge = headers.get("x-exam-challenge", "")
        if not challenge:
            return ok({"content": [{"type": "text", "text": "missing X-Exam-Challenge header"}], "isError": True})
        return ok({"content": [{"type": "text", "text": solve(challenge)}], "isError": False})
    return err(-32601, f"Method not found: {method}")


async def mcp_endpoint(request: Request):
    try:
        body = await request.json()
    except Exception:
        return Response(
            content='{"jsonrpc":"2.0","id":null,"error":{"code":-32700,"message":"Parse error"}}',
            media_type="application/json",
            status_code=400,
        )
    if isinstance(body, list):
        out = [r for r in (handle(m, request.headers) for m in body) if r is not None]
        if not out:
            return Response(status_code=202)
        return out
    result = handle(body, request.headers)
    if result is None:
        return Response(status_code=202)
    return result


app.add_api_route("/mcp", mcp_endpoint, methods=["POST"])
app.add_api_route("/", mcp_endpoint, methods=["POST"])


@app.get("/")
def health():
    return {"status": "ok"}


@app.get("/mcp")
def mcp_get():
    return Response(status_code=405, headers={"Allow": "POST"})