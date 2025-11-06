import os
from typing import Optional

from pydantic.v1 import Field
from pydantic_settings import BaseSettings

use_secret = True
use_secret_env = os.getenv("USE_SECRET")
if use_secret_env and use_secret_env.lower() == "false":
    use_secret = False


class Settings(BaseSettings):
    # 配置
    INTERVAL_MINUTES: int = Field(..., env="INTERVAL_MINUTES")
    STOP_LOSS_INTERVAL_SECOND: int = Field(..., env="STOP_LOSS_INTERVAL_SECOND")
    USDT_AMOUNT: int = Field(..., env="USDT_AMOUNT")
    LEVERAGE: int = Field(..., env="LEVERAGE")
    MGN_MODE: str = Field(..., env="MGN_MODE")
    SYMBOLS: str = Field(..., env="SYMBOLS")

    OKX_APIKEY: str = Field(..., env="OKX_APIKEY")
    OKX_SECRET: str = Field(..., env="OKX_SECRET")
    OKX_PASSWORD: str = Field(..., env="OKX_PASSWORD")

    AI_ENDPOINT: str = Field(..., env="AI_ENDPOINT")
    OPENAI_API_KEY: str = Field(..., env="OPENAI_API_KEY")
    OPENAI_BASE_URL: str = Field(..., env="OPENAI_BASE_URL")
    OPENAI_MODEL: str = Field(..., env="OPENAI_MODEL")
    AI_TIMEFRAMES: str = Field(..., env="AI_TIMEFRAMES")
    AI_COMPARE: int = Field(..., env="AI_COMPARE")

    model_config = {
        "extra": "ignore",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


settings = Settings()
