"""Configuration for the AI Agent Evaluation Pipeline."""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment."""
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # Database - use SQLite for local dev if no Postgres
    database_url: str = "sqlite+aiosqlite:///./agent_eval.db"
    
    # LLM
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    eval_model: str = "gpt-4o-mini"  # Cost-effective for evaluations
    
    # Evaluation thresholds
    latency_threshold_ms: int = 1000
    max_conversation_turns: int = 20
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
