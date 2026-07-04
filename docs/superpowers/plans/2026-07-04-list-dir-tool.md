# list_dir 工具 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `tools.py` 中新增一个统一的 `list_dir` 工具,支持平铺列目录、glob 模式匹配、树状结构展示三种模式,补齐 agent 缺失的目录浏览能力。

**Architecture:** `list_dir` 作为唯一的公开入口函数,先做路径存在性/类型校验,再根据 `pattern`/`recursive` 参数分发给三个内部辅助函数之一:`_list_dir_flat`(默认平铺列表)、`_list_dir_glob`(glob 匹配,用 `pathlib.Path.glob` 实现,原生支持 `**` 递归)、`_list_dir_tree`(递归遍历输出缩进树状文本)。三者共享统一的 `SKIP_DIRS` 忽略规则、隐藏文件过滤规则、`max_results` 截断规则。

**Tech Stack:** Python 标准库(`os`、`pathlib`),无新增第三方依赖。

## Global Constraints

- 不引入任何外部依赖,只用标准库(源自 spec:"不引入新的外部依赖")
- 错误处理返回字符串 `"(列目录失败:...)"`,不抛异常(源自 spec 的统一错误风格)
- 树状展示用简单的两空格缩进表示层级,不使用 `├──`/`└──` 等制图字符(为保持实现最简)
- 项目未初始化 git 仓库(无 `.git` 目录),因此本计划**不包含 git commit 步骤**
- 不加入 `NEEDS_CONFIRMATION`(源自 spec:纯只读操作)
- **测试策略(按 [docs/开发规范.md](../../开发规范.md) 现阶段规定):本次实现暂不为 `list_dir` 编写测试用例,只需保证已有测试套件(`pytest -v`)不被破坏。测试留待后续统一补齐。**

---

### Task 1: 平铺列目录模式 + 分发骨架

**Files:**
- Modify: `tools.py`(在 `search` 函数之后、`TOOLS` 列表之前,即原第 138-141 行之间插入新代码)

**Interfaces:**
- Produces: `list_dir(path: str = ".", pattern: str | None = None, recursive: bool = False, max_depth: int | None = None, show_hidden: bool = False, max_results: int = 200) -> str`(本任务只实现平铺分支,`pattern`/`recursive` 参数先接受但暂不生效,后续任务接入)
- Produces: `_list_dir_flat(path: str, show_hidden: bool, max_results: int) -> str`
- Consumes: 模块级常量 `SKIP_DIRS`(已存在于 `tools.py` 第 9 行)

- [ ] **Step 1: 实现 `list_dir` 分发骨架与 `_list_dir_flat`**

在 `tools.py` 的 `search` 函数结束(第 138 行)之后、`TOOLS = [` (第 141 行)之前插入:

```python
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
```

- [ ] **Step 2: 手动冒烟检查**

Run: `python -c "from tools import list_dir; print(list_dir('.'))"`
Expected: 打印当前目录下的条目列表,`docs/`、`tests/` 等目录带 `/` 后缀,按名称排序,不包含 `.git`(若存在)等 `SKIP_DIRS` 目录。

---

### Task 2: glob 模式匹配

**Files:**
- Modify: `tools.py`(顶部 import 区块 + `list_dir` 函数体 + 新增 `_list_dir_glob`)

**Interfaces:**
- Consumes: Task 1 产出的 `list_dir(...)`(修改其函数体,增加 pattern 分支)、模块级 `SKIP_DIRS`
- Produces: `_list_dir_glob(path: str, pattern: str, show_hidden: bool, max_results: int) -> str`

- [ ] **Step 1: 实现 glob 分支**

在 `tools.py` 顶部 import 区块(第 3-6 行)加入:

```python
from pathlib import Path
```

将 `list_dir` 函数体中的:

```python
    return _list_dir_flat(path, show_hidden, max_results)
```

替换为:

```python
    if pattern:
        return _list_dir_glob(path, pattern, show_hidden, max_results)
    return _list_dir_flat(path, show_hidden, max_results)
```

