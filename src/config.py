import os
import yaml
from typing import Any, Dict

# Path to config.yaml
CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.yaml")

def load_config() -> Dict[str, Any]:
    """
    Load configuration from config.yaml and override with environment variables.
    """
    config = {}
    
    # Load from YAML
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r") as f:
                config = yaml.safe_load(f) or {}
        except Exception as e:
            print(f"Warning: Failed to load config.yaml: {e}")
    
    return config

# Load configuration once
_config = load_config()

# Export configuration with environment variable overrides
# Environment variables take precedence over config.yaml

RETRIEVAL_STRATEGY = os.getenv("RETRIEVAL_STRATEGY", _config.get("retrieval_strategy", "semantic"))
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", _config.get("llm_model_name", "llama"))

def get_config_value(key: str, default: Any = None) -> Any:
    """
    Get a configuration value, checking environment variables first, then config.yaml, then default.
    Key should be in lowercase for config.yaml matching.
    Env var is assumed to be UPPERCASE of key.
    """
    env_key = key.upper()
    if env_key in os.environ:
        return os.environ[env_key]
    
    return _config.get(key, default)
