# 需求/设计文档:System Prompt(上下文组装层)

- 日期:2026-07-04
- 类型:brainstorming 产出的需求/设计文档

## 背景

my-claw 目前完全没有 system prompt——`agent.py` 的 `client.messages.create(...)` 调用没有传 `system` 参数,模型不知道自己的身份、可用工具的使用方式、工作准则和安全边界。这一点在上一轮"修复会话污染等健壮性问题"的开发日志里已被标记为待增强项。

与用户梳理当前缺失能力后,归纳出三档:System prompt / 流式输出 / 上下文管理属于"影响像不像个 Agent 的核心缺失"一档。用户选择优先做 **System Prompt**。

设计过程中用户提出关键顾虑:不想简单加一个静态 `system_prompt.md` 文件就完事,因为后期想让"上下文自己拼接出来"(工具清单、项目级说明、环境信息等来源陆续加入)。因此设计从"单一静态文件"调整为"分层可扩展的组装层",为后续扩展预留结构,但**第一版只落地两段来源**,不做过度设计。

## 需求范围

用户明确选择的范围(多选确认后收敛):

1. **存放方式**:独立 `system_prompt.md` 文件 + env 变量可覆盖(而非硬编码在 Python 常量里)。
2. **动态环境注入**:system prompt 需要动态拼接当前工作目录(cwd)、操作系统、日期。
3. **组装层范围**:第一版做到"静态基座 + 自动工具清单 + 环境块"三段式,架构上是一个可继续追加来源的有序列表,而不是写死的字符串拼接。

明确排除(本次不做,留作后续追加来源的方向):
- prompt caching
- 项目级说明文件注入(类似 CLAUDE.md 的项目约定自动读取)

## 设计

### 整体结构:组装层 + 有序 section 列表

新增 `context.py` 模块,核心是：

```python
def build_system_prompt(config: Config) -> str:
    return "\n\n".join(section(config) for section in SECTIONS)

SECTIONS = [_base_section, _tools_section, _env_section]
```

`SECTIONS` 是一个有序的"来源"列表，每个来源是一个 `(config) -> str` 的函数。以后要加新来源（项目说明文件、git 状态、记忆等），只需要新增一个函数并追加到 `SECTIONS`，不需要改动其他 section 或主循环。这是这次设计要解决用户顾虑（"后期想让上下文自己拼接"）的关键点。

### 三个 section

**1. `_base_section`（静态基座）**

- 从 `config.system_prompt_file` 指定的路径读取 `.md` 文件内容并原样返回。
- 默认文件：仓库根目录新增的 `system_prompt.md`。
- 读取失败（文件不存在等）时，fallback 到一段硬编码的最小默认串，并打印一次 warning（不抛异常导致启动失败）。
- 内容覆盖：
  - 身份：你是"龙虾 Agent 🦞"，一个跑在用户终端里的命令行编码助手。
  - 工作准则：先理解再动手；改动尽量小而精确；改完用工具自我验证（如跑测试、读回改动确认）；拿不准先问用户。
  - 工具**用法指引**（非清单，清单由下一段自动生成）：例如"改文件前先用 read_file 看清楚现状"、"edit 的 old_string 必须唯一，不唯一就补充上下文或用 replace_all"、"搜代码优先用 search/list_dir，而不是 run_bash 里拼 grep/find"。
  - 安全边界：run_bash / write_file / edit 会弹确认，涉及破坏性或不可逆操作要先说明意图；只在用户可控的目录/环境里操作。

**2. `_tools_section`（自动工具清单）**

- 遍历 `tools.py` 的 `TOOLS` 列表，生成一份紧凑名册：每行 `- {name}: {description 首句}`。
- 定位：这不是重复注入完整 schema——Anthropic API 的 `tools=TOOLS` 参数已经把完整 schema（参数、类型、描述）注入模型上下文，重复写等于浪费 token。这一段只提供一份随工具增删自动同步的"名字对照表"，让基座 `.md` 里手写的工作准则能稳定引用工具名，不会因为改工具名/加工具而导致提示词脱节。

**3. `_env_section`（动态环境块）**

- 生成一段 `<env>` 文本块，包含：
  - 当前工作目录：`os.getcwd()`
  - 操作系统：`platform.platform()`
  - 日期：`date.today()`（`datetime.date`）
- 每次启动时动态生成，不缓存。

### 涉及的配置改动

`config.py`：
- `Config` 新增字段 `system_prompt_file: str`。
- `load_config()` 读取 env `SYSTEM_PROMPT_FILE`，默认值 `"system_prompt.md"`。

### 涉及的主循环改动

`agent.py`：
- `main()` 中，`config = load_config()` 之后调用 `system_prompt = build_system_prompt(config)`。
- `run_turn` 增加接收 system prompt 的方式（作为参数传入，或挂在 config 上，实现阶段定），在 `client.messages.create(...)` 调用中加上 `system=...`。这是本次唯一改动到主循环调用点的地方，不改变 `run_turn` 其他逻辑（工具分发、迭代上限、异常兜底均不变）。

### 涉及文件

- 新增 `system_prompt.md`（仓库根）
- 新增 `context.py`
- 修改 `config.py`（加字段 + 加载逻辑）
- 修改 `agent.py`（组装并传入 `system` 参数）
- 修改 `README.md`（补充 `SYSTEM_PROMPT_FILE` 环境变量说明）

## 测试计划

> 按 [docs/开发规范.md](../../开发规范.md) 现阶段规定，本次实现暂不要求编写新测试用例。**例外**：若已有测试（如 `tests/test_agent_loop.py` 中 mock `client.messages.create` 并断言调用参数的用例）因新增 `system=` 参数而断言过时，需要同步修正，保证现有测试套件能跑通——这不算"新写测试"，只是维持现状不被破坏。

后续统一补齐测试时的覆盖清单（保留供参考）：
- `build_system_prompt` 三段都被正确拼接，且顺序固定
- 基座文件缺失时 fallback 到默认串，且不抛异常
- `SYSTEM_PROMPT_FILE` 环境变量可覆盖默认文件路径
- 工具清单 section 随 `TOOLS` 变化自动同步（增删工具后名册跟着变）
- 环境块包含 cwd/OS/日期且格式正确

## 验证方式

- `pytest` 全量跑通，确认不破坏现有测试。
- 手动跑 `python agent.py`，通过日志或临时打印确认最终传给 API 的 `system` 内容包含三段（基座/工具名册/环境信息），且 cwd、日期与实际一致。
- 手动验证 `SYSTEM_PROMPT_FILE` 指向自定义文件时能正确覆盖默认基座内容。

## 结果

（待实施，实施方案将写入 `docs/superpowers/plans/`）
