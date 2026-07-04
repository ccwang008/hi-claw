#!/usr/bin/env python3
"""最简龙虾 Agent 🦞 —— 一个能对话、能执行 bash/文件操作的最小 agentic loop。"""

import logging
import os
import sys
from datetime import datetime

from anthropic import Anthropic
from dotenv import load_dotenv

from config import Config, load_config
from tools import NEEDS_CONFIRMATION, TOOL_HANDLERS, TOOLS

load_dotenv()


def default_confirm(tool_name: str, tool_input: dict) -> bool:
    print(f"\n[待执行] {tool_name}({tool_input})")
    try:
        confirm = input("执行这个操作吗? [y/N] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        confirm = "n"
    if confirm != "y":
        print("已跳过。")
    return confirm == "y"


def setup_logger(log_dir: str) -> logging.Logger:
    os.makedirs(log_dir, exist_ok=True)
    filename = os.path.join(log_dir, datetime.now().strftime("%Y%m%d-%H%M%S.log"))
    logger = logging.getLogger("lobster-agent")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    handler = logging.FileHandler(filename, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    return logger


def _dispatch_tool(block, config: Config, confirm_fn, logger) -> str:
    name = block.name
    tool_input = dict(block.input)
    if name == "run_bash":
        tool_input.setdefault("timeout", config.bash_timeout)

    if logger:
        logger.info("工具请求: %s(%r)", name, tool_input)

    if name in NEEDS_CONFIRMATION:
        confirmed = confirm_fn(name, tool_input)
        if logger:
            logger.info("确认结果: %s -> %s", name, "同意" if confirmed else "拒绝")
        if not confirmed:
            return "(用户拒绝执行该操作)"

    handler = TOOL_HANDLERS[name]
    output = handler(**tool_input)
    if logger:
        logger.info("工具输出: %s", output[:2000])
    return output


def run_turn(client, messages, config: Config, confirm_fn=default_confirm, logger=None):
    """跑完一轮:messages 末尾已是用户输入 -> 模型可能多次调用工具 -> 最终文本回复。"""
    while True:
        response = client.messages.create(
            model=config.model,
            max_tokens=config.max_tokens,
            messages=messages,
            tools=TOOLS,
        )
        messages.append({"role": "assistant", "content": response.content})

        for block in response.content:
            if block.type == "text":
                print(f"\n龙虾> {block.text}")
                if logger:
                    logger.info("助手回复: %s", block.text)

        if response.stop_reason != "tool_use":
            break

        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                output = _dispatch_tool(block, config, confirm_fn, logger)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": output,
                    }
                )
        messages.append({"role": "user", "content": tool_results})

    return messages


def main() -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("请先在 .env 文件中设置 ANTHROPIC_API_KEY(或导出为环境变量),再运行本程序。")
        sys.exit(1)

    config = load_config()
    logger = setup_logger(config.log_dir)
    logger.info("会话开始,model=%s max_tokens=%s", config.model, config.max_tokens)

    client_kwargs = {}
    if config.base_url:
        client_kwargs["base_url"] = config.base_url
    client = Anthropic(**client_kwargs)
    messages = []
    print("🦞 龙虾 Agent 已启动。输入 exit / quit 退出。")

    while True:
        try:
            user_input = input("\n你> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见 🦞")
            break

        if user_input in ("exit", "quit"):
            print("再见 🦞")
            break
        if not user_input:
            continue

        logger.info("用户输入: %s", user_input)
        messages.append({"role": "user", "content": user_input})

        try:
            run_turn(client, messages, config, logger=logger)
        except Exception:
            logger.exception("运行出错")
            print("\n[出错了,已记录到日志]")


if __name__ == "__main__":
    main()