在 `_list_dir_flat` 函数之后新增:

```python
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
```

- [ ] **Step 2: 手动冒烟检查**

Run: `python -c "from tools import list_dir; print(list_dir('.', pattern='**/*.py'))"`
Expected: 打印项目内所有 `.py` 文件路径(包括 `tools.py`、`agent.py`、`config.py`、`tests/*.py`),不包含 `.txt`/`.md` 等其他类型文件。

---

### Task 3: 树状结构展示

**Files:**
- Modify: `tools.py`(`list_dir` 函数体 + 新增 `_list_dir_tree`)

**Interfaces:**
- Consumes: Task 2 产出的 `list_dir(...)`(再次修改函数体,增加 recursive 分支)、模块级 `SKIP_DIRS`
- Produces: `_list_dir_tree(path: str, max_depth: int | None, show_hidden: bool, max_results: int) -> str`

- [ ] **Step 1: 实现树状分支**

将 `list_dir` 函数体中的:

```python
    if pattern:
        return _list_dir_glob(path, pattern, show_hidden, max_results)
    return _list_dir_flat(path, show_hidden, max_results)
```

替换为:

```python
    if pattern:
        return _list_dir_glob(path, pattern, show_hidden, max_results)
    if recursive:
        return _list_dir_tree(path, max_depth, show_hidden, max_results)
    return _list_dir_flat(path, show_hidden, max_results)
```

在 `_list_dir_glob` 函数之后新增:

```python
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
```

- [ ] **Step 2: 手动冒烟检查**

Run: `python -c "from tools import list_dir; print(list_dir('tests', recursive=True))"`
Expected: 打印 `tests/` 目录的树状结构(目前是平铺文件,应看到 `test_agent_loop.py`、`test_config.py`、`test_tools.py` 三个文件,无嵌套子目录时不体现缩进层级)。

---

### Task 4: 注册工具 schema 与 handler

**Files:**
- Modify: `tools.py`(`TOOLS` 列表、`TOOL_HANDLERS` 字典)
- Modify: `tests/test_tools.py`(仅修正因新增工具而过时的既有断言,不新增测试)

**Interfaces:**
- Consumes: Task 1-3 产出的 `list_dir(...)`
- Produces: `TOOLS` 中新增 `name="list_dir"` 条目;`TOOL_HANDLERS["list_dir"] = list_dir`

- [ ] **Step 1: 注册工具**

在 `tools.py` 的 `TOOLS` 列表中,`search` 条目(第 198-217 行)之后、列表结尾 `]` 之前新增:

```python
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
```

在 `TOOL_HANDLERS` 字典中加入一行:

```python
    "list_dir": list_dir,
```

- [ ] **Step 2: 修正因新增工具而过时的既有断言**

`tests/test_tools.py` 中已有的 `test_tools_schema_names_match_handlers` 断言了工具名单是固定的 5 个,新增 `list_dir` 后会失败。这不是"新写测试",只是维持已有测试套件能跑通,按 [docs/开发规范.md](../../开发规范.md) 的例外规定需要修正。

将:

```python
def test_tools_schema_names_match_handlers():
    schema_names = {tool["name"] for tool in TOOLS}
    handler_names = set(TOOL_HANDLERS.keys())

    assert schema_names == handler_names
    assert schema_names == {"run_bash", "read_file", "write_file", "edit", "search"}
```

替换为:

```python
def test_tools_schema_names_match_handlers():
    schema_names = {tool["name"] for tool in TOOLS}
    handler_names = set(TOOL_HANDLERS.keys())

    assert schema_names == handler_names
    assert schema_names == {
        "run_bash",
        "read_file",
        "write_file",
        "edit",
        "search",
        "list_dir",
    }
```

`test_needs_confirmation_is_subset_of_tool_names` 无需修改(`list_dir` 不加入 `NEEDS_CONFIRMATION`,该测试断言的仍是原有三个工具名,依然成立)。

