"""
Self-Healing API Gateway Configuration
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Server
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    debug: bool = Field(default=False)
    
    # Legacy API (Upstream)
    legacy_api_url: str = Field(default="http://localhost:8001")
    
    # Redis
    redis_url: str = Field(default="redis://localhost:6379")
    redis_cache_ttl: int = Field(default=3600)  # 1 hour
    
    # MongoDB
    mongodb_url: str = Field(default="mongodb://localhost:27017")
    mongodb_db_name: str = Field(default="schema_healer")
    
    # LLM Configuration
    llm_api_key: str = Field(default="")
    llm_model: str = Field(default="gpt-4o-mini")
    llm_base_url: str = Field(default="https://api.openai.com/v1")
    
    # Healing Configuration
    enable_auto_healing: bool = Field(default=True)
    max_healing_attempts: int = Field(default=3)
    healing_confidence_threshold: float = Field(default=0.8)
    
    # CORS Configuration (comma-separated list of origins)
    cors_origins: str = Field(default="*")
    
    # Frontend URL (for embedded playground)
    frontend_url: str = Field(default="http://localhost:3000")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
