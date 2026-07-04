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
