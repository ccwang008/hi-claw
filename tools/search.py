"""内容搜索工具。"""

import fnmatch
import os
import re
from typing import Optional

from tool_registry import ToolSpec

SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", "node_modules"}


def search(
    pattern: str,
    path: str = ".",
    file_glob: Optional[str] = None,
    max_results: int = 200,
) -> str:
    """在目录树里按正则匹配文件内容,纯 Python 实现,不依赖外部 grep/rg。"""
    regex = re.compile(pattern)
    matches = []
    truncated = False

    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for filename in sorted(files):
            if file_glob and not fnmatch.fnmatch(filename, file_glob):
                continue
            filepath = os.path.join(root, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    for lineno, line in enumerate(f, start=1):
                        if regex.search(line):
                            matches.append(f"{filepath}:{lineno}:{line.rstrip(chr(10))}")
                            if len(matches) >= max_results:
                                truncated = True
                                break
            except (UnicodeDecodeError, OSError):
                continue
            if truncated:
                break
        if truncated:
            break

    if not matches:
        return "(未找到匹配)"

    result = "\n".join(matches)
    if truncated:
        result += "\n(结果过多,已截断,建议缩小搜索范围)"
    return result


SEARCH_TOOL = ToolSpec(
    name="search",
    description="在目录树里按正则表达式搜索文件内容,可选按文件名 glob 模式过滤。",
    input_schema={
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "要搜索的正则表达式。"},
            "path": {"type": "string", "description": "搜索起始目录,默认当前目录。"},
            "file_glob": {
                "type": "string",
                "description": "文件名 glob 过滤模式,如 '*.py',可选。",
            },
            "max_results": {
                "type": "integer",
                "description": "最多返回的匹配数量,默认 200。",
            },
        },
        "required": ["pattern"],
    },
    handler=search,
)
