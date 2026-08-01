from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    app_name: str = "RAG Document Q&A"
    debug: bool = False

    # Auth
    secret_key: str = "change-me-in-.env"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24

    # Postgres
    database_url: str = "postgresql://raguser:ragpass@localhost:5432/ragdb"

    # ChromaDB
    chroma_persist_dir: str = "./data/chroma"
    chroma_collection_name: str = "documents"

    # Chunking
    chunk_size: int = 800          # characters per chunk
    chunk_overlap: int = 150       # characters of overlap between chunks

    # Retrieval
    top_k_chunks: int = 5

    # Groq (LLM)
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    # Uploads
    upload_dir: str = "./uploads"
    max_upload_mb: int = 20

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
