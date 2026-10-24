from pydantic_settings import BaseSettings,SettingsConfigDict
from pydantic import Field
from typing import Literal
from pathlib import Path
import os

# Project root = two levels above backend/config/
PROJECT_ROOT = Path(__file__).resolve().parents[2]

class Settings(BaseSettings):
    app_name: str = "Meridian AI - Procurement Intelligence"
    app_env: str = Field("local", validation_alias="ENVIRONMENT")
    app_version: str = "1.1.0"

    # --- The toggle ---
    app_mode: Literal["local", "cloud"] = Field("local", validation_alias="APP_MODE")

    # --- Gemini (used in BOTH modes for the chat model) --- 
    GOOGLE_API_KEY: str = Field("", validation_alias="GOOGLE_API_KEY")
    llm_model_name: str = Field("gemini-3.8-flash", validation_alias="VERTEX_LLM_MODEL_NAME")
    # 0 = most repeatable answers. If the model loops or repeats itself, try 1.0 (Gemini 3 default)
    llm_temperature: float = Field(0.0, validation_alias="LLM_TEMPERATURE")

    # --- Embeddings ---
    # Local: Gemini API model (API key). Chroma has no fixed size, 768 keeps both modes alike.
    local_embedding_model_name: str = Field("gemini-embedding-001", validation_alias="LOCAL_EMBEDDING_MODEL_NAME")
    embedding_dimensions: int = 768
    
    # --- Agent middleware limits ---
    agent_max_model_calls: int = Field(8, validation_alias="AGENT_MAX_MODEL_CALLS")
    agent_max_tool_calls: int = Field(6, validation_alias="AGENT_MAX_TOOL_CALLS")
    agent_max_retries: int = Field(2, validation_alias="AGENT_MAX_RETRIES")


    # --- Local mode storage ---
    local_data_dir: str = Field(str(PROJECT_ROOT / ".meridian"), validation_alias="LOCAL_DATA_DIR")
    chroma_collection: str = Field("meridian_docs", validation_alias="CHROMA_COLLECTION")

    @property
    def local_upload_dir(self) -> str:
        return os.path.join(self.local_data_dir, "uploads")

    @property
    def chroma_dir(self) -> str:
        return os.path.join(self.local_data_dir, "chroma")
    
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),  # found no matter which folder you start from
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()