from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    app_env: str = Field(default="development")
    api_v1_prefix: str = "/api/v1"
    cors_origins: str = Field(default="http://localhost:5173,http://127.0.0.1:5173")

    # Database
    database_url: str = Field(default="postgresql+psycopg://intelapi:intelapi@db:5432/intelapi")

    # Session/auth
    session_secret_key: str = Field(default="dev-session-secret-change-me")
    session_cookie_name: str = "intelapi_session"
    session_cookie_secure: bool = False
    session_cookie_samesite: str = "lax"
    session_ttl_seconds: int = 60 * 60 * 24 * 14  # 14 days
    google_client_id: str = Field(default="")
    csrf_secret: str = Field(default="dev-csrf-secret-change-me")

    # Environment secret encryption
    encryption_key: str = Field(default="")  # Fernet key. Auto-generated when empty for dev only.

    # Outbound execution policy
    outbound_connect_timeout_seconds: float = 5.0
    outbound_read_timeout_seconds: float = 15.0
    outbound_total_timeout_seconds: float = 30.0
    outbound_max_response_bytes: int = 1 * 1024 * 1024  # 1 MiB
    outbound_max_redirects: int = 5
    outbound_max_concurrency: int = 20
    outbound_spec_max_bytes: int = 2 * 1024 * 1024  # 2 MiB
    outbound_block_loopback: bool = True
    outbound_block_private: bool = True
    outbound_allowed_hosts: str = Field(default="")  # comma-separated host:port allowlist (future use)

    # Campaign defaults
    campaign_default_budget: int = 200
    campaign_lease_seconds: int = 30
    campaign_heartbeat_seconds: int = 10
    worker_id: str = Field(default="worker-local")

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def outbound_allowed_hosts_list(self) -> List[str]:
        return [o.strip() for o in self.outbound_allowed_hosts.split(",") if o.strip()]


@lru_cache()
def get_settings() -> Settings:
    return Settings()
