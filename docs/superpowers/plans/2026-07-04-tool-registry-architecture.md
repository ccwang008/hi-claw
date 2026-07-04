# Tool Registry Architecture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the tool system into a `ToolSpec` + `ToolRegistry` architecture, split tool implementations by domain, preserve existing tool behavior, and update the project wording from "最简龙虾 Agent" to "龙虾 Agent".

**Architecture:** `tool_registry.py` becomes the single execution and schema boundary for tools. The `tools/` package owns domain-specific implementations and exports `ALL_TOOL_SPECS`; `agent.py` only asks the registry for API schemas, confirmation requirements, and dispatch results.

**Tech Stack:** Python 3, dataclasses, Anthropic Messages API tool schema, pytest-compatible existing tests, Markdown project docs.

---

## Current State Notes

The working tree already contains uncommitted tool changes in `tools.py` and `tests/test_tools.py`. The current tool set to preserve is:

- `run_bash`
- `read_file`
- `write_file`
- `mkdir`
- `append_file`
- `delete_file`
- `edit`
- `search`
- `list_dir`

Do not drop `mkdir`, `append_file`, or `delete_file` during the migration.

## File Structure

- Create: `tool_registry.py`
  - Owns `ToolSpec`, `ToolRegistry`, API schema generation, confirmation lookup, default argument injection, and safe dispatch error wrapping.
- Create: `tools/__init__.py`
  - Imports all domain tool specs and exposes `ALL_TOOL_SPECS`.
- Create: `tools/bash.py`
  - Contains `run_bash` and `RUN_BASH_TOOL`.
- Create: `tools/files.py`
  - Contains `read_file`, `write_file`, `mkdir`, `append_file`, `delete_file`, `edit`, and their tool specs.
- Create: `tools/search.py`
  - Contains `search`, `SKIP_DIRS`, and `SEARCH_TOOL`.
- Create: `tools/list_dir.py`
  - Contains `list_dir`, its helper functions, and `LIST_DIR_TOOL`.
- Modify: `agent.py`
  - Replace direct `TOOLS` / `TOOL_HANDLERS` / `NEEDS_CONFIRMATION` imports with registry usage.
- Modify: `tools/__init__.py`
  - During migration, keep compatibility exports for existing `from tools import ...` imports. Python resolves the new `tools/` package before the old top-level `tools.py`, so compatibility must live in the package `__init__`.
- Modify/Delete: `tools.py`
  - After all tool implementations live in `tools/`, retire the old top-level module content. It is no longer a viable import shim once `tools/` exists.
- Modify: `tests/test_agent_loop.py`
  - Add coverage for registry error wrapping through the agent loop.
- Modify: `tests/test_tools.py`
  - Keep existing tool behavior tests working through the compatibility shim.
- Modify: `README.md`
  - Update project title/description and tool count.
- Modify: `CLAUDE.md`
  - Update project title/description.
- Modify: `docs/开发日志/vibecoding日志/2026-07-04-工具系统工程化重构设计.md`
  - Add an implementation-plan entry after this plan is written.

---

### Task 1: Add Tool Registry

**Files:**
- Create: `tool_registry.py`

- [ ] **Step 1: Create `tool_registry.py` with `ToolSpec` and `ToolRegistry`**

Add this file:

```python
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
            normalized.setdefault("timeout", config.bash_timeout)
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

        normalized = self.normalized_input(name, tool_input, config)
        try:
            output = spec.handler(**normalized)
        except TypeError as e:
            if logger:
                logger.exception("工具参数错误: %s(%r)", name, normalized)
            return f"(工具调用失败:参数错误 {name}: {e})"
        except Exception as e:
            if logger:
                logger.exception("工具执行异常: %s(%r)", name, normalized)
            return f"(工具调用失败:{name}: {e})"

        return output
```

- [ ] **Step 2: Run a syntax check**

Run:

```bash
python -m py_compile tool_registry.py
```

Expected: command exits with status 0 and prints no output.

---

### Task 2: Split Bash Tool

**Files:**
- Create: `tools/__init__.py`
- Create: `tools/bash.py`

- [ ] **Step 1: Create the `tools` package and bash tool module**

Add `tools/__init__.py`. Because the package immediately shadows the old top-level `tools.py`, include a temporary compatibility bridge to preserve existing imports until Tasks 3-5 finish the migration:

