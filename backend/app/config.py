from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # str_strip_whitespace: values pasted into a host's env-var UI or piped into a CLI often pick
    # up a trailing newline, which would otherwise break API keys.
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", str_strip_whitespace=True
    )

    google_books_api_key: str = ""

    # The assistant's AI model, served by NVIDIA's OpenAI-compatible API (https://build.nvidia.com).
    # The model must support tool calling. NVIDIA retires models from its API without notice (it then
    # answers 404 "Function ... Not found for account"), so this was moved off nemotron-3-super in
    # 2026-11. nemotron-3.5-super took ~30s for a turn with searches and three recommendations.
    nvidia_api_key: str
    nvidia_model: str = "nvidia/nemotron-3.5-super-vl-120b-a12b"
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"

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

    # FastAPI's interactive docs at /docs and /openapi.json. Off unless turned on (in a local .env),
    # so a public deployment never advertises the API by accident.
    api_docs_enabled: bool = False

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
