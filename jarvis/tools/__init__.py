"""Tool registry, argument validation, confirmation gating, and audit logging."""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

SECRET_KEY_PATTERNS = re.compile(r"(key|token|secret|password|auth)", re.IGNORECASE)
SECRET_VAL_PATTERNS = re.compile(
    r"(AIza[0-9A-Za-z-_]{10,}|AQ\.[0-9A-Za-z-_]{10,}|gsk_[0-9A-Za-z-_]{10,}|sk-[0-9A-Za-z-_]{10,}|Bearer\s+[^\s]+)",
    re.IGNORECASE,
)


class ToolError(Exception):
    """Raised when tool execution fails, is unknown, or violates validation/confirmation."""
    pass


@dataclass
class ToolDef:
    name: str
    description: str
    parameters: dict[str, Any]
    handler: Callable[..., Any]
    risk: str = "confirm"  # "safe" or "confirm"

    def __post_init__(self) -> None:
        if self.risk not in ("safe", "confirm"):
            self.risk = "confirm"


def mask_secrets(data: Any) -> Any:
    """Mask credentials and sensitive strings in arguments or results."""
    if isinstance(data, dict):
        masked = {}
        for k, v in data.items():
            if SECRET_KEY_PATTERNS.search(str(k)):
                masked[k] = "[MASKED]"
            else:
                masked[k] = mask_secrets(v)
        return masked
    elif isinstance(data, list):
        return [mask_secrets(item) for item in data]
    elif isinstance(data, str):
        if SECRET_VAL_PATTERNS.search(data):
            return SECRET_VAL_PATTERNS.sub("[MASKED]", data)
        return data
    return data


def validate_arguments(schema: dict[str, Any], args: dict[str, Any]) -> None:
    """Validate arguments dictionary against a basic JSON schema subset."""
    properties = schema.get("properties", {})
    required = schema.get("required", [])

    for req in required:
        if req not in args:
            raise ToolError(f"Missing required argument '{req}'")

    for key, val in args.items():
        if key not in properties:
            continue
        prop_spec = properties[key]
        expected_type = prop_spec.get("type")

        if expected_type == "integer":
            if not isinstance(val, int) or isinstance(val, bool):
                raise ToolError(f"Argument '{key}' must be an integer, got {type(val).__name__}")
        elif expected_type == "number":
            if not isinstance(val, (int, float)) or isinstance(val, bool):
                raise ToolError(f"Argument '{key}' must be a number, got {type(val).__name__}")
        elif expected_type == "string":
            if not isinstance(val, str):
                raise ToolError(f"Argument '{key}' must be a string, got {type(val).__name__}")
        elif expected_type == "boolean":
            if not isinstance(val, bool):
                raise ToolError(f"Argument '{key}' must be a boolean, got {type(val).__name__}")

        if "minimum" in prop_spec and isinstance(val, (int, float)):
            if val < prop_spec["minimum"]:
                raise ToolError(f"Argument '{key}' must be >= {prop_spec['minimum']}")
        if "maximum" in prop_spec and isinstance(val, (int, float)):
            if val > prop_spec["maximum"]:
                raise ToolError(f"Argument '{key}' must be <= {prop_spec['maximum']}")


class ToolRegistry:
    def __init__(self, log_path: Path | None = None) -> None:
        self._tools: dict[str, ToolDef] = {}
        self.log_path = log_path or Path("data/tool-log.jsonl")

    def register(self, tool: ToolDef) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> ToolDef:
        if name not in self._tools:
            raise ToolError(f"Unknown tool '{name}'")
        return self._tools[name]

    def list_tools(self) -> list[ToolDef]:
        return list(self._tools.values())

    def to_openai_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in self.list_tools()
        ]

    def execute(self, name: str, arguments: dict[str, Any], confirmed: bool = False) -> Any:
        tool = self.get(name)
        validate_arguments(tool.parameters, arguments)

        if tool.risk == "confirm" and not confirmed:
            raise ToolError(f"Tool '{name}' requires user confirmation before execution.")

        try:
            result = tool.handler(**arguments)
        except Exception as exc:
            if isinstance(exc, ToolError):
                raise
            raise ToolError(f"Error executing tool '{name}': {exc}") from exc

        self._log_call(name, arguments, result)
        return result

    def _log_call(self, name: str, arguments: dict[str, Any], result: Any) -> None:
        entry = {
            "timestamp": time.time(),
            "name": name,
            "arguments": mask_secrets(arguments),
            "result": mask_secrets(result),
        }
        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, default=str) + "\n")
        except Exception:
            pass  # Logging error must never break tool execution


