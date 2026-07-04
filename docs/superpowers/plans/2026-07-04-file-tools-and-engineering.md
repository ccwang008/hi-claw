# 实施方案:补齐工具能力 + 工程化基础

对应设计文档:[../specs/2026-07-04-file-tools-and-engineering-design.md](../specs/2026-07-04-file-tools-and-engineering-design.md)

状态:**已完成**(2026-07-04)

## 任务拆分与结果

全程采用 TDD(先写失败测试,确认 RED,再写最小实现,确认 GREEN)。

1. **config.py** —— `Config` dataclass + `load_config()`。测试:`tests/test_config.py`(默认值 + 环境变量覆盖)。
2. **tools.py:run_bash + read_file** —— run_bash 原样迁移,新增 read_file(cat -n 风格、offset/limit、缺失文件/目录/二进制错误处理)。测试:`tests/test_tools.py`。
3. **tools.py:write_file** —— 整体写入/覆盖、自动建父目录。
4. **tools.py:edit** —— 精确字符串替换,唯一性校验 + replace_all。
5. **tools.py:search** —— 纯 Python 实现,目录跳过规则、file_glob 过滤、max_results 截断、二进制文件跳过。
6. **tools.py:TOOLS/TOOL_HANDLERS/NEEDS_CONFIRMATION** —— 工具注册表,测试校验 schema 名称与 handler 一致、确认集合是 schema 名称的子集。
7. **agent.py:run_turn()** —— 主循环重构为可注入 mock client / confirm_fn 的函数。测试:`tests/test_agent_loop.py`,覆盖工具分发、确认通过/拒绝、消息累积、stop_reason 退出。
8. **agent.py:日志集成** —— 与任务 7 一并完成,`logs/` 按会话时间戳落盘。
9. **requirements.txt / .gitignore / README.md** —— 新增 pytest 依赖、logs 和 .pytest_cache 忽略规则、多模块项目结构说明。
10. **验证** —— pytest 全绿(29/29);用真实 API 手动跑通 read_file / write_file(确认后写入)/ edit(确认后替换)/ search(命中格式正确)/ 拒绝确认(文件未创建)五条路径,核对日志内容。

## 关键文件

- `agent.py`、`config.py`、`tools.py`
- `tests/test_config.py`、`tests/test_tools.py`、`tests/test_agent_loop.py`
- `requirements.txt`、`.gitignore`、`README.md`

## 验证记录

```
$ pytest -v
...
============================== 29 passed in 2.48s ===============================
```

手动验证覆盖:
- `read_file` 读取 README.md 指定行范围,行号格式正确
- `write_file` 触发 y/N 确认,确认后文件内容正确写入
- `edit` 触发确认,确认后替换生效
- `search` 命中格式 `path:lineno:content` 正确,`.venv`/`__pycache__` 未被搜到
- 拒绝确认(输入 n)时目标文件未被创建
- `logs/` 目录下日志文件包含以上所有关键事件
