# 2026-07-04 新增 System Prompt 设计文档

- **Commit**: `1a368d1` — docs: 新增 system prompt 设计文档
- **远程仓库**: https://github.com/ccwang008/hi-claw.git
- **分支**: `main`

## 改动清单

- 新增 `docs/superpowers/specs/2026-07-04-system-prompt-design.md`
  ——设计 my-claw 的 System Prompt,采用可扩展的上下文组装层
  (静态基座 + 自动工具清单 + 动态环境块),为后续继续追加上下文
  来源(项目说明、记忆等)预留结构。

## 备注

- 对应 vibecoding 日志:[2026-07-04-system-prompt设计](../vibecoding日志/2026-07-04-system-prompt设计.md)
- 本次提交只包含 spec 文档;实际代码实现(`context.py`/`system_prompt.md`/
  `config.py`/`agent.py` 改动)将在用户 review spec 并批准实施方案后另行提交。
