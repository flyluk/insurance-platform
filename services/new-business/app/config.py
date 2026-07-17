from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "new-business"
    database_url: str = "postgresql://insurance:insurancepass@postgres:5432/nb_db"
    jwt_secret: str = "change-me-in-production"
    jwt_expire_minutes: int = 60
    jwt_algorithm: str = "HS256"

    underwriting_events_url: str = "http://underwriting:8000/events"

    db_pool_size: int = 5
    db_max_overflow: int = 8
    db_pool_timeout: int = 5
    db_pool_recycle: int = 1800
    uvicorn_workers: int = 2
    outbox_poll_seconds: float = 2.0


settings = Settings()
