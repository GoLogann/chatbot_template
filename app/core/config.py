from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LoggingConfig(BaseModel):
    version: int = 1
    formatters: dict = {
        "default": {
            "format": "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s"
        }
    }
    handlers: dict = {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "default",
            # "stream": "ext://sys.stderr",
        }
    }
    root: dict = {"level": "INFO", "handlers": ["console"]}


class Settings(BaseSettings):
    AWS_REGION: str = "us-east-1"
    AWS_PROFILE: Optional[str] = None
    BEDROCK_MODEL_ID_CHAT: str = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
    BEDROCK_MODEL_ID_EMBED: str = "amazon.titan-embed-text-v2:0"
    TEMPERATURE: float = 0.2
    
    DDB_TABLE: str = Field(default="ChatbotTemplateTable")
    AWS_ENDPOINT_URL: Optional[str] = None
    USE_DYNAMODB_LOCAL: bool = False
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    
    APP_URL: str = Field(default="http://localhost:8090", env="APP_URL")
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")

    TRACING_SERVICE_NAME: str = "chatbot-template"

    # Langfuse Configuration
    LANGFUSE_HOST: Optional[str] = None
    LANGFUSE_PUBLIC_KEY: Optional[str] = None
    LANGFUSE_SECRET_KEY: Optional[str] = None

    # WhatsApp Configuration (Meta API)
    WHATSAPP_PHONE_NUMBER_ID: Optional[str] = None
    WHATSAPP_ACCESS_TOKEN: Optional[str] = None
    WHATSAPP_VERIFY_TOKEN: Optional[str] = None

    LOGGING: LoggingConfig = LoggingConfig()

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
