import os
import yaml
from typing import Any, Dict
from dotenv import load_dotenv

# Load .env before reading any settings so environment overrides are always applied
load_dotenv()

# Path to config.yaml
CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.yaml")

def load_config() -> Dict[str, Any]:
    """
    Load configuration from config.yaml.
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

# Environment variables take precedence over config.yaml
RETRIEVAL_STRATEGY = get_config_value("retrieval_strategy", "semantic")
LLM_MODEL_NAME = get_config_value("llm_model_name", "llama")
VECTOR_DB = get_config_value("vector_db", "chroma")  # "chroma" (local) or "pinecone"

# Vector store settings shared by ingestion and retrieval
CHROMA_PATH = "data/chroma_db"
COLLECTION_NAME = "aerostream_docs"
EMBEDDING_MODEL = "nomic-embed-text"