- [ ] **Step 3: 运行已有测试套件确认未被破坏**

Run: `pytest -v`
Expected: 全部 PASS(仍为 29 个测试,只是其中一个断言内容已更新)

---

### Task 5: 手动验证与文档归档

**Files:**
- Modify: `docs/superpowers/plans/2026-07-04-list-dir-tool.md`(本文件,追加验证记录)
- Modify: `docs/superpowers/specs/2026-07-04-list-dir-tool-design.md`(更新"结果"章节状态)

**Interfaces:**
- Consumes: 已完整实现并注册的 `list_dir` 工具

- [ ] **Step 1: 运行 agent 做手动验证**

在项目根目录执行 `python agent.py`,在交互中依次让 agent 调用 `list_dir` 完成三种场景:
1. 平铺列出项目根目录(默认参数)
2. glob 匹配 `"**/*.py"` 找出所有 Python 文件
3. 树状展示 `tests/` 目录结构

确认:三次调用都不触发确认提示(因为 `list_dir` 不在 `NEEDS_CONFIRMATION` 中),且输出内容与预期一致(平铺列表按名称排序并带 `/` 后缀;glob 只返回 `.py` 文件;树状展示体现层级缩进)。

- [ ] **Step 2: 记录验证结果**

在本文件末尾追加一个 `## 验证结果` 章节,写明:
- `pytest -v` 的最终通过数(应为 29/29)
- 手动验证三种场景的实际执行记录(简述每次调用的输入参数和输出摘要)
- 明确记录:`list_dir` 目前无自动化测试覆盖,属于按 [docs/开发规范.md](../../开发规范.md) 现阶段策略的已知测试债务,待策略放开后补齐

- [ ] **Step 3: 更新 spec 文档状态**

在 `docs/superpowers/specs/2026-07-04-list-dir-tool-design.md` 的"结果"章节,把状态从"设计已完成,已获用户批准"更新为"已实现(测试暂缓,见 docs/开发规范.md)"。

## 验证结果

- **`pytest -v`(通过 `.venv/bin/python -m pytest -v` 运行):29/29 全部通过**,含更新后的 `test_tools_schema_names_match_handlers` 断言。
- **手动验证:** 通过 `.venv/bin/python agent.py` 实际跑通一次交互会话(接入 `.env` 中配置的 DeepSeek Anthropic 兼容端点,模型 `deepseek-v4-pro`),依次发出三条指令,agent 均正确调用 `list_dir` 且**未触发确认提示**(符合 `list_dir` 不在 `NEEDS_CONFIRMATION` 的预期):
  1. `list_dir()`(无参数)—— 工具输出平铺列出项目根目录条目(`CLAUDE.md`、`README.md`、`agent.py`、`config.py`、`docs/`、`logs/`、`pytest.ini`、`requirements.txt`、`tests/`、`tools.py`),目录带 `/` 后缀,按名称排序。
  2. `list_dir(pattern="**/*.py")` —— 工具输出 6 个 `.py` 文件(`agent.py`、`config.py`、`tools.py`、`tests/test_agent_loop.py`、`tests/test_config.py`、`tests/test_tools.py`),不含非 `.py` 文件。
  3. `list_dir(path="tests", recursive=True)` —— 工具输出 `tests/` 下 3 个测试文件的平铺树状结果(该目录无嵌套子目录,故未体现缩进层级;另在 `docs/` 目录上人工追加验证过多层嵌套场景,`docs/superpowers/plans/`、`docs/superpowers/specs/` 等子目录正确以两空格缩进逐层展示)。
  - 以上三次工具调用的具体输入/输出均记录在 `logs/` 下对应时间戳的日志文件中,可供追溯。
- **已知测试债务:** `list_dir` 目前无自动化测试覆盖,属于按 [docs/开发规范.md](../../开发规范.md) 现阶段策略的已知空缺,待测试策略放开后按 spec 文档"测试计划"章节列出的清单补齐。
