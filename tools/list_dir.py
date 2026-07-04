"""目录列表工具。"""

import os
from pathlib import Path
from typing import Optional

from tool_registry import ToolSpec
from tools.search import SKIP_DIRS


def list_dir(
    path: str = ".",
    pattern: Optional[str] = None,
    recursive: bool = False,
    max_depth: Optional[int] = None,
    show_hidden: bool = False,
    max_results: int = 200,
) -> str:
    """列出目录内容:平铺列表、glob 模式匹配或树状结构。"""
    if not os.path.exists(path):
        return f"(列目录失败:路径不存在 {path})"
    if not os.path.isdir(path):
        return f"(列目录失败:{path} 不是一个目录)"

    if pattern:
        return _list_dir_glob(path, pattern, show_hidden, max_results)
    if recursive:
        return _list_dir_tree(path, max_depth, show_hidden, max_results)
    return _list_dir_flat(path, show_hidden, max_results)


def _list_dir_flat(path: str, show_hidden: bool, max_results: int) -> str:
    try:
        entries = sorted(os.listdir(path))
    except OSError as e:
        return f"(列目录失败:{e})"

    entries = [e for e in entries if e not in SKIP_DIRS]
    if not show_hidden:
        entries = [e for e in entries if not e.startswith(".")]

    if not entries:
        return "(空目录)"

    truncated = len(entries) > max_results
    entries = entries[:max_results]

    lines = [
        name + "/" if os.path.isdir(os.path.join(path, name)) else name
        for name in entries
    ]

    result = "\n".join(lines)
    if truncated:
        result += "\n(结果过多,已截断,建议缩小范围)"
    return result


def _list_dir_glob(path: str, pattern: str, show_hidden: bool, max_results: int) -> str:
    base = Path(path)
    try:
        matched = sorted(base.glob(pattern))
    except ValueError as e:
        return f"(列目录失败:{e})"

    results = []
    for p in matched:
        rel_parts = p.relative_to(base).parts
        if any(part in SKIP_DIRS for part in rel_parts):
            continue
        if not show_hidden and any(part.startswith(".") for part in rel_parts):
            continue
        results.append(str(p) + "/" if p.is_dir() else str(p))

    if not results:
        return "(未找到匹配)"

    truncated = len(results) > max_results
    results = results[:max_results]

    result = "\n".join(results)
    if truncated:
        result += "\n(结果过多,已截断,建议缩小范围)"
    return result


def _list_dir_tree(
    path: str, max_depth: Optional[int], show_hidden: bool, max_results: int
) -> str:
    lines = []
    count = 0
    truncated = False

    def walk(current, depth, prefix):
        nonlocal count, truncated
        if truncated:
            return
        try:
            entries = sorted(os.listdir(current))
        except OSError:
            return

        entries = [e for e in entries if e not in SKIP_DIRS]
        if not show_hidden:
            entries = [e for e in entries if not e.startswith(".")]

        for name in entries:
            if count >= max_results:
                truncated = True
                return
            full = os.path.join(current, name)
            is_dir = os.path.isdir(full)
            lines.append(f"{prefix}{name}/" if is_dir else f"{prefix}{name}")
            count += 1
            if is_dir and (max_depth is None or depth < max_depth):
                walk(full, depth + 1, prefix + "  ")

    walk(path, 1, "")

    if not lines:
        return "(空目录)"

    result = "\n".join(lines)
    if truncated:
        result += "\n(结果过多,已截断,建议缩小范围)"
    return result


LIST_DIR_TOOL = ToolSpec(
    name="list_dir",
    description=(
        "列出目录内容,支持平铺列表、glob 模式匹配(如 '**/*.py')"
        "或树状结构展示,自动跳过 .git/.venv/node_modules 等常见目录。"
    ),
    input_schema={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "要列出的目录路径,默认当前目录。"},
            "pattern": {
                "type": "string",
                "description": "glob 匹配模式,如 '*.py' 或 '**/*.py'(递归),可选。传入后忽略 recursive 参数。",
            },
            "recursive": {
                "type": "boolean",
                "description": "是否以树状结构递归展示子目录,默认 false。",
            },
            "max_depth": {
                "type": "integer",
                "description": "树状展示时的最大递归深度,可选,默认不限制。",
            },
            "show_hidden": {
                "type": "boolean",
                "description": "是否显示以 . 开头的隐藏文件/目录,默认 false。",
            },
            "max_results": {
                "type": "integer",
                "description": "最多返回的条目数量,默认 200。",
            },
        },
        "required": [],
    },
    handler=list_dir,
)
