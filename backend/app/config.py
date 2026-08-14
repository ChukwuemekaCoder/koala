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
    # Comma-separated list of allowed CORS origins (e.g. local dev +
    # deployed Vercel frontend at once) — split via frontend_origins below
    # rather than passed to CORSMiddleware as-is, which would treat the
    # whole comma-joined string as one literal origin that matches nothing.
    frontend_origin: str = "http://localhost:5173"

    @property
    def frontend_origins(self) -> list[str]:
        return [origin.strip() for origin in self.frontend_origin.split(",") if origin.strip()]


settings = Settings()
