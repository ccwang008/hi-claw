from config import load_config


def test_load_config_defaults(monkeypatch):
    monkeypatch.delenv("MODEL_ID", raising=False)
    monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
    monkeypatch.delenv("MAX_TOKENS", raising=False)
    monkeypatch.delenv("BASH_TIMEOUT", raising=False)
    monkeypatch.delenv("LOG_DIR", raising=False)

    config = load_config()

    assert config.model == "claude-haiku-4-5"
    assert config.base_url is None
    assert config.max_tokens == 2048
    assert config.bash_timeout == 60
    assert config.log_dir == "logs"


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
