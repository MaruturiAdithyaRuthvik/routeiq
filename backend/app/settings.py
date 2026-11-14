"""Runtime configuration for the RouteIQ API."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    database_url: str = (
        "postgresql+psycopg://routeiq_app_login:routeiq_app_dev_only@localhost:5432/routeiq"
    )
    evaluator_database_url: str = (
        "postgresql://routeiq_evaluator_login:routeiq_evaluator_dev_only@localhost:5432/routeiq"
    )
    postgres_user: str = "routeiq"
    postgres_password: str = "routeiq_dev_only"
    postgres_db: str = "routeiq"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    jwt_secret: str = "routeiq-local-demo-secret-change-me"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    port: int = 8000

    model_config = SettingsConfigDict(env_file=_ROOT / ".env", extra="ignore")

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