```python
"""工具包入口。"""

import importlib.util
from pathlib import Path

from tools.bash import RUN_BASH_TOOL, run_bash

_LEGACY_TOOLS_PATH = Path(__file__).resolve().parent.parent / "tools.py"
_legacy_spec = importlib.util.spec_from_file_location("_legacy_tools", _LEGACY_TOOLS_PATH)
_legacy_tools = importlib.util.module_from_spec(_legacy_spec)
assert _legacy_spec and _legacy_spec.loader
_legacy_spec.loader.exec_module(_legacy_tools)

read_file = _legacy_tools.read_file
write_file = _legacy_tools.write_file
mkdir = _legacy_tools.mkdir
append_file = _legacy_tools.append_file
delete_file = _legacy_tools.delete_file
edit = _legacy_tools.edit
search = _legacy_tools.search
list_dir = _legacy_tools.list_dir
TOOLS = _legacy_tools.TOOLS
TOOL_HANDLERS = _legacy_tools.TOOL_HANDLERS
NEEDS_CONFIRMATION = _legacy_tools.NEEDS_CONFIRMATION

ALL_TOOL_SPECS = [
    RUN_BASH_TOOL,
]

__all__ = [
    "ALL_TOOL_SPECS",
    "RUN_BASH_TOOL",
    "run_bash",
    "read_file",
    "write_file",
    "mkdir",
    "append_file",
    "delete_file",
    "edit",
    "search",
    "list_dir",
    "TOOLS",
    "TOOL_HANDLERS",
    "NEEDS_CONFIRMATION",
]
```

Add `tools/bash.py`:

```python
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
```

- [ ] **Step 2: Run a syntax check**

Run:

```bash
python -m py_compile tools/__init__.py tools/bash.py
```

Expected: command exits with status 0 and prints no output.

- [ ] **Step 3: Verify old imports still work during migration**

Run:

```bash
python - <<'PY'
from tools import read_file, run_bash, TOOLS, TOOL_HANDLERS, NEEDS_CONFIRMATION

print(run_bash("echo smoke"))
print(callable(read_file))
print(sorted(tool["name"] for tool in TOOLS))
print(sorted(TOOL_HANDLERS))
print(sorted(NEEDS_CONFIRMATION))
PY
```

Expected output includes `smoke`, `True`, and the current 9 tool names.

---

### Task 3: Split File Tools

**Files:**
- Create: `tools/files.py`
- Modify: `tools/__init__.py`

- [ ] **Step 1: Create `tools/files.py`**

Add this file:

