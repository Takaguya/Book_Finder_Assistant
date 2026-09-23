from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # str_strip_whitespace: values pasted into a host's env-var UI or piped into a CLI often pick
    # up a trailing newline, which would otherwise break API keys.
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", str_strip_whitespace=True
    )

    google_books_api_key: str = ""
    gemini_api_key: str
    gemini_model: str = "gemini-3.6-flash"

    firebase_service_account_path: str = "./serviceAccountKey.json"
    # The key file's JSON contents, for hosts where the file itself can't be deployed (Vercel).
    # Takes priority over firebase_service_account_path when set.
    firebase_service_account_json: str = ""
    firebase_project_id: str = ""

    cors_origins: str = "http://localhost:5173"
    chat_history_limit: int = 20

    # Per-user request limits, enforced across all server instances (see
    # app/dependencies/rate_limit.py). Set one to 0 to turn it off.
    rate_limit_chat_per_minute: int = 6
    rate_limit_chat_per_day: int = 100
    rate_limit_new_sessions_per_hour: int = 20
    rate_limit_book_searches_per_minute: int = 20

    # FastAPI's interactive docs at /docs and /openapi.json. Turn off on public deployments so the
    # API isn't advertised.
    api_docs_enabled: bool = True

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
