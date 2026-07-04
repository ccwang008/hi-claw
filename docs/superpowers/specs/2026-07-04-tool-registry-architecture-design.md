# 需求/设计文档:工具系统工程化重构

## 背景

当前项目已经从单一 `run_bash` 持续扩展工具能力。设计讨论开始时主干认知中已有 6 个工具:`run_bash`、`read_file`、`write_file`、`edit`、`search`、`list_dir`;进入实施方案阶段时,工作区又出现了 `mkdir`、`append_file`、`delete_file` 三个文件操作工具。工具数量本身还不算失控,但工具相关职责已经集中在 `tools.py` 中:

- 工具实现函数
- Anthropic tool schema
- `TOOL_HANDLERS` 分发注册表
- `NEEDS_CONFIRMATION` 权限集合
- 若干工具内部辅助函数

这种结构适合最初 demo,但继续扩展时会出现几个问题:

- 新增工具需要同时改多个散点,容易漏注册或漏权限设置。
- `agent.py` 直接知道 schema、handler、确认集合等细节,边界不够清楚。
- 工具异常会穿透到外层对话循环,不利于模型根据失败结果自我修正。
- `tools.py` 会继续膨胀,不利于按领域维护工具。

用户明确希望为了后续扩展把目录结构拆得更工程化一些,并顺便调整“最简龙虾 Agent”这个定位说法。

## 目标

本次重构目标是建立一个清晰、可扩展的工具系统架构,同时保持项目仍然小而可读。

具体目标:

- 引入统一的 `ToolSpec`,把工具名、描述、schema、handler、确认策略放在同一个定义里。
- 引入 `tool_registry.py`,集中负责工具注册、schema 生成、工具查找、执行、确认判断和错误包装。
- 将工具实现按领域拆到 `tools/` 包中,避免单个 `tools.py` 继续膨胀。
- 让 `agent.py` 只负责对话循环和用户交互,不再直接操作 `TOOL_HANDLERS` / `NEEDS_CONFIRMATION`。
- 将项目文案从“最简龙虾 Agent”调整为“龙虾 Agent”,描述为可扩展的命令行 AI 编码 Agent。

## 非目标

本次不改变工具的外部行为和工具参数语义。

本次不新增工具、不引入插件热加载、不做复杂权限系统、不改变 Anthropic API 调用方式。

测试策略仍遵守 `docs/开发规范.md`:现阶段不要求为新功能补充全量新测试,但如果现有测试因结构调整失效,需要同步修正以保持测试套件可运行。

## 推荐架构

目录结构调整为:

```text
agent.py
config.py
tool_registry.py

tools/
  __init__.py
  bash.py
  files.py
  search.py
  list_dir.py

tests/
  test_agent_loop.py
  test_config.py
  test_tools.py
```

后续如果测试文件继续变大,再自然拆出 `test_tool_registry.py` 或 `test_tools_*.py`;本次不强制大规模测试重排。

## ToolSpec 设计

`ToolSpec` 是工具注册的唯一事实来源:

```python
@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: dict
    handler: Callable[..., str]
    requires_confirmation: bool = False
```

每个工具模块导出一个或多个 `ToolSpec`。例如 `tools/files.py` 导出 `READ_FILE_TOOL`、`WRITE_FILE_TOOL`、`EDIT_TOOL`。

`tools/__init__.py` 汇总所有工具:

```python
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
```

## ToolRegistry 设计

`tool_registry.py` 提供统一入口:

- `ToolRegistry(tool_specs)`
- `api_schemas() -> list[dict]`
- `requires_confirmation(name: str) -> bool`
- `dispatch(name: str, tool_input: dict, config: Config, logger=None) -> str`

`dispatch()` 负责:

- 校验工具名是否存在。
- 复制并规范化 tool input。
- 为 `run_bash` 注入 `config.bash_timeout` 默认值。
- 调用 handler。
- 捕获未知工具、参数错误、工具内部异常。
- 将失败包装成字符串返回给模型,而不是让整轮对话崩掉。
- 在 logger 中记录完整异常信息。

错误返回保持当前项目的文本风格,例如:

```text
(工具调用失败:未知工具 foo)
(工具调用失败:参数错误 read_file: ...)
(工具调用失败:search: ...)
```

## agent.py 边界

`agent.py` 继续保留:

- `default_confirm()`
- `setup_logger()`
- `run_turn()`
- `main()`

但工具相关依赖改为 registry:

- API 调用时传 `tools=registry.api_schemas()`
- tool_use block 交给 registry 执行
- 是否确认由 `registry.requires_confirmation(name)` 判断
- `agent.py` 不再导入 `TOOL_HANDLERS`、`TOOLS`、`NEEDS_CONFIRMATION`

确认流程仍留在 `agent.py`,因为它属于 CLI 用户交互,不是工具实现本身。

## 文案更新

项目主标题建议从:

```text
最简龙虾 Agent
```

调整为:

```text
龙虾 Agent
```

项目描述建议从:

```text
一个最小可运行的命令行 AI 编码 Agent。
```

调整为:

```text
一个可扩展的命令行 AI 编码 Agent,提供对话循环、工具调用、确认机制和日志记录等基础能力。
```

这样保留“龙虾 Agent”的项目识别,同时不再把项目定位限制在最简 demo。

## 迁移策略

推荐按低风险顺序迁移:

1. 新增 `tool_registry.py`,定义 `ToolSpec` 和 `ToolRegistry`。
2. 新建 `tools/` 包,先迁移工具实现和 schema,保持外部工具名不变。
3. 修改 `agent.py`,通过 registry 获取 schema 和执行工具。
4. 保留兼容导出或同步修正测试,让现有测试可以继续验证工具名单和确认策略。
5. 更新 README、CLAUDE.md 和相关文档中的“最简龙虾 Agent”说法。
6. 补充本次开发日志。

## 验收标准

- 现有工具名、参数和基本行为保持不变,包括当前工作区已有的 `run_bash`、`read_file`、`write_file`、`mkdir`、`append_file`、`delete_file`、`edit`、`search`、`list_dir`。
- `agent.py` 不再直接依赖 `TOOLS`、`TOOL_HANDLERS`、`NEEDS_CONFIRMATION`。
- 新增工具时只需要新增/修改对应工具模块的 `ToolSpec` 汇总入口。
- 工具执行异常不会导致整轮对话直接崩掉,而是以 tool_result 文本返回给模型。
- README 和主要入口文档不再使用“最简龙虾 Agent”作为项目定位。

## 后续扩展

完成本次架构后,后续可以更自然地继续做:

- workspace root 安全边界
- 工具启用/禁用配置
- 更细粒度权限策略
- 工具输出长度限制和结构化摘要
- 按工具模块拆分测试文件