```python
"""文件读写与编辑工具。"""

import os
import shutil
from typing import Optional

from tool_registry import ToolSpec

DEFAULT_READ_LIMIT = 2000


def read_file(path: str, offset: Optional[int] = None, limit: Optional[int] = None) -> str:
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


def mkdir(path: str, parents: bool = True) -> str:
    """创建目录,支持递归创建多级父目录。"""
    if os.path.exists(path):
        return f"(创建失败:目录已存在 {path})"
    try:
        if parents:
            os.makedirs(path, exist_ok=True)
        else:
            os.mkdir(path)
    except OSError as e:
        return f"(创建失败:{e})"
    return f"已创建目录 {path}"


def append_file(path: str, content: str) -> str:
    """在文件末尾追加内容,文件不存在时自动创建。"""
    parent = os.path.dirname(path)
    try:
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(content)
    except OSError as e:
        return f"(追加失败:{e})"
    return f"已追加 {len(content.encode('utf-8'))} 字节到 {path}"


def delete_file(path: str, recursive: bool = False) -> str:
    """删除文件或目录。删除目录时需要设置 recursive=True。"""
    if not os.path.exists(path):
        return f"(删除失败:路径不存在 {path})"

    try:
        if os.path.isfile(path) or os.path.islink(path):
            os.remove(path)
            return f"已删除 {path}"
        if os.path.isdir(path):
            if not recursive:
                return f"(删除失败:{path} 是目录,请设置 recursive=true)"
            shutil.rmtree(path)
            return f"已递归删除 {path}"
        return f"(删除失败:未知类型 {path})"
    except OSError as e:
        return f"(删除失败:{e})"


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

    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)
    except OSError as e:
        return f"(编辑失败:{e})"

    return f"已修改 {path}"


READ_FILE_TOOL = ToolSpec(
    name="read_file",
    description="读取文件内容,按行号显示,支持只读取部分行范围。",
    input_schema={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "文件路径。"},
            "offset": {"type": "integer", "description": "起始行号(从 1 开始),可选。"},
            "limit": {"type": "integer", "description": "最多读取的行数,可选。"},
        },
        "required": ["path"],
    },
    handler=read_file,
)

WRITE_FILE_TOOL = ToolSpec(
    name="write_file",
    description="写入文件内容,若文件已存在则整体覆盖,自动创建父目录。",
    input_schema={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "文件路径。"},
            "content": {"type": "string", "description": "要写入的完整内容。"},
        },
        "required": ["path", "content"],
    },
    handler=write_file,
    requires_confirmation=True,
)

MKDIR_TOOL = ToolSpec(
    name="mkdir",
    description="创建目录,支持递归创建多级父目录。",
    input_schema={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "要创建的目录路径。"},
            "parents": {
                "type": "boolean",
                "description": "是否递归创建父目录,默认 true。",
            },
        },
        "required": ["path"],
    },
    handler=mkdir,
)

APPEND_FILE_TOOL = ToolSpec(
    name="append_file",
    description="在文件末尾追加内容,文件不存在时自动创建。",
    input_schema={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "文件路径。"},
            "content": {"type": "string", "description": "要追加的内容。"},
        },
        "required": ["path", "content"],
    },
    handler=append_file,
    requires_confirmation=True,
)

DELETE_FILE_TOOL = ToolSpec(
    name="delete_file",
    description="删除文件或目录。删除目录时需要设置 recursive=true。",
    input_schema={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "要删除的文件或目录路径。"},
            "recursive": {
                "type": "boolean",
                "description": "删除目录时是否递归删除所有内容,默认 false。",
            },
        },
        "required": ["path"],
    },
    handler=delete_file,
    requires_confirmation=True,
)

EDIT_TOOL = ToolSpec(
    name="edit",
    description="对文件做精确字符串替换,old_string 必须在文件中唯一出现,否则需设置 replace_all。",
    input_schema={
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
    handler=edit,
    requires_confirmation=True,
)
```

- [ ] **Step 2: Expand `tools/__init__.py` exports**

Replace `tools/__init__.py` with:

```python
"""工具包入口。"""

from tools.bash import RUN_BASH_TOOL, run_bash
from tools.files import (
    APPEND_FILE_TOOL,
    DELETE_FILE_TOOL,
    EDIT_TOOL,
    MKDIR_TOOL,
    READ_FILE_TOOL,
    WRITE_FILE_TOOL,
    append_file,
    delete_file,
    edit,
    mkdir,
    read_file,
    write_file,
)

ALL_TOOL_SPECS = [
    RUN_BASH_TOOL,
    READ_FILE_TOOL,
    WRITE_FILE_TOOL,
    MKDIR_TOOL,
    APPEND_FILE_TOOL,
    DELETE_FILE_TOOL,
    EDIT_TOOL,
]

__all__ = [
    "ALL_TOOL_SPECS",
    "RUN_BASH_TOOL",
    "READ_FILE_TOOL",
    "WRITE_FILE_TOOL",
    "MKDIR_TOOL",
    "APPEND_FILE_TOOL",
    "DELETE_FILE_TOOL",
    "EDIT_TOOL",
    "run_bash",
    "read_file",
    "write_file",
    "mkdir",
    "append_file",
    "delete_file",
    "edit",
]
```

- [ ] **Step 3: Run a syntax check**

Run:

```bash
python -m py_compile tools/files.py tools/__init__.py
```

Expected: command exits with status 0 and prints no output.

---

### Task 4: Split Search and List Directory Tools

**Files:**
- Create: `tools/search.py`
- Create: `tools/list_dir.py`
- Modify: `tools/__init__.py`

- [ ] **Step 1: Create `tools/search.py`**

Add this file:

```python
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
```

- [ ] **Step 2: Create `tools/list_dir.py`**

Add this file:

```python
"""目录浏览工具。"""

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
```

- [ ] **Step 3: Expand `tools/__init__.py` exports again**

Replace `tools/__init__.py` with:

