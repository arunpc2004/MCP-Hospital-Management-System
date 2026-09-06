"""User-facing Groq host that discovers and calls tools through MCP."""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Any

from groq import Groq

from .client import HospitalMCPClient
from .config import load_host_settings
from .errors import ConfigurationError


SYSTEM_PROMPT = """
You are a Hospital Management Assistant connected to a synthetic demonstration
database through MCP tools.

Rules:
- Use a tool whenever the user asks for patient, lab, doctor, medicine, or
  appointment data.
- Never invent hospital records or claim an operation succeeded without a
  successful tool result.
- Ask the user for any required argument that is missing.
- Explain tool errors clearly and briefly.
- Do not provide medical diagnoses or treatment advice.
""".strip()

MUTATING_TOOLS = {"schedule_appointment", "cancel_appointment"}
MAX_TOOL_ROUNDS = 5


def _to_plain_json(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json", by_alias=True, exclude_none=True)
    return value


def mcp_tools_to_groq(mcp_tools: list[Any]) -> list[dict[str, Any]]:
    """Convert MCP tool metadata into Groq's local tool-calling format."""

    groq_tools: list[dict[str, Any]] = []
    for tool in mcp_tools:
        input_schema = _to_plain_json(tool.inputSchema)
        groq_tools.append(
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or "Hospital MCP tool",
                    "parameters": input_schema,
                },
            }
        )
    return groq_tools


def _assistant_message_payload(message: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"role": "assistant"}
    if message.content is not None:
        payload["content"] = message.content

    if message.tool_calls:
        payload["tool_calls"] = [
            {
                "id": call.id,
                "type": "function",
                "function": {
                    "name": call.function.name,
                    "arguments": call.function.arguments,
                },
            }
            for call in message.tool_calls
        ]
    return payload


def _serialize_tool_result(result: Any) -> str:
    return json.dumps(
        _to_plain_json(result),
        ensure_ascii=False,
        default=str,
    )


def _approved_by_user(tool_name: str, arguments: dict[str, Any]) -> bool:
    print("\nApproval required for database-changing operation:")
    print(f"  Tool: {tool_name}")
    print(f"  Arguments: {json.dumps(arguments, ensure_ascii=False)}")
    answer = input("Approve this operation? [y/N]: ").strip().lower()
    return answer in {"y", "yes"}


async def run_agent_turn(
    groq: Groq,
    model: str,
    mcp_client: HospitalMCPClient,
    messages: list[dict[str, Any]],
    groq_tools: list[dict[str, Any]],
    allowed_tool_names: set[str],
) -> str:
    """Run Groq and MCP tool calls until the model produces a final answer."""

    for _ in range(MAX_TOOL_ROUNDS):
        completion = groq.chat.completions.create(
            model=model,
            messages=messages,
            tools=groq_tools,
            tool_choice="auto",
        )
        message = completion.choices[0].message
        messages.append(_assistant_message_payload(message))

        if not message.tool_calls:
            return message.content or "I could not produce a response."

        for tool_call in message.tool_calls:
            tool_name = tool_call.function.name
            try:
                arguments = json.loads(tool_call.function.arguments or "{}")
            except json.JSONDecodeError:
                tool_output = json.dumps(
                    {
                        "success": False,
                        "error": {
                            "type": "invalid_arguments",
                            "message": "The model produced invalid JSON arguments",
                        },
                    }
                )
            else:
                if tool_name not in allowed_tool_names:
                    tool_output = json.dumps(
                        {
                            "success": False,
                            "error": {
                                "type": "unknown_tool",
                                "message": f"Tool '{tool_name}' is not available",
                            },
                        }
                    )
                elif tool_name in MUTATING_TOOLS and not _approved_by_user(
                    tool_name, arguments
                ):
                    tool_output = json.dumps(
                        {
                            "success": False,
                            "error": {
                                "type": "user_denied",
                                "message": "The user did not approve the operation",
                            },
                        }
                    )
                else:
                    try:
                        result = await mcp_client.call_tool(tool_name, arguments)
                        tool_output = _serialize_tool_result(result)
                    except Exception as exc:
                        tool_output = json.dumps(
                            {
                                "success": False,
                                "error": {
                                    "type": "mcp_call_failed",
                                    "message": str(exc),
                                },
                            }
                        )

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_name,
                    "content": tool_output,
                }
            )

    return "The request required too many tool operations. Please simplify it."


async def run_chat() -> None:
    settings = load_host_settings()
    groq = Groq(api_key=settings.groq_api_key)

    async with HospitalMCPClient() as mcp_client:
        mcp_tools = await mcp_client.list_tools()
        groq_tools = mcp_tools_to_groq(mcp_tools)
        allowed_tool_names = {tool.name for tool in mcp_tools}

        print("Hospital MCP Assistant")
        print(f"Connected tools: {', '.join(sorted(allowed_tool_names))}")
        print("Type 'exit' to close the application.\n")

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]

        while True:
            try:
                question = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nGoodbye.")
                break

            if not question:
                continue
            if question.lower() in {"exit", "quit"}:
                print("Goodbye.")
                break

            messages.append({"role": "user", "content": question})
            answer = await run_agent_turn(
                groq,
                settings.groq_model,
                mcp_client,
                messages,
                groq_tools,
                allowed_tool_names,
            )
            print(f"\nAssistant: {answer}\n")


def main() -> None:
    try:
        asyncio.run(run_chat())
    except ConfigurationError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    except Exception as exc:
        print(f"Application error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
