# 最简龙虾 Agent:补齐工具能力 + 工程化基础

## Context

当前 `my-claw/agent.py` 是一个约 100 行的单文件 CLI agent,只有一个 `run_bash` 工具,靠它硬凑读文件/写文件/搜索等所有操作。通过 brainstorming 讨论确认了两类必要缺口:

1. **工具能力太单一** —— 除了 bash,没有结构化的文件读写、编辑、代码搜索工具,agent 干活效率低且不精确。
2. **工程化基础缺失** —— 没有日志落盘(出问题难排查)、没有自动化测试(改代码没有回归保护)、配置项散落在各处环境变量读取里。

目标:在保持"最小可运行 agentic loop"这个核心理念的前提下,把这两块补齐。因为新增内容会让代码量远超原来的 100 行,经确认改为拆分成多个模块(不再是单文件项目),README 同步更新说明。

## 设计

### 文件组织

```
my-claw/
  agent.py              # CLI 入口 + 主循环(run_turn 函数,可被测试注入 mock）
  config.py             # Config dataclass + load_config()
  tools.py              # 5 个工具的 schema(TOOLS）+ 实现 + 分发逻辑
  requirements.txt      # 新增 pytest(dev 依赖）
  tests/
    test_tools.py       # 工具函数单元测试
    test_config.py      # 配置加载测试
    test_agent_loop.py  # mock Anthropic client,测主循环调度逻辑
  README.md             # 多模块说明 + 新工具/配置/日志/测试的使用说明
  logs/                 # 运行时生成,按会话时间戳落盘,勿提交(已加入 .gitignore）
```

### 工具设计(`tools.py`)

统一结构:
- `TOOLS`:喂给 Anthropic API 的 schema 列表(在现有 `run_bash` schema 基础上新增 4 个）
- `TOOL_HANDLERS: dict[str, Callable]`:name → 处理函数
- `NEEDS_CONFIRMATION = {"run_bash", "write_file", "edit"}`:需要 y/N 确认的工具集合(`read_file` / `search` 是纯读操作,直接执行不打断交互)

各工具行为:

- **run_bash**(沿用现有实现,原样迁移到 `tools.py`)
- **read_file(path, offset=None, limit=None)**:按行读取文件,`cat -n` 风格输出行号+内容;默认最多读 2000 行,超出则裁剪并在末尾提示"还有 N 行未显示,可用 offset/limit 分页"。文件不存在 / 是目录 / 编码错误等情况捕获异常,返回描述性错误字符串(不 raise),与 `run_bash` 现有的"输出即结果"风格保持一致。
- **write_file(path, content)**:整体写入,若文件已存在则覆盖;自动 `os.makedirs(parent, exist_ok=True)` 创建父目录。成功返回类似"已写入 path(N 字节)"的消息;权限错误等同样捕获返回描述性错误。
- **edit(path, old_string, new_string, replace_all=False)**:读取文件全文,统计 `old_string` 出现次数——0 次报错"未找到匹配文本";>1 次且 `replace_all=False` 报错"找到 N 处匹配,请提供更多上下文使其唯一,或设置 replace_all=true";否则执行替换并写回文件。
- **search(pattern, path=".", file_glob=None, max_results=200)**:纯 Python 实现,不依赖外部 grep/rg 二进制。用 `os.walk` 遍历目录树,跳过 `.git`、`.venv`、`__pycache__`、`node_modules` 等目录;若指定 `file_glob`(如 `"*.py"`)用 `fnmatch` 过滤文件名;逐行用 `re.search(pattern, line)` 匹配,命中格式为 `path:lineno: line内容`;结果数超过 `max_results` 时截断并提示。读取时遇到二进制/解码失败的文件直接跳过。

### 主循环重构(`agent.py`)

把现有 `main()` 里的内层 while 循环抽成独立函数 `run_turn(client, messages, config, confirm_fn=default_confirm, logger=None)`,便于测试注入 mock client 和假的 confirm 函数。工具分发按 `TOOL_HANDLERS[block.name]` 查找并调用,若 `block.name in NEEDS_CONFIRMATION` 才走确认流程,否则直接执行。每一步(模型调用、工具请求、确认结果、工具输出)都通过 `logger` 记录。

### 配置(`config.py`)

`Config` dataclass + `load_config()`,从环境变量读取 `model`/`base_url`/`max_tokens`/`bash_timeout`/`log_dir`,提供当前代码里已有的默认值(`claude-haiku-4-5` / 2048 / 60 / `"logs"`)。

### 日志

标准库 `logging`,不引入新依赖。`main()` 启动时在 `logs/` 下按启动时间生成日志文件,记录:会话开始、用户输入、助手文本回复、工具调用请求、确认结果、工具执行结果、异常堆栈。

### 测试(`tests/`)

- `test_tools.py`:用 `tmp_path` fixture 覆盖 read_file/write_file/edit/search 的正常路径 + 边界情况,`run_bash` 测简单命令输出 + 超时行为。
- `test_agent_loop.py`:用 `unittest.mock.Mock` 构造假的 Anthropic client,配合假 `confirm_fn`,验证工具正确分发、确认通过/拒绝两条分支、消息历史正确累积、`stop_reason` 判断退出循环。

## 验证方式

1. `pip install -r requirements.txt` 后运行 `pytest -v`,确认所有测试通过。
2. 手动运行 `python agent.py`,验证 read_file / write_file(确认后写入) / edit(确认后替换) / search(命中格式正确) / 拒绝确认(文件未创建)五条路径,并检查 `logs/` 目录下生成的日志内容。

## 结果

已实现并通过验证,详见 [实施方案](../plans/2026-07-04-file-tools-and-engineering.md)。