```python
"""工具包入口。"""

from tools.bash import RUN_BASH_TOOL, run_bash
from tools.files import (
    APPEND_FILE_TOOL,
    DELETE_FILE_TOOL,
    EDIT_TOOL,
    MKDIR_TOOL,
    READ_FILE_TOOL,
    WRITE_FILE_TOOL,
    append_file,
    delete_file,
    edit,
    mkdir,
    read_file,
    write_file,
)
from tools.list_dir import LIST_DIR_TOOL, list_dir
from tools.search import SEARCH_TOOL, search

ALL_TOOL_SPECS = [
    RUN_BASH_TOOL,
    READ_FILE_TOOL,
    WRITE_FILE_TOOL,
    MKDIR_TOOL,
    APPEND_FILE_TOOL,
    DELETE_FILE_TOOL,
    EDIT_TOOL,
    SEARCH_TOOL,
    LIST_DIR_TOOL,
]

__all__ = [
    "ALL_TOOL_SPECS",
    "RUN_BASH_TOOL",
    "READ_FILE_TOOL",
    "WRITE_FILE_TOOL",
    "MKDIR_TOOL",
    "APPEND_FILE_TOOL",
    "DELETE_FILE_TOOL",
    "EDIT_TOOL",
    "SEARCH_TOOL",
    "LIST_DIR_TOOL",
    "run_bash",
    "read_file",
    "write_file",
    "mkdir",
    "append_file",
    "delete_file",
    "edit",
    "search",
    "list_dir",
]
```

- [ ] **Step 4: Run a syntax check**

Run:

```bash
python -m py_compile tools/search.py tools/list_dir.py tools/__init__.py
```

Expected: command exits with status 0 and prints no output.

---

### Task 5: Finalize Package Compatibility Exports

**Files:**
- Modify: `tools/__init__.py`
- Modify/Delete: `tools.py`

- [ ] **Step 1: Replace temporary legacy bridge in `tools/__init__.py` with registry-derived exports**

Replace the contents of `tools/__init__.py` with:

```python
"""工具包入口。"""

from tool_registry import ToolRegistry
from tools.bash import RUN_BASH_TOOL, run_bash
from tools.files import (
    APPEND_FILE_TOOL,
    DELETE_FILE_TOOL,
    EDIT_TOOL,
    MKDIR_TOOL,
    READ_FILE_TOOL,
    WRITE_FILE_TOOL,
    append_file,
    delete_file,
    edit,
    mkdir,
    read_file,
    write_file,
)
from tools.list_dir import LIST_DIR_TOOL, list_dir
from tools.search import SEARCH_TOOL, search

ALL_TOOL_SPECS = [
    RUN_BASH_TOOL,
    READ_FILE_TOOL,
    WRITE_FILE_TOOL,
    MKDIR_TOOL,
    APPEND_FILE_TOOL,
    DELETE_FILE_TOOL,
    EDIT_TOOL,
    SEARCH_TOOL,
    LIST_DIR_TOOL,
]

DEFAULT_REGISTRY = ToolRegistry(ALL_TOOL_SPECS)

TOOLS = DEFAULT_REGISTRY.api_schemas()
TOOL_HANDLERS = {
    spec.name: spec.handler
    for spec in ALL_TOOL_SPECS
}
NEEDS_CONFIRMATION = DEFAULT_REGISTRY.confirmation_tool_names()

__all__ = [
    "ALL_TOOL_SPECS",
    "DEFAULT_REGISTRY",
    "TOOLS",
    "TOOL_HANDLERS",
    "NEEDS_CONFIRMATION",
    "run_bash",
    "read_file",
    "write_file",
    "mkdir",
    "append_file",
    "delete_file",
    "edit",
    "search",
    "list_dir",
]
```

- [ ] **Step 2: Retire top-level `tools.py`**

Delete `tools.py` after confirming no code imports it by file path. Normal `import tools` now resolves to the package and receives the compatibility exports from `tools/__init__.py`.

- [ ] **Step 3: Verify compatibility imports**

Run:

```bash
python - <<'PY'
from tools import TOOLS, TOOL_HANDLERS, NEEDS_CONFIRMATION

names = {tool["name"] for tool in TOOLS}
print(sorted(names))
print(sorted(TOOL_HANDLERS))
print(sorted(NEEDS_CONFIRMATION))
PY
```

