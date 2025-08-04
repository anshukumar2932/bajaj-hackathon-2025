import os
from pydantic import BaseSettings

class Settings(BaseSettings):
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    HACKRX_API_KEY: str = os.getenv("HACKRX_API_KEY", "default-key-if-not-set")
    PORT: int = int(os.getenv("PORT", "10000"))
    HOST: str = os.getenv("HOST", "0.0.0.0")

    class Config:
        env_file = ".env" if os.path.exists(".env") else None

config = Settings()