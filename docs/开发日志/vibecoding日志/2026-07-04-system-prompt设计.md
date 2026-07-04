# 2026-07-04 System Prompt 设计(brainstorming)

- **主题**:通过 superpowers:brainstorming 技能梳理 my-claw 缺失功能,选定并设计 System Prompt
- **对应提交**:[2026-07-04-1a368d1-新增system-prompt设计文档](../提交日志/2026-07-04-1a368d1-新增system-prompt设计文档.md)

## 目标

用户要求「一步一步来」梳理项目当前还缺哪些必要功能,每步都要等确认后再进入实施,不要一次性说完。

## 过程

1. **梳理现状**:读 `README.md`/`agent.py`/`tools.py`/`config.py` 及上一轮开发日志,确认当前已有
   6 个工具、危险操作确认、日志、env 配置、迭代上限+异常兜底(刚修完健壮性问题)。
2. **列出缺失项,分三档**:
   - 🔴 核心缺失:无 system prompt、无流式输出、上下文无限增长无管理
   - 🟠 好用度:会话不持久、无斜杠命令、看不到 token 用量
   - 🟢 锦上添花:run_bash 无额外拦截、无 prompt caching、无法中途打断
3. 用户选择第一步做 **System Prompt**。
4. **设计迭代**(brainstorming 逐问逐答):
   - 存放方式:独立 `.md` 文件 + env 可覆盖(而非硬编码常量)
   - 是否动态注入环境信息(cwd/OS/日期):是
   - **关键转折**:最初设计是"读一个静态 system_prompt.md 拼上环境块"的两段式。用户提出
     顾虑——"直接加 system_prompt.md 这样好吗?后期其实想让上下文自己拼接出来"。
     据此把设计从"写死的两段拼接"改造成**分层可扩展的组装层**:`SECTIONS` 是一个
     `(config) -> str` 函数的有序列表,`build_system_prompt` 遍历拼接;以后加新来源
     (项目说明文件、git 状态、记忆等)只需要追加一个 section 函数,不改动其他部分。
   - 组装层第一版范围:用户选择"再加自动工具清单 section"(即基座+工具清单+环境块
     三段),而非只做两段或再加项目说明文件 section。
   - 讨论工具清单 section 的定位时说明:Anthropic API 的 `tools=TOOLS` 参数已经把完整
     schema 注入模型上下文,工具清单 section **不重复**塞 schema,只提供一份紧凑名册
     (name + 一句话描述),供基座 `.md` 手写的工作准则稳定引用工具名,增删工具时自动同步。
5. 用户认可最终设计,写入 spec 文档并提交。

## 关键决策

- **组装层而非单文件**:直接原因是用户提出的"后期想自动拼接"的需求。选择"有序 section
  函数列表"而不是更复杂的插件/优先级系统,是遵循 YAGNI——现在只需要顺序拼接,复杂的
  优先级/条件启用机制留到真正需要时再加。
- **工具清单不重复 schema**:避免和 API 自动注入的内容重复浪费 token,只解决"基座提示词
  引用工具名会不会随工具增删脱节"这一个具体问题。

## 范围之外(本次不做)

- prompt caching
- 项目级说明文件自动注入(类似 CLAUDE.md 的项目约定读取)——留作组装层后续可追加的方向

## 结果

Spec 已写入 `docs/superpowers/specs/2026-07-04-system-prompt-design.md` 并提交
(`1a368d1`)。下一步:用户 review 该 spec,确认无误后进入 `writing-plans` 生成实施方案。