def default_registry() -> ToolRegistry:
    """Build the standard tool registry with allowlisted tools."""
    from .apps import open_app, open_folder
    from .info import get_time, get_weather, search_web

    registry = ToolRegistry()

    registry.register(
        ToolDef(
            name="get_time",
            description="Get the current local time, date, and day in the user's timezone (Africa/Nairobi).",
            parameters={"type": "object", "properties": {}},
            handler=get_time,
            risk="safe",
        )
    )

    registry.register(
        ToolDef(
            name="get_weather",
            description="Fetch current live weather conditions for a city (defaults to Nakuru, Kenya).",
            parameters={
                "type": "object",
                "properties": {"city": {"type": "string", "description": "City name, e.g. Nakuru, Nairobi"}},
            },
            handler=get_weather,
            risk="safe",
        )
    )

    registry.register(
        ToolDef(
            name="search_web",
            description="Search the web for up-to-date facts, flight info, or general queries.",
            parameters={
                "type": "object",
                "properties": {"query": {"type": "string", "description": "Search query"}},
                "required": ["query"],
            },
            handler=search_web,
            risk="safe",
        )
    )

    registry.register(
        ToolDef(
            name="open_app",
            description="Launch an allowlisted desktop app (chrome, msedge, notepad, calc, explorer, code).",
            parameters={
                "type": "object",
                "properties": {
                    "app_name": {"type": "string", "description": "App name: chrome, msedge, notepad, calc, explorer, code"},
                    "target": {"type": "string", "description": "Optional file path or URL to open with the app"},
                },
                "required": ["app_name"],
            },
            handler=open_app,
            risk="safe",
        )
    )

    registry.register(
        ToolDef(
            name="open_folder",
            description="Open an allowlisted folder in Windows Explorer (Desktop, Downloads, Documents, project folder).",
            parameters={
                "type": "object",
                "properties": {"folder_path": {"type": "string", "description": "Folder path to open"}},
                "required": ["folder_path"],
            },
            handler=open_folder,
            risk="safe",
        )
    )

    registry.register(
        ToolDef(
            name="remember",
            description="Store a personal fact, preference, or detail about the user into persistent memory.",
            parameters={
                "type": "object",
                "properties": {
                    "fact": {"type": "string", "description": "The fact or preference to remember"},
                    "category": {"type": "string", "description": "Optional category, e.g. profile, preference, family"},
                },
                "required": ["fact"],
            },
            handler=tool_remember,
            risk="safe",
        )
    )

    registry.register(
        ToolDef(
            name="recall",
            description="Search persistent memory for facts matching a keyword.",
            parameters={
                "type": "object",
                "properties": {"keyword": {"type": "string", "description": "Keyword to look up in memory"}},
                "required": ["keyword"],
            },
            handler=tool_recall,
            risk="safe",
        )
    )

    registry.register(
        ToolDef(
            name="forget",
            description="Delete saved memories matching a keyword. Deletes data permanently.",
            parameters={
                "type": "object",
                "properties": {"keyword": {"type": "string", "description": "Keyword matching memories to delete"}},
                "required": ["keyword"],
            },
            handler=tool_forget,
            risk="confirm",
        )
    )

    return registry


def tool_remember(fact: str, category: str = "profile") -> str:
    from ..memory import Memory
    mem = Memory()
    try:
        mem.remember(fact, category=category)
        return f"Remembered: {fact}"
    finally:
        mem.close()


def tool_recall(keyword: str) -> str:
    from ..memory import Memory
    mem = Memory()
    try:
        facts = mem.recall(keyword)
        if not facts:
            return f"No memories found matching '{keyword}'."
        return "\n".join(f"- {f}" for f in facts)
    finally:
        mem.close()


def tool_forget(keyword: str) -> str:
    from ..memory import Memory
    mem = Memory()
    try:
        count = mem.forget(keyword)
        if count == 0:
            return f"No memories found matching '{keyword}' to forget."
        return f"Forgotten {count} memor{'y' if count == 1 else 'ies'} matching '{keyword}'."
    finally:
        mem.close()
