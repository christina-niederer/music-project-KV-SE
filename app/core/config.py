from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str #required from .env
    echo_sql: bool #required from .env

    model_config = SettingsConfigDict(env_file=".env", env_prefix="APP_", extra="ignore")

settings = Settings()