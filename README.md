# 龙虾 Agent 🦞 (my-claw)

一个可扩展的命令行 AI 编码 Agent。它在终端里跑一个多轮对话循环,Claude 可以调用工具在你的机器上真正执行操作,形成「对话 + 干活」的 agentic loop。

## 项目结构

```
my-claw/
  agent.py          # CLI 入口 + 主循环(run_turn 函数)
  config.py         # 配置:Config dataclass + load_config()
  tool_registry.py  # ToolSpec + ToolRegistry,统一管理工具 schema/确认/分发
  tools/            # 按领域拆分的工具实现与 ToolSpec
    bash.py
    files.py
    search.py
    list_dir.py
  requirements.txt
  tests/
    test_tools.py       # 工具函数单元测试
    test_config.py       # 配置加载测试
    test_agent_loop.py  # 主循环测试(mock Anthropic client)
  logs/             # 运行时生成,每次会话一个日志文件(已加入 .gitignore)
```

## 安装

```bash
pip install -r requirements.txt
```

## 设置 API Key

复制 `.env.example` 为 `.env`,填入你的 key:

```bash
cp .env.example .env
```

也可以直接导出环境变量:

```bash
export ANTHROPIC_API_KEY=你的key
```

其他可选环境变量(都有默认值,一般不需要改):

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `MODEL_ID` | `claude-haiku-4-5` | 使用的模型 |
| `ANTHROPIC_BASE_URL` | (无) | 自定义 API 网关地址 |
| `MAX_TOKENS` | `2048` | 单次回复最大 token 数 |
| `BASH_TIMEOUT` | `60` | `run_bash` 工具的超时秒数 |
| `LOG_DIR` | `logs` | 日志文件目录 |
| `MAX_ITERATIONS` | `25` | 单轮对话内最多连续调用工具的轮数,防止死循环 |

## 运行

```bash
python agent.py
```

启动后直接在 `你>` 后面输入即可,例如「现在这个目录下有哪些文件?」。输入 `exit` 或 `quit`(或按 Ctrl-C)退出。

## 工具

Agent 可以调用以下工具:

- **run_bash**:执行 shell 命令
- **read_file**:按行号读取文件内容,支持 `offset`/`limit` 分页
- **write_file**:整体写入/覆盖文件,自动创建父目录
- **mkdir**:创建目录,支持递归创建父目录
- **append_file**:在文件末尾追加内容,文件不存在时自动创建
- **delete_file**:删除文件或目录,删除目录时需要 `recursive=true`
- **edit**:对文件做精确字符串替换(`old_string` 必须唯一,否则需设置 `replace_all`)
- **search**:在目录树里按正则搜索文件内容,纯 Python 实现,支持 `file_glob` 过滤,自动跳过 `.git`/`.venv`/`__pycache__`/`node_modules`
- **list_dir**:列出目录内容,支持平铺列表、glob 匹配和树状结构展示

其中 `run_bash`、`write_file`、`append_file`、`delete_file`、`edit` 会修改文件系统或执行命令,每次调用前都会打印出操作详情并等你输入 `y` 确认(默认 `N`,即回车就跳过)。其他工具不需要确认。

## 日志

每次启动会在 `logs/` 下按时间戳生成一个日志文件(如 `logs/20260704-103000.log`),记录用户输入、助手回复、工具调用请求、确认结果、工具输出、异常堆栈,方便事后排查。

## 测试

```bash
pytest -v
```

## ⚠️ 安全提示

每次模型想执行 `run_bash`/`write_file`/`append_file`/`delete_file`/`edit` 这类会改动系统的操作,都会先打印详情并等你确认,另有超时保护。即便如此,也请在你可控的目录/环境中使用,不要在生产或敏感机器上随意运行。
