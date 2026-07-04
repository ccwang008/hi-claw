from unittest.mock import Mock

from agent import run_turn
from config import Config
from tool_registry import ToolRegistry, ToolSpec


def make_config(**overrides):
    defaults = dict(
        model="claude-haiku-4-5",
        base_url=None,
        max_tokens=2048,
        bash_timeout=60,
        log_dir="logs",
    )
    defaults.update(overrides)
    return Config(**defaults)


class FakeTextBlock:
    type = "text"

    def __init__(self, text):
        self.text = text


class FakeToolUseBlock:
    type = "tool_use"

    def __init__(self, id, name, input):
        self.id = id
        self.name = name
        self.input = input


class FakeResponse:
    def __init__(self, content, stop_reason):
        self.content = content
        self.stop_reason = stop_reason


def make_client(responses):
    client = Mock()
    client.messages.create = Mock(side_effect=responses)
    return client


def test_run_turn_text_only_response_stops_loop():
    client = make_client([FakeResponse([FakeTextBlock("你好")], stop_reason="end_turn")])
    messages = [{"role": "user", "content": "hi"}]

    result = run_turn(client, messages, make_config())

    assert client.messages.create.call_count == 1
    assert result[-1]["role"] == "assistant"


def test_run_turn_dispatches_tool_not_needing_confirmation(tmp_path):
    target = tmp_path / "sample.txt"
    target.write_text("line one\n")

    responses = [
        FakeResponse(
            [FakeToolUseBlock("tool1", "read_file", {"path": str(target)})],
            stop_reason="tool_use",
        ),
        FakeResponse([FakeTextBlock("done")], stop_reason="end_turn"),
    ]
    client = make_client(responses)
    messages = [{"role": "user", "content": "read it"}]

    def confirm_fn(name, tool_input):
        raise AssertionError("read_file should not require confirmation")

    result = run_turn(client, messages, make_config(), confirm_fn=confirm_fn)

    tool_result_message = result[-2]
    assert tool_result_message["role"] == "user"
    assert "line one" in tool_result_message["content"][0]["content"]


def test_run_turn_confirmed_tool_executes(tmp_path):
    target = tmp_path / "new.txt"

    responses = [
        FakeResponse(
            [
                FakeToolUseBlock(
                    "tool1", "write_file", {"path": str(target), "content": "hello"}
                )
            ],
            stop_reason="tool_use",
        ),
        FakeResponse([FakeTextBlock("done")], stop_reason="end_turn"),
    ]
    client = make_client(responses)
    messages = [{"role": "user", "content": "write it"}]

    run_turn(client, messages, make_config(), confirm_fn=lambda name, inp: True)

    assert target.read_text() == "hello"


def test_run_turn_declined_tool_does_not_execute(tmp_path):
    target = tmp_path / "new.txt"

    responses = [
        FakeResponse(
            [
                FakeToolUseBlock(
                    "tool1", "write_file", {"path": str(target), "content": "hello"}
                )
            ],
            stop_reason="tool_use",
        ),
        FakeResponse([FakeTextBlock("done")], stop_reason="end_turn"),
    ]
    client = make_client(responses)
    messages = [{"role": "user", "content": "write it"}]

    result = run_turn(client, messages, make_config(), confirm_fn=lambda name, inp: False)

    assert not target.exists()
    tool_result_message = result[-2]
    assert "拒绝" in tool_result_message["content"][0]["content"]


def test_run_turn_bash_uses_config_timeout():
    responses = [
        FakeResponse(
            [FakeToolUseBlock("tool1", "run_bash", {"command": "sleep 2"})],
            stop_reason="tool_use",
        ),
        FakeResponse([FakeTextBlock("done")], stop_reason="end_turn"),
    ]
    client = make_client(responses)
    messages = [{"role": "user", "content": "run it"}]

    result = run_turn(
        client, messages, make_config(bash_timeout=1), confirm_fn=lambda name, inp: True
    )

    tool_result_message = result[-2]
    assert "超时" in tool_result_message["content"][0]["content"]


def test_run_turn_unknown_tool_returns_tool_result_error():
    responses = [
        FakeResponse(
            [FakeToolUseBlock("tool1", "missing_tool", {"path": "x"})],
            stop_reason="tool_use",
        ),
        FakeResponse([FakeTextBlock("done")], stop_reason="end_turn"),
    ]
    client = make_client(responses)
    messages = [{"role": "user", "content": "call missing tool"}]

    result = run_turn(client, messages, make_config())

    tool_result_message = result[-2]
    assert "未知工具 missing_tool" in tool_result_message["content"][0]["content"]


def test_run_turn_tool_parameter_error_returns_tool_result_error():
    def sample_tool(required):
        return required

    registry = ToolRegistry(
        [
            ToolSpec(
                name="sample_tool",
                description="sample",
                input_schema={
                    "type": "object",
                    "properties": {"required": {"type": "string"}},
                    "required": ["required"],
                },
                handler=sample_tool,
            )
        ]
    )
    responses = [
        FakeResponse(
            [FakeToolUseBlock("tool1", "sample_tool", {"extra": "x"})],
            stop_reason="tool_use",
        ),
        FakeResponse([FakeTextBlock("done")], stop_reason="end_turn"),
    ]
    client = make_client(responses)
    messages = [{"role": "user", "content": "call bad tool"}]

    result = run_turn(client, messages, make_config(), registry=registry)

    tool_result_message = result[-2]
    assert "参数错误 sample_tool" in tool_result_message["content"][0]["content"]
