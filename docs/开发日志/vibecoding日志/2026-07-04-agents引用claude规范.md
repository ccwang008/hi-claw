# 2026-07-04 AGENTS 引用 CLAUDE 规范

- **主题**:让 `AGENTS.md` 引用 `CLAUDE.md`,避免两份 Agent 规范重复维护
- **对应提交**:暂无

## 目标

根据“agent.md 应该引用 claude.md”的要求,将面向 Codex/Agents 的入口文件调整为引用 `CLAUDE.md`,让项目通用 Agent 规范保持单一来源。

## 过程

1. 检查仓库中实际存在的文件:发现有 `AGENTS.md` 和 `CLAUDE.md`,没有小写的 `agent.md` 或 `claude.md`。
2. 对比两个文件内容:确认 `AGENTS.md` 与 `CLAUDE.md` 当前内容完全重复。
3. 将 `AGENTS.md` 改为轻量入口,保留项目标题和 README 引用,并明确项目通用 Agent 规则以 `CLAUDE.md` 为准。

## 遇到的问题 / 决策

- **文件名大小写不一致**:用户说的是 `agent.md` / `claude.md`,仓库实际文件为 `AGENTS.md` / `CLAUDE.md`;按仓库现状修改 `AGENTS.md`。
- **避免双份规范漂移**:不再复制 `CLAUDE.md` 的完整内容,只在 `AGENTS.md` 中建立引用。
