import os
from pydantic_settings import BaseSettings  # Changed import
from pydantic import Field

class Settings(BaseSettings):
    GEMINI_API_KEY: str = Field(default="", env="GEMINI_API_KEY")
    HACKRX_API_KEY: str = Field(
        default="eee600e04aa65918a209cc00dce620a24133f7c319bc2fc5cd3e600071dfbb5e",
        env="HACKRX_API_KEY"
    )
    PORT: int = Field(default=10000, env="PORT")
    HOST: str = Field(default="0.0.0.0", env="HOST")

    class Config:
        env_file = ".env" if os.path.exists(".env") else None
        extra = "ignore"

config = Settings()