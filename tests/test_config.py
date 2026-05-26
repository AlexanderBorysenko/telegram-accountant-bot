import os
import pytest
from unittest.mock import patch


def test_config_loads_from_env():
    env = {
        "TELEGRAM_BOT_TOKEN": "test-token",
        "ANTHROPIC_API_KEY": "test-key",
        "MONGODB_URI": "mongodb://localhost:27017",
        "MONGODB_DB_NAME": "testdb",
    }
    with patch.dict(os.environ, env, clear=False):
        from importlib import reload
        import src.config as config_module
        reload(config_module)
        config = config_module.Settings()
        assert config.telegram_bot_token == "test-token"
        assert config.anthropic_api_key == "test-key"
        assert config.mongodb_uri == "mongodb://localhost:27017"
        assert config.mongodb_db_name == "testdb"


def test_config_defaults():
    env = {
        "TELEGRAM_BOT_TOKEN": "test-token",
        "ANTHROPIC_API_KEY": "test-key",
    }
    with patch.dict(os.environ, env, clear=False):
        from importlib import reload
        import src.config as config_module
        reload(config_module)
        config = config_module.Settings()
        assert config.mongodb_uri == "mongodb://mongo:27017"
        assert config.mongodb_db_name == "buhalter"
