# 开发日志

记录 my-claw 🦞 的开发过程,采用**四层追溯体系**(完整定义见 [docs/开发规范.md](../开发规范.md) 的「开发过程追溯(四层)」章节)。本目录按四层分类归档:

- `transcripts/` —— **L1 原始对话**。每个会话一份完整、可读的对话记录(问答 + 推理过程 + 工具调用与结果),文件名格式 `YYYY-MM-DD-<主题或slug>.md`。导出方式不绑定工具,详见该目录 README。
- `vibecoding日志/` —— **L2 精炼开发日志**。每一次开发的提炼归纳,一个任务一条,文件名格式 `YYYY-MM-DD-<主题>.md`。
- `决策记录/` —— **L3 ADR**。重要架构/技术选择单独归档,文件名格式 `NNNN-<title>.md`(四位序号递增)。
- `提交日志/` —— **L4 提交记录**。每一次 Git 提交一个文件,文件名格式 `YYYY-MM-DD-<commit短hash>-<主题>.md`。

## 约定

- 日期用当天实际日期,同一天多次开发/提交用主题区分。
- 各层侧重不同:transcript 是完整留档;vibecoding 日志侧重「做了什么、为什么这么做、遇到的问题」;ADR 侧重「背景/决策/理由/后果」;提交日志侧重「本次提交的改动清单与 commit 信息」。
- **交叉引用(以 commit 为锚点)**:提交日志里注明 commit hash、关联的 vibecoding 日志、transcript、以及涉及的 ADR;vibecoding 日志注明对应提交日志;ADR 注明关联的 commit / transcript / devlog。L1 完整 transcript 随对应代码提交一同入库。
