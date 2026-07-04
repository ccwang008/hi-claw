"""工具注册与统一分发。"""

from dataclasses import dataclass
from typing import Callable

from config import Config


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: dict
    handler: Callable[..., str]
    requires_confirmation: bool = False

    def api_schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }


class ToolRegistry:
    def __init__(self, tool_specs: list[ToolSpec]):
        self._tools = {spec.name: spec for spec in tool_specs}

    def api_schemas(self) -> list[dict]:
        return [spec.api_schema() for spec in self._tools.values()]

    def tool_names(self) -> set[str]:
        return set(self._tools.keys())

    def confirmation_tool_names(self) -> set[str]:
        return {
            name
            for name, spec in self._tools.items()
            if spec.requires_confirmation
        }

    def requires_confirmation(self, name: str) -> bool:
        spec = self._tools.get(name)
        return bool(spec and spec.requires_confirmation)

    def normalized_input(self, name: str, tool_input: dict, config: Config) -> dict:
        normalized = dict(tool_input)
        if name == "run_bash":
            if normalized.get("timeout") is None:
                normalized["timeout"] = config.bash_timeout
        return normalized

    def dispatch(
        self,
        name: str,
        tool_input: dict,
        config: Config,
        logger=None,
    ) -> str:
        spec = self._tools.get(name)
        if spec is None:
            return f"(工具调用失败:未知工具 {name})"

        try:
            normalized = self.normalized_input(name, tool_input, config)
        except Exception as e:
            if logger:
                logger.exception("工具参数错误: %s(%r)", name, tool_input)
            return f"(工具调用失败:参数错误 {name}: {e})"

        try:
            output = spec.handler(**normalized)
        except TypeError as e:
            if logger:
                logger.exception("工具参数错误: %s(%r)", name, tool_input)
            return f"(工具调用失败:参数错误 {name}: {e})"
        except Exception as e:
            if logger:
                logger.exception("工具执行异常: %s(%r)", name, tool_input)
            return f"(工具调用失败:{name}: {e})"

        return output
