import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
env_path = Path(__file__).resolve().parents[2] / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

class Settings:
    # Database Settings
    DATABASE_URL: str = os.environ.get("DATABASE_URL", "sqlite:///./database.db")
    
    # OpenRouter / Qwen LLM Settings
    OPENROUTER_API_KEY: str = os.environ.get("OPENROUTER_API_KEY", "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")
    OPENROUTER_MODEL: str = os.environ.get("OPENROUTER_MODEL", "qwen/qwen-2.5-72b-instruct")
    OPENROUTER_API_BASE: str = os.environ.get("OPENROUTER_API_BASE", "https://openrouter.ai/api/v1")
    
    # Port configuration for reference
    BACKEND_PORT: int = int(os.environ.get("BACKEND_PORT", 8000))
    FRONTEND_PORT: int = int(os.environ.get("FRONTEND_PORT", 8501))

settings = Settings()
