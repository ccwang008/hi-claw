"""Shell 命令工具。"""

import subprocess

from tool_registry import ToolSpec


def run_bash(command: str, timeout: int = 60) -> str:
    """执行一条 shell 命令,返回合并后的输出(带超时保护)。"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return f"(命令执行超时,已在 {timeout} 秒后中止)"
    output = (result.stdout or "") + (result.stderr or "")
    return output.strip() or "(no output)"


RUN_BASH_TOOL = ToolSpec(
    name="run_bash",
    description="在用户的机器上执行一条 shell 命令,并返回它的标准输出和标准错误。",
    input_schema={
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "要执行的 shell 命令,例如 'ls -la'。",
            }
        },
        "required": ["command"],
    },
    handler=run_bash,
    requires_confirmation=True,
)
