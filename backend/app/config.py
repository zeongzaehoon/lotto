import os

from pydantic_settings import BaseSettings, SettingsConfigDict

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    mongodb_url: str = "mongodb://admin:changeme@localhost:27017/lotto_db?authSource=admin"
    mongo_db_name: str = "lotto_db"
    ml_dir: str = os.path.join(_BASE_DIR, "ml")


settings = Settings()