Expected output includes these exact sorted tool names in the first two lines:

```text
['append_file', 'delete_file', 'edit', 'list_dir', 'mkdir', 'read_file', 'run_bash', 'search', 'write_file']
['append_file', 'delete_file', 'edit', 'list_dir', 'mkdir', 'read_file', 'run_bash', 'search', 'write_file']
['append_file', 'delete_file', 'edit', 'run_bash', 'write_file']
```

---

### Task 6: Update Agent Loop to Use Registry

**Files:**
- Modify: `agent.py`

- [ ] **Step 1: Update imports and add registry construction**

In `agent.py`, replace the old direct tool registry imports with:

```python
from tool_registry import ToolRegistry
from tools import ALL_TOOL_SPECS

DEFAULT_REGISTRY = ToolRegistry(ALL_TOOL_SPECS)
```

- [ ] **Step 2: Replace `_dispatch_tool`**

Replace the current `_dispatch_tool` function with:

```python
def _dispatch_tool(block, config: Config, confirm_fn, logger, registry=DEFAULT_REGISTRY) -> str:
    name = block.name
    raw_input = block.input
    tool_input = registry.normalized_input(name, raw_input, config)

    if logger:
        logger.info("工具请求: %s(%r)", name, tool_input)

    if registry.requires_confirmation(name):
        confirmed = confirm_fn(name, tool_input)
        if logger:
            logger.info("确认结果: %s -> %s", name, "同意" if confirmed else "拒绝")
        if not confirmed:
            return "(用户拒绝执行该操作)"

    output = registry.dispatch(name, tool_input, config, logger=logger)
    if logger:
        logger.info("工具输出: %s", output[:2000])
    return output
```

- [ ] **Step 3: Add registry parameter to `run_turn`**

Change the `run_turn` signature from:

```python
def run_turn(client, messages, config: Config, confirm_fn=default_confirm, logger=None):
```

to:

```python
def run_turn(
    client,
    messages,
    config: Config,
    confirm_fn=default_confirm,
    logger=None,
    registry=DEFAULT_REGISTRY,
):
```

- [ ] **Step 4: Use registry schemas in the API call**

Inside `run_turn`, replace:

```python
tools=TOOLS,
```

with:

```python
tools=registry.api_schemas(),
```

- [ ] **Step 5: Pass registry into `_dispatch_tool`**

Inside the `for block in response.content` loop, replace:

```python
output = _dispatch_tool(block, config, confirm_fn, logger)
```

with:

```python
output = _dispatch_tool(block, config, confirm_fn, logger, registry)
```

- [ ] **Step 6: Run a syntax check**

Run:

```bash
python -m py_compile agent.py
```

Expected: command exits with status 0 and prints no output.

---

### Task 7: Preserve and Extend Tests

**Files:**
- Modify: `tests/test_agent_loop.py`

- [ ] **Step 1: Add imports for registry test helpers**

At the top of `tests/test_agent_loop.py`, after the existing imports, add:

```python
from tool_registry import ToolRegistry, ToolSpec
```

- [ ] **Step 2: Add test for unknown tool error wrapping**

Append this test to `tests/test_agent_loop.py`:

```python
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
```

- [ ] **Step 3: Add test for tool parameter error wrapping**

Append this test to `tests/test_agent_loop.py`:

```python
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
```

- [ ] **Step 4: Run focused tests**

Run:

```bash
pytest tests/test_agent_loop.py tests/test_tools.py -v
```

Expected: all tests pass. If `pytest` is unavailable in the shell, run:

```bash
python -m pytest tests/test_agent_loop.py tests/test_tools.py -v
```

Expected: all tests pass.

---

### Task 8: Update Project Wording and Docs

**Files:**
- Modify: `README.md`
- Modify: `CLAUDE.md`
- Modify: `docs/开发日志/vibecoding日志/2026-07-04-工具系统工程化重构设计.md`

- [ ] **Step 1: Update README title and description**

In `README.md`, use:

```markdown
# 龙虾 Agent 🦞 (my-claw)

一个可扩展的命令行 AI 编码 Agent。它在终端里跑一个多轮对话循环,Claude 可以调用工具在你的机器上真正执行操作,形成「对话 + 干活」的 agentic loop。
```

- [ ] **Step 2: Update README project structure**

