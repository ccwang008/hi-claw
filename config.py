"""集中管理运行配置,统一从环境变量读取。"""

import os
from dataclasses import dataclass


@dataclass
class Config:
    model: str
    base_url: str | None
    max_tokens: int
    bash_timeout: int
    log_dir: str


def load_config() -> Config:
    return Config(
        model=os.environ.get("MODEL_ID", "claude-haiku-4-5"),
        base_url=os.environ.get("ANTHROPIC_BASE_URL") or None,
        max_tokens=int(os.environ.get("MAX_TOKENS", "2048")),
        bash_timeout=int(os.environ.get("BASH_TIMEOUT", "60")),
        log_dir=os.environ.get("LOG_DIR", "logs"),
    )
