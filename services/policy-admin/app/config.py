from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "policy-admin"
    database_url: str = "postgresql://insurance:insurancepass@postgres:5432/policy_db"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"

    product_engine_url: str = "http://product-engine:8000"
    new_business_events_url: str = "http://new-business:8000/events"
    finance_events_url: str = "http://finance:8000/events"

    db_pool_size: int = 5
    db_max_overflow: int = 8
    db_pool_timeout: int = 5
    db_pool_recycle: int = 1800
    uvicorn_workers: int = 1
    outbox_poll_seconds: float = 2.0


settings = Settings()
