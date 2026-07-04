# 需求/设计文档:新增 list_dir 工具

- 日期:2026-07-04
- 类型:brainstorming 产出的需求/设计文档

## 背景

my-claw 目前是一个三模块(agent.py / config.py / tools.py)的极简 CLI Agent,已有 5 个工具:`run_bash`、`read_file`、`write_file`、`edit`、`search`。这是继"补齐工具能力 + 工程化基础"之后的第二轮迭代。

与用户逐项梳理当前缺失的能力后,归纳出几个方向:对话记忆/持久化、上下文管理、System Prompt/人设配置、工具集扩展、确认/权限机制、流式输出、打包/CI。用户选择优先深入**工具集扩展**,并进一步聚焦到**目录浏览类工具**——现在 agent 只能靠 `run_bash` 拼命令或用 `search` 硬找文件,没有原生的列目录/glob 匹配/树状结构展示能力,建立项目全貌认知效率较低。

## 需求范围

用户明确要求目录浏览工具覆盖以下能力(多选确认):
- 基础列目录(类似 `ls`)
- glob 模式匹配(如 `**/*.py`)
- 树状结构展示(类似 `tree`)
- 自动跳过 `.gitignore`/常见忽略目录,避免噪音

工具粒度上,用户明确选择**一个统一工具**(而非拆成 `list_dir` + `tree` 两个工具),以保持与现有 5 个工具一致的"少而精"风格。

## 设计

在 `tools.py` 中新增 `list_dir` 工具,复用已有的 `SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", "node_modules"}` 常量,不引入新的外部依赖。

### 签名

```python
def list_dir(
    path: str = ".",
    pattern: str | None = None,
    recursive: bool = False,
    max_depth: int | None = None,
    show_hidden: bool = False,
    max_results: int = 200,
) -> str
```

### 三种模式(靠参数组合区分,不新增额外工具)

1. **平铺列目录(默认)** —— 不传 `pattern`、`recursive=False` 时,列出 `path` 下的直接条目,目录名后加 `/` 区分类型,按名称排序。
2. **glob 模式匹配** —— 传 `pattern`(如 `"*.py"` 或 `"**/*.py"`)时,用 `pathlib.Path(path).glob(pattern)` 递归匹配(`**` 原生支持跨目录),结果按路径排序。
3. **树状结构** —— `recursive=True` 且不传 `pattern` 时,输出多层缩进的树状文本,深度默认不限,可用 `max_depth` 限制,避免大项目输出爆炸。

### 统一规则

- 三种模式都自动跳过 `SKIP_DIRS` 中的目录
- `show_hidden=False`(默认)时过滤掉以 `.` 开头的文件/目录
- 结果超过 `max_results`(默认 200)时截断,并追加提示:`"(结果过多,已截断,建议缩小范围)"`
- 错误处理沿用现有风格:路径不存在/不是目录时返回 `"(xxx 失败:...)"` 字符串,不抛异常,不新增自定义异常类型

### 接入方式

- 加入 `TOOLS` schema 列表(参照 `search` 工具 schema 的写法和中文描述风格)
- 加入 `TOOL_HANDLERS` 注册表
- **不加入 `NEEDS_CONFIRMATION`**(纯只读操作,和 `read_file`/`search` 一致,无需用户确认)

## 涉及文件

- `tools.py` —— 新增 `list_dir` 函数实现、`TOOLS` schema 条目、`TOOL_HANDLERS` 注册
- `tests/test_tools.py` —— 新增 `list_dir` 的测试用例

## 测试计划

> **状态更新(2026-07-04):** 按 [docs/开发规范.md](../../开发规范.md) 现阶段规定,本次实现暂不编写测试用例,以下测试点作为后续补齐测试时的覆盖清单保留。

沿用 `test_tools.py` 现有的 `tmp_path` 风格,覆盖:
- 平铺列目录(混合文件和子目录,验证排序和 `/` 后缀)
- glob 匹配(含 `**` 递归跨目录匹配)
- 树状输出(多层嵌套)
- `max_depth` 截断树状输出
- 隐藏文件默认过滤 + `show_hidden=True` 时显示
- 自动跳过 `SKIP_DIRS` 中的目录
- 路径不存在 / 传入非目录路径的错误提示
- 结果数量超过 `max_results` 时的截断提示

## 验证方式

- `pytest` 全量跑通(包含新增用例),确认不破坏现有 29 个测试
- 手动在项目根目录跑一次 agent,让它调用 `list_dir` 做平铺列目录、glob 匹配、树状展示三种场景,确认输出符合预期且无需确认提示(read-only 工具)

## 结果

已实现(测试暂缓,见 [docs/开发规范.md](../../开发规范.md))。实施方案与验证记录见 `docs/superpowers/plans/2026-07-04-list-dir-tool.md`。
