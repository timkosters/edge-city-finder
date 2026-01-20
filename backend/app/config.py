from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    EXA_API_KEY: str = ""
    TAVILY_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
