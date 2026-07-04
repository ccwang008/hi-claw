# my-claw

龙虾 Agent 🦞 —— 项目说明见 [README.md](README.md)。

## 文档规范(硬性要求)

所有通过 superpowers 技能(`brainstorming`、`writing-plans` 等)产生的需求/设计文档、实施方案,一律保存在 `docs/superpowers/` 下并分类归档,规则见 [docs/superpowers/README.md](docs/superpowers/README.md):

- `docs/superpowers/specs/` —— 需求/设计文档
- `docs/superpowers/plans/` —— 实施方案

即使处于 Plan Mode、因文件写入限制只能先把设计写进 plan 文件,approve 之后也必须把最终设计/计划补一份到上面对应目录,不能只留在 plan 文件里。

所有开发过程与提交都要记入 `docs/开发日志/` 并分类归档,规则见 [docs/开发日志/README.md](docs/开发日志/README.md):

- `docs/开发日志/vibecoding日志/` —— 每一次开发的对话记录,一次开发一个文件,`YYYY-MM-DD-<主题>.md`
- `docs/开发日志/提交日志/` —— 每一次 GitHub 提交的记录,一次提交一个文件,`YYYY-MM-DD-<commit短hash>-<主题>.md`

每完成一段开发都要补 vibecoding 日志,每次向 GitHub 提交都要补提交日志,两者交叉引用。

## 开发规范

日常开发流程/规范(如测试策略等)见 [docs/开发规范.md](docs/开发规范.md)。
