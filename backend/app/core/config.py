from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_chat_model: str = Field(default="gpt-4.1-mini", alias="OPENAI_CHAT_MODEL")
    chroma_collection_name: str = Field(default="budget_measures", alias="CHROMA_COLLECTION_NAME")
    sqlite_db_path: Path = Field(default_factory=lambda: _repo_root() / "data" / "sqlite" / "catalogue.db")
    chroma_path: Path = Field(default_factory=lambda: _repo_root() / "data" / "chroma")


@lru_cache
def get_settings() -> Settings:
    return Settings()