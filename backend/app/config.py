import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=env_path if env_path.exists() else None)

class Settings:
    DATABASE_URL: str = os.environ.get("DATABASE_URL", "sqlite:///./database.db")
    AI_PLATFORM_API_KEY: str = os.environ.get("AI_PLATFORM_API_KEY", "")
    AI_PLATFORM_MODEL: str = os.environ.get("AI_PLATFORM_MODEL", "google/gemma-4-31b-it")
    AI_PLATFORM_API_BASE: str = os.environ.get("AI_PLATFORM_API_BASE", "https://maas-llm-aiplatform-hcm.api.vngcloud.vn/v1")

settings = Settings()