In the README project structure block, replace the old flat tool description with:

```text
my-claw/
  agent.py          # CLI 入口 + 主循环(run_turn 函数)
  config.py         # 配置:Config dataclass + load_config()
  tool_registry.py  # ToolSpec + ToolRegistry,统一管理工具 schema/确认/分发
  tools/            # 按领域拆分的工具实现与 ToolSpec
    bash.py
    files.py
    search.py
    list_dir.py
  requirements.txt
  tests/
    test_tools.py
    test_config.py
    test_agent_loop.py
  logs/             # 运行时生成,每次会话一个日志文件(已加入 .gitignore)
```

- [ ] **Step 3: Update README tool list**

Replace the README tool list with:

```markdown
Agent 可以调用以下工具:

- **run_bash**:执行 shell 命令
- **read_file**:按行号读取文件内容,支持 `offset`/`limit` 分页
- **write_file**:整体写入/覆盖文件,自动创建父目录
- **mkdir**:创建目录,支持递归创建父目录
- **append_file**:在文件末尾追加内容,文件不存在时自动创建
- **delete_file**:删除文件或目录,删除目录时需要 `recursive=true`
- **edit**:对文件做精确字符串替换(`old_string` 必须唯一,否则需设置 `replace_all`)
- **search**:在目录树里按正则搜索文件内容,纯 Python 实现,支持 `file_glob` 过滤,自动跳过 `.git`/`.venv`/`__pycache__`/`node_modules`
- **list_dir**:列出目录内容,支持平铺列表、glob 匹配和树状结构展示

其中 `run_bash`、`write_file`、`append_file`、`delete_file`、`edit` 会修改文件系统或执行命令,每次调用前都会打印出操作详情并等你输入 `y` 确认(默认 `N`,即回车就跳过)。其他工具是纯读或低风险操作,不需要确认。
```

- [ ] **Step 4: Update CLAUDE heading and description**

In `CLAUDE.md`, use:

```markdown
# my-claw

龙虾 Agent 🦞 —— 项目说明见 [README.md](README.md)。
```

- [ ] **Step 5: Append implementation-plan note to vibecoding log**

Append this section to `docs/开发日志/vibecoding日志/2026-07-04-工具系统工程化重构设计.md`:

```markdown

## 实施方案

已补充实施方案:

- `docs/superpowers/plans/2026-07-04-tool-registry-architecture.md`

方案把当前工作区已有的 9 个工具纳入迁移范围,避免重构时丢失 `mkdir`、`append_file`、`delete_file`。
```

- [ ] **Step 6: Search for old wording**

Run:

```bash
rg -n "最简龙虾 Agent|五个工具|5 个工具|6 个工具" README.md CLAUDE.md AGENTS.md docs
```

Expected: matches may remain only in historical design/log context where the old wording is being discussed, not as current project positioning.

---

### Task 9: Full Verification

**Files:**
- No edits unless verification reveals an issue.

- [ ] **Step 1: Run syntax checks for all Python files**

Run:

```bash
python -m py_compile agent.py config.py tool_registry.py tools/*.py tests/*.py
```

Expected: command exits with status 0 and prints no output.

- [ ] **Step 2: Run the test suite**

Run:

```bash
pytest -v
```

Expected: all tests pass. If `pytest` is unavailable, run:

```bash
python -m pytest -v
```

Expected: all tests pass.

- [ ] **Step 3: Manually inspect registry output**

Run:

```bash
python - <<'PY'
from tools import DEFAULT_REGISTRY

print(len(DEFAULT_REGISTRY.api_schemas()))
print(sorted(DEFAULT_REGISTRY.tool_names()))
print(sorted(DEFAULT_REGISTRY.confirmation_tool_names()))
PY
```

Expected output:

```text
9
['append_file', 'delete_file', 'edit', 'list_dir', 'mkdir', 'read_file', 'run_bash', 'search', 'write_file']
['append_file', 'delete_file', 'edit', 'run_bash', 'write_file']
```

- [ ] **Step 4: Check git diff**

Run:

```bash
git diff --stat
```

Expected: diff includes the registry refactor, tools package, agent update, tests, README/CLAUDE wording, spec/log/plan docs. The `.trae/` untracked directory should remain untouched unless the user explicitly asks to include it.
