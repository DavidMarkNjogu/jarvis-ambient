from __future__ import annotations

import json
from pathlib import Path
import pytest

from jarvis.tools import ToolRegistry, ToolError, ToolDef


def test_unknown_tool_is_refused(tmp_path: Path) -> None:
    registry = ToolRegistry(log_path=tmp_path / "tool-log.jsonl")
    with pytest.raises(ToolError) as exc_info:
        registry.execute("unknown_tool", {})
    assert "unknown_tool" in str(exc_info.value)


def test_arguments_are_validated_against_the_schema(tmp_path: Path) -> None:
    registry = ToolRegistry(log_path=tmp_path / "tool-log.jsonl")
    registry.register(
        ToolDef(
            name="set_volume",
            description="Set output volume level",
            parameters={
                "type": "object",
                "properties": {
                    "level": {"type": "integer", "minimum": 0, "maximum": 100}
                },
                "required": ["level"],
            },
            handler=lambda level: f"volume {level}",
            risk="safe",
        )
    )

    # Missing required argument
    with pytest.raises(ToolError) as exc_info:
        registry.execute("set_volume", {})
    assert "level" in str(exc_info.value).lower()

    # Wrong type
    with pytest.raises(ToolError) as exc_info:
        registry.execute("set_volume", {"level": "high"})
    assert "level" in str(exc_info.value).lower()

    # Out of range
    with pytest.raises(ToolError) as exc_info:
        registry.execute("set_volume", {"level": 150})
    assert "level" in str(exc_info.value).lower()

    # Test types: number, string, boolean
    registry.register(
        ToolDef(
            name="type_tester",
            description="Tests type validation",
            parameters={
                "type": "object",
                "properties": {
                    "num": {"type": "number"},
                    "txt": {"type": "string"},
                    "flag": {"type": "boolean"},
                },
            },
            handler=lambda **kwargs: kwargs,
            risk="safe",
        )
    )

    # number invalid
    with pytest.raises(ToolError) as exc:
        registry.execute("type_tester", {"num": "not_a_number"})
    assert "number" in str(exc.value).lower()

    with pytest.raises(ToolError) as exc:
        registry.execute("type_tester", {"num": True})
    assert "number" in str(exc.value).lower()

    # string invalid
    with pytest.raises(ToolError) as exc:
        registry.execute("type_tester", {"txt": 12345})
    assert "string" in str(exc.value).lower()

    # boolean invalid
    with pytest.raises(ToolError) as exc:
        registry.execute("type_tester", {"flag": "true"})
    assert "boolean" in str(exc.value).lower()


def test_confirm_first_tools_do_nothing_without_a_yes(tmp_path: Path) -> None:
    called = []
    registry = ToolRegistry(log_path=tmp_path / "tool-log.jsonl")
    registry.register(
        ToolDef(
            name="delete_file",
            description="Delete a file",
            parameters={"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
            handler=lambda path: called.append(path) or "deleted",
            risk="confirm",
        )
    )

    with pytest.raises(ToolError) as exc_info:
        registry.execute("delete_file", {"path": "test.txt"}, confirmed=False)
    assert "confirmation" in str(exc_info.value).lower()
    assert called == []

    # Default without confirmed parameter must also require confirmation
    with pytest.raises(ToolError) as exc_info2:
        registry.execute("delete_file", {"path": "test.txt"})
    assert "confirmation" in str(exc_info2.value).lower()
    assert called == []


def test_confirm_first_tools_run_after_a_yes(tmp_path: Path) -> None:
    called = []
    registry = ToolRegistry(log_path=tmp_path / "tool-log.jsonl")
    registry.register(
        ToolDef(
            name="delete_file",
            description="Delete a file",
            parameters={"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
            handler=lambda path: called.append(path) or "deleted",
            risk="confirm",
        )
    )

    result = registry.execute("delete_file", {"path": "test.txt"}, confirmed=True)
    assert result == "deleted"
    assert called == ["test.txt"]


def test_unlabeled_tools_default_to_confirm_first(tmp_path: Path) -> None:
    called = []
    registry = ToolRegistry(log_path=tmp_path / "tool-log.jsonl")
    # No risk argument passed -> defaults to confirm
    registry.register(
        ToolDef(
            name="reboot_system",
            description="Reboots the machine",
            parameters={"type": "object", "properties": {}},
            handler=lambda: called.append(True) or "rebooted",
        )
    )

    with pytest.raises(ToolError) as exc_info:
        registry.execute("reboot_system", {}, confirmed=False)
    assert "confirmation" in str(exc_info.value).lower()
    assert called == []


def test_every_call_is_logged_with_name_args_and_result(tmp_path: Path) -> None:
    log_file = tmp_path / "tool-log.jsonl"
    registry = ToolRegistry(log_path=log_file)
    registry.register(
        ToolDef(
            name="add_numbers",
            description="Add two numbers",
            parameters={
                "type": "object",
                "properties": {
                    "a": {"type": "integer"},
                    "b": {"type": "integer"},
                },
                "required": ["a", "b"],
            },
            handler=lambda a, b: a + b,
            risk="safe",
        )
    )

    result = registry.execute("add_numbers", {"a": 5, "b": 7})
    assert result == 12

    assert log_file.exists()
    lines = [json.loads(line) for line in log_file.read_text(encoding="utf-8").strip().splitlines()]
    assert len(lines) == 1
    entry = lines[0]
    assert entry["name"] == "add_numbers"
    assert entry["arguments"] == {"a": 5, "b": 7}
    assert entry["result"] == 12
    assert "timestamp" in entry


def test_secrets_are_not_written_to_the_log(tmp_path: Path) -> None:
    log_file = tmp_path / "tool-log.jsonl"
    registry = ToolRegistry(log_path=log_file)
    registry.register(
        ToolDef(
            name="connect_api",
            description="Connect to API",
            parameters={
                "type": "object",
                "properties": {
                    "api_key": {"type": "string"},
                    "token": {"type": "string"},
                    "data": {"type": "string"},
                },
                "required": ["api_key", "token", "data"],
            },
            handler=lambda api_key, token, data: f"connected: {api_key}",
            risk="safe",
        )
    )

    registry.execute("connect_api", {"api_key": "AIzaSySecretKey12345", "token": "Bearer gsk_secrettoken99", "data": "hello"})
    lines = [json.loads(line) for line in log_file.read_text(encoding="utf-8").strip().splitlines()]
    entry = lines[0]
    # Sensitive keys and sensitive values must be masked
    args = entry["arguments"]
    assert args["api_key"] != "AIzaSySecretKey12345"
    assert "[MASKED]" in args["api_key"]
    assert args["token"] != "Bearer gsk_secrettoken99"
    assert "[MASKED]" in args["token"]
    assert args["data"] == "hello"
    assert "AIzaSy" not in json.dumps(entry)
    assert "gsk_secret" not in json.dumps(entry)
