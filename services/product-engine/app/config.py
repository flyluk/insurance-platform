from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "product-engine"
    database_url: str = "postgresql://insurance:insurancepass@postgres:5432/product_db"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"

    db_pool_size: int = 5
    db_max_overflow: int = 8
    db_pool_timeout: int = 5
    db_pool_recycle: int = 1800
    uvicorn_workers: int = 2


settings = Settings()
