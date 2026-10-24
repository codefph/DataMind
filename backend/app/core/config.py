import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# 本机启用了系统代理（127.0.0.1:1080），Python 的 HTTP 库默认会走代理，
# 导致访问本地容器（Qdrant/Redis/Postgres）被转发为 502。这里让本地地址绕过代理。
os.environ.setdefault("NO_PROXY", "127.0.0.1,localhost,::1")
os.environ.setdefault("no_proxy", "127.0.0.1,localhost,::1")
os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")

BASE_DIR = Path(__file__).resolve().parents[2]

# 把 .env 中的变量加载到 os.environ，供 LiteLLM 等读取厂商 API Key
load_dotenv(BASE_DIR / ".env", override=False)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "DataMind"
    environment: str = "dev"
    debug: bool = False
    api_prefix: str = "/api"

    qdrant_url: str = "http://127.0.0.1:6333"
    qdrant_collection: str = "kb"
    redis_url: str = "redis://127.0.0.1:6379/0"
    database_url: str = "postgresql+asyncpg://datamind:datamind@127.0.0.1:5432/datamind"
    fernet_key: str = ""

    model_default: str = "openai/gpt-4o-mini"
    embedding_default: str = "openai/text-embedding-3-small"
    model_fallbacks: str = ""
    rate_limit_per_minute: int = 30


@lru_cache
def get_settings() -> Settings:
    return Settings()

