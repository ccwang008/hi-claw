"""文件系统工具。"""

import os
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
            import shutil

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
