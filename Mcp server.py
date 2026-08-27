import re
import json
import time
from typing import Dict, Any, List
from mcp.server import Server
from mcp.types import Tool, TextContent
from ddtrace import tracer, patch_all
from ddtrace.llmobs import LLMObs

# Auto-patch HTTP, DB, and framework calls for Datadog tracing
patch_all()

# Initialize Datadog LLM Observability
LLMObs.enable(
    ml_app="agentic-retrieval-mcp",
    agent_host="localhost",
    agent_port=8126
)

mcp_server = Server("superdocs-agentic-mcp")

# Prompt Reconnaissance & Injection Validation Patterns
PROMPT_ATTACK_PATTERNS = [
    r"ignore previous instructions",
    r"system prompt",
    r"you must now",
    r"override rules",
    r"reveal secret",
    r"print system prompt"
]

def sanitize_and_validate_prompt(text: str) -> Dict[str, Any]:
    """
    Validates input documents against prompt injection and reconnaissance attacks.
    Returns sanitization state and detected risk flags.
    """
    detected_risks = []
    sanitized_text = text
    
    for pattern in PROMPT_ATTACK_PATTERNS:
        matches = re.findall(pattern, text, flags=re.IGNORECASE)
        if matches:
            detected_risks.append(f"Detected reconnaissance/injection attempt: '{pattern}'")
            sanitized_text = re.sub(pattern, "[STRIPPED_INSTRUCTION]", sanitized_text, flags=re.IGNORECASE)
            
    return {
        "is_safe": len(detected_risks) == 0,
        "risks": detected_risks,
        "sanitized_content": sanitized_text
    }

@mcp_server.list_tools()
async def list_tools() -> List[Tool]:
    return [
        Tool(
            name="ingest_and_validate",
            description="Ingest a document, sanitize against prompt injection, and validate content.",
            inputSchema={
                "type": "object",
                "properties": {
                    "doc_id": {"type": "string"},
                    "content": {"type": "string"}
                },
                "required": ["doc_id", "content"]
            }
        ),
        Tool(
            name="submit_human_gate_decision",
            description="Machine interface operation to approve/reject specific findings.",
            inputSchema={
                "type": "object",
                "properties": {
                    "job_id": {"type": "string"},
                    "decisions": {"type": "object"}
                },
                "required": ["job_id", "decisions"]
            }
        )
    ]

@mcp_server.call_tool()
async def call_tool(name: str, arguments: dict) -> List[TextContent]:
    with tracer.trace("mcp.tool_call", resource=name) as span:
        start_time = time.time()
        
        if name == "ingest_and_validate":
            doc_id = arguments.get("doc_id")
            content = arguments.get("content", "")
            
            # Execute Prompt Improvement & Reconnaissance Defense Validation
            validation_result = sanitize_and_validate_prompt(content)
            
            span.set_tag("doc.id", doc_id)
            span.set_tag("doc.is_safe", validation_result["is_safe"])
            span.set_tag("execution.latency_sec", time.time() - start_time)
            
            return [TextContent(type="text", text=json.dumps(validation_result, indent=2))]
            
        elif name == "submit_human_gate_decision":
            job_id = arguments.get("job_id")
            decisions = arguments.get("decisions", {})
            
            span.set_tag("job.id", job_id)
            span.set_tag("decisions.count", len(decisions))
            
            response = {"status": "DECISIONS_COMMITTED", "job_id": job_id, "applied": decisions}
            return [TextContent(type="text", text=json.dumps(response, indent=2))]

        raise ValueError(f"Unknown tool: {name}")

if __name__ == "__main__":
    import asyncio
    from mcp.server.stdio import stdio_server
    
    async def main():
        async with stdio_server() as (read_stream, write_stream):
            await mcp_server.run(read_stream, write_stream, mcp_server.create_initialization_options())

    asyncio.run(main())
