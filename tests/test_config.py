import pytest

from config import load_config


def test_load_config_defaults(monkeypatch):
    monkeypatch.delenv("MODEL_ID", raising=False)
    monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
    monkeypatch.delenv("MAX_TOKENS", raising=False)
    monkeypatch.delenv("BASH_TIMEOUT", raising=False)
    monkeypatch.delenv("LOG_DIR", raising=False)
    monkeypatch.delenv("MAX_ITERATIONS", raising=False)

    config = load_config()

    assert config.model == "claude-haiku-4-5"
    assert config.base_url is None
    assert config.max_tokens == 2048
    assert config.bash_timeout == 60
    assert config.log_dir == "logs"
    assert config.max_iterations == 25


def test_load_config_invalid_int_raises(monkeypatch):
    monkeypatch.setenv("MAX_TOKENS", "not-a-number")

    with pytest.raises(ValueError) as excinfo:
        load_config()

    assert "MAX_TOKENS" in str(excinfo.value)


def test_load_config_env_override(monkeypatch):
    monkeypatch.setenv("MODEL_ID", "claude-opus-4-8")
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://example.com")
    monkeypatch.setenv("MAX_TOKENS", "4096")
    monkeypatch.setenv("BASH_TIMEOUT", "120")
    monkeypatch.setenv("LOG_DIR", "custom-logs")

    config = load_config()

    assert config.model == "claude-opus-4-8"
    assert config.base_url == "https://example.com"
    assert config.max_tokens == 4096
    assert config.bash_timeout == 120
    assert config.log_dir == "custom-logs"
