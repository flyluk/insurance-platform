from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "gateway"
    database_url: str = "postgresql://insurance:insurancepass@postgres:5432/identity_db"
    jwt_secret: str = "change-me-in-production"
    jwt_expire_minutes: int = 480
    jwt_algorithm: str = "HS256"

    new_business_url: str = "http://new-business:8000"
    underwriting_url: str = "http://underwriting:8000"
    policy_admin_url: str = "http://policy-admin:8000"
    claims_url: str = "http://claims:8000"
    finance_url: str = "http://finance:8000"

    db_pool_size: int = 5
    db_max_overflow: int = 8
    db_pool_timeout: int = 5
    db_pool_recycle: int = 1800


settings = Settings()
