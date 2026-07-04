# my-claw

龙虾 Agent 🦞 —— 项目说明见 [README.md](README.md)。

## 文档规范(硬性要求)

所有通过 superpowers 技能(`brainstorming`、`writing-plans` 等)产生的需求/设计文档、实施方案,一律保存在 `docs/superpowers/` 下并分类归档,规则见 [docs/superpowers/README.md](docs/superpowers/README.md):

- `docs/superpowers/specs/` —— 需求/设计文档
- `docs/superpowers/plans/` —— 实施方案

即使处于 Plan Mode、因文件写入限制只能先把设计写进 plan 文件,approve 之后也必须把最终设计/计划补一份到上面对应目录,不能只留在 plan 文件里。

所有开发过程与提交都要按**四层追溯体系**记入 `docs/开发日志/` 并分类归档。该体系**工具无关**(不绑定任何 IDE/Agent 的 hook 或私有会话格式),完整规则见 [docs/开发规范.md](docs/开发规范.md) 的「开发过程追溯(四层)」章节与 [docs/开发日志/README.md](docs/开发日志/README.md):

- `docs/开发日志/transcripts/` —— **L1 原始对话**,每个会话一份完整可读记录,`YYYY-MM-DD-<主题或slug>.md`(导出方式交给当前工具,不绑定)
- `docs/开发日志/vibecoding日志/` —— **L2 精炼开发日志**,一个任务一条,`YYYY-MM-DD-<主题>.md`
- `docs/开发日志/决策记录/` —— **L3 ADR**,重要架构决策触发式归档,`NNNN-<title>.md`
- `docs/开发日志/提交日志/` —— **L4 提交记录**,一次提交一个文件,`YYYY-MM-DD-<commit短hash>-<主题>.md`

每个会话结束要在 transcripts/ 留完整对话记录;每完成一段开发补 vibecoding 日志;有重要架构决策时补 ADR;每次向 Git 提交补提交日志。四者以 commit 为锚点交叉引用。

## 开发规范

日常开发流程/规范(如测试策略等)见 [docs/开发规范.md](docs/开发规范.md)。
