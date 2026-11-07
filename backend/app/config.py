"""Application configuration loaded from environment variables."""

try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseModel as BaseSettings
from pydantic import Field, ConfigDict
from typing import Optional


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Verity"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://verity:verity@localhost:5432/verity"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # LLM
    LLM_API_BASE: str = "https://api.openai.com/v1"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 2048

    # Embedding
    EMBEDDING_API_BASE: str = "https://api.openai.com/v1"
    EMBEDDING_API_KEY: str = ""
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS: int = 1536
    EMBEDDING_BATCH_SIZE: int = 64

    # Reranking
    RERANKER_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    RERANKER_TOP_K: int = 10

    # Ingestion
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 64
    MAX_FILE_SIZE_MB: int = 100
    SUPPORTED_EXTENSIONS: str = ".pdf,.docx,.txt,.md,.csv"
    BATCH_INGESTION_WORKERS: int = 4

    # Retrieval
    BM25_TOP_K: int = 25
    VECTOR_TOP_K: int = 25
    HYBRID_TOP_K: int = 20
    RRF_K: int = 60
    BM25_WEIGHT: float = 0.4
    VECTOR_WEIGHT: float = 0.6
    MAX_CONTEXT_TOKENS: int = 4096

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:3001"

    # Upload
    UPLOAD_DIR: str = "./uploads"

    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
