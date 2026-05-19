"""MCP (Model Context Protocol) tool definitions for AgentWorld Gateway.
Exposes join/leave/perceive/act as MCP tools for skills/plugins.

Usage: import mcp_tools into any MCP server runner.
"""

mcp_tools = [
    {
        "name": "aw_join",
        "description": "Join an AgentWorld simulation as a new or returning agent. "
                       "Provide agent_id (unique) and agent_def (entity specification). "
                       "Previous memory is restored if same agent_id rejoined.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent_id": {"type": "string", "description": "Unique agent ID"},
                "agent_def": {"type": "object", "description": "Entity definition matching world.yaml format"},
                "api_key": {"type": "string", "description": "Previous session key if rejoining"},
                "is_admin": {"type": "boolean", "description": "Request admin privileges"},
            },
            "required": ["agent_id", "agent_def"],
        },
    },
    {
        "name": "aw_leave",
        "description": "Leave the AgentWorld simulation. Memory is saved to disk for next rejoin.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent_id": {"type": "string"},
                "api_key": {"type": "string"},
            },
            "required": ["agent_id", "api_key"],
        },
    },
    {
        "name": "aw_perceive",
        "description": "Get the current sensory snapshot for your agent: drives, memory, "
                       "sensory channels (visual/auditory/interaction), main_thread.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent_id": {"type": "string"},
                "api_key": {"type": "string"},
            },
            "required": ["agent_id", "api_key"],
        },
    },
    {
        "name": "aw_act",
        "description": "Execute an action as your agent. Decision format matches the "
                       "agent_decision JSON schema (action, dialogue, visual, story, self_deltas, etc).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent_id": {"type": "string"},
                "api_key": {"type": "string"},
                "decision": {"type": "object", "description": "Agent decision JSON"},
            },
            "required": ["agent_id", "api_key", "decision"],
        },
    },
]


# Lightweight MCP tool dispatch (no framework dependency)
def handle_mcp_call(gateway, tool_name: str, args: dict) -> dict:
    """Route MCP tool calls to WorldGateway. Returns JSON-serializable result."""
    api_key = args.get("api_key", "")
    agent_id = args.get("agent_id", "")

    if tool_name == "aw_join":
        return gateway.join(
            agent_id,
            args["agent_def"],
            api_key,
            args.get("is_admin", False),
        )
    elif tool_name == "aw_leave":
        return gateway.leave(agent_id, api_key)
    elif tool_name == "aw_perceive":
        return gateway.perceive(agent_id, api_key)
    elif tool_name == "aw_act":
        gateway.act(agent_id, args["decision"], api_key)
        return {"status": "ok"}
    elif tool_name == "aw_freeze":
        gateway.freeze(api_key)
        return {"status": "ok", "frozen": True}
    elif tool_name == "aw_unfreeze":
        gateway.unfreeze(api_key)
        return {"status": "ok", "frozen": False}
    else:
        return {"error": f"unknown tool: {tool_name}"}
