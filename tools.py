"""Agent 可调用的工具:schema 定义 + 实现 + 分发注册表。"""

import fnmatch
import os
import re
import subprocess
from pathlib import Path

DEFAULT_READ_LIMIT = 2000
SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", "node_modules"}


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


def read_file(path: str, offset: int | None = None, limit: int | None = None) -> str:
    """按行读取文件,cat -n 风格输出行号+内容。"""
    if os.path.isdir(path):
        return f"(读取失败:{path} 是一个目录)"
    if not os.path.exists(path):
        return f"(读取失败:文件不存在 {path})"

    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except UnicodeDecodeError:
        return f"(读取失败:{path} 无法读取,可能不是文本文件或编码不是 utf-8)"
    except OSError as e:
        return f"(读取失败:{e})"

    start = (offset - 1) if offset else 0
    count = limit if limit else DEFAULT_READ_LIMIT
    selected = lines[start : start + count]

    result_lines = [
        f"{start + i + 1:6d}\t{line.rstrip(chr(10))}"
        for i, line in enumerate(selected)
    ]

    remaining = len(lines) - (start + len(selected))
    if remaining > 0:
        result_lines.append(f"(还有 {remaining} 行未显示,可用 offset/limit 分页)")

    return "\n".join(result_lines) if result_lines else "(空文件)"


def write_file(path: str, content: str) -> str:
    """整体写入/覆盖文件,自动创建父目录。"""
    parent = os.path.dirname(path)
    try:
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
    except OSError as e:
        return f"(写入失败:{e})"
    return f"已写入 {path}({len(content.encode('utf-8'))} 字节)"


def edit(path: str, old_string: str, new_string: str, replace_all: bool = False) -> str:
    """对文件做精确字符串替换。"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    except OSError as e:
        return f"(编辑失败:{e})"

    count = content.count(old_string)
    if count == 0:
        return f"(编辑失败:未找到匹配文本 {old_string!r})"
    if count > 1 and not replace_all:
        return (
            f"(编辑失败:找到 {count} 处匹配,请提供更多上下文使其唯一,"
            "或设置 replace_all=true)"
        )

    if replace_all:
        new_content = content.replace(old_string, new_string)
    else:
        new_content = content.replace(old_string, new_string, 1)

    with open(path, "w", encoding="utf-8") as f:
        f.write(new_content)

    return f"已修改 {path}"


def search(
    pattern: str,
    path: str = ".",
    file_glob: str | None = None,
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


def list_dir(
    path: str = ".",
    pattern: str | None = None,
    recursive: bool = False,
    max_depth: int | None = None,
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
    path: str, max_depth: int | None, show_hidden: bool, max_results: int
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


TOOLS = [
    {
        "name": "run_bash",
        "description": "在用户的机器上执行一条 shell 命令,并返回它的标准输出和标准错误。",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "要执行的 shell 命令,例如 'ls -la'。",
                }
            },
            "required": ["command"],
        },
    },
    {
        "name": "read_file",
        "description": "读取文件内容,按行号显示,支持只读取部分行范围。",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "文件路径。"},
                "offset": {"type": "integer", "description": "起始行号(从 1 开始),可选。"},
                "limit": {"type": "integer", "description": "最多读取的行数,可选。"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "写入文件内容,若文件已存在则整体覆盖,自动创建父目录。",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "文件路径。"},
                "content": {"type": "string", "description": "要写入的完整内容。"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "edit",
        "description": "对文件做精确字符串替换,old_string 必须在文件中唯一出现,否则需设置 replace_all。",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "文件路径。"},
                "old_string": {"type": "string", "description": "要被替换的原始文本。"},
                "new_string": {"type": "string", "description": "替换后的新文本。"},
                "replace_all": {
                    "type": "boolean",
                    "description": "是否替换所有出现的位置,默认 false。",
                },
            },
            "required": ["path", "old_string", "new_string"],
        },
    },
    {
        "name": "search",
        "description": "在目录树里按正则表达式搜索文件内容,可选按文件名 glob 模式过滤。",
        "input_schema": {
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
    },
    {
        "name": "list_dir",
        "description": (
            "列出目录内容,支持平铺列表、glob 模式匹配(如 '**/*.py')"
            "或树状结构展示,自动跳过 .git/.venv/node_modules 等常见目录。"
        ),
        "input_schema": {
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
    },
]

TOOL_HANDLERS = {
    "run_bash": run_bash,
    "read_file": read_file,
    "write_file": write_file,
    "edit": edit,
    "search": search,
    "list_dir": list_dir,
}

NEEDS_CONFIRMATION = {"run_bash", "write_file", "edit"}
