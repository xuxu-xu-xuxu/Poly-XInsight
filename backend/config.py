from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    milvus_host: str = "localhost"
    milvus_port: int = 19530
    es_host: str = "http://localhost:9200"
    es_user: str = "elastic"
    es_password: str = "YourPassword123!"
    database_url: str = "postgresql+asyncpg://user:password@localhost:5432/literature"
    bge_embed_url: str = "http://localhost:8000/embed"
    llm_provider: str = "deepseek"
    llm_api_key: str = ""
    llm_base_url: str = "https://api.deepseek.com/v1"
    llm_model: str = "deepseek-chat"
    upload_dir: str = "./uploads"
    scansci_download_dir: str = "./downloads"
    scansci_download_strategy: str = "legal_only"
    chunk_size: int = 1100
    chunk_overlap: int = 150
    ingestion_concurrency: int = 2
    embedding_batch_size: int = 80
    llm_extract_concurrency: int = 2
    enable_structured_extraction: bool = False
    extraction_confidence_threshold: float = 0.7

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings() -> Settings:
    return Settings()
