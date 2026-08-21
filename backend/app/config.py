from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent
ARTIFACTS_DIR = BASE_DIR / "artifacts"
DATA_DIR = BASE_DIR / "data"


class Settings(BaseSettings):
    groq_api_key: str = ""
    database_url: str = f"sqlite:///{BASE_DIR / 'data' / 'airisk.db'}"
    cors_origins: str = "http://localhost:3000"
    max_transactions_load: int = 150000
    model_name: str = "XGBoost"

    class Config:
        env_file = BASE_DIR / ".env"
        extra = "ignore"


settings = Settings()
