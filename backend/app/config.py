from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    redis_url: str = "redis://redis:6379/0"
    supabase_url: str
    supabase_anon_key: str | None = None
    # Test-fixture use only (creating/tearing down the integration test's
    # throwaway user via the Auth Admin API) — never read by request-
    # handling code. Optional so the app still boots without it.
    supabase_service_role_key: str | None = None
    frontend_origin: str = "http://localhost:5173"


settings = Settings()
