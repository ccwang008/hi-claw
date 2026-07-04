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
    max_iterations: int


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        raise ValueError(f"环境变量 {name} 必须是整数,当前值:{raw!r}") from None


def load_config() -> Config:
    return Config(
        model=os.environ.get("MODEL_ID", "claude-haiku-4-5"),
        base_url=os.environ.get("ANTHROPIC_BASE_URL") or None,
        max_tokens=_env_int("MAX_TOKENS", 2048),
        bash_timeout=_env_int("BASH_TIMEOUT", 60),
        log_dir=os.environ.get("LOG_DIR", "logs"),
        max_iterations=_env_int("MAX_ITERATIONS", 25),
    )
