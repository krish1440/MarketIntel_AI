import os
from pathlib import Path
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    # Angel One SmartAPI
    ANGEL_API_KEY: str = os.getenv("ANGEL_API_KEY", "")
    ANGEL_CLIENT_CODE: str = os.getenv("ANGEL_CLIENT_CODE", "")
    ANGEL_PIN: str = os.getenv("ANGEL_PIN", "")
    ANGEL_TOTP_SECRET: str = os.getenv("ANGEL_TOTP_SECRET", "")
    
    # Storage Paths
    BASE_DIR: Path = BASE_DIR
    DATA_DIR: Path = BASE_DIR / "data"
    LAKEHOUSE_DIR: Path = BASE_DIR / "data" / "lakehouse"
    BRONZE_DIR: Path = LAKEHOUSE_DIR / "bronze"
    SILVER_DIR: Path = LAKEHOUSE_DIR / "silver"
    GOLD_DIR: Path = LAKEHOUSE_DIR / "gold"
    
    # Redis
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))

    class Config:
        case_sensitive = True

settings = Settings()

# Ensure directories exist
for directory in [
    settings.DATA_DIR,
    settings.LAKEHOUSE_DIR,
    settings.BRONZE_DIR,
    settings.SILVER_DIR,
    settings.GOLD_DIR,
    settings.BRONZE_DIR / "master",
    settings.BRONZE_DIR / "bhavcopy",
    settings.BRONZE_DIR / "intraday_raw",
    settings.SILVER_DIR / "ohlcv_1d",
    settings.SILVER_DIR / "ohlcv_1m",
    settings.SILVER_DIR / "ohlcv_5m",
    settings.GOLD_DIR / "features_daily",
    settings.GOLD_DIR / "features_intraday_5m",
    settings.GOLD_DIR / "sector_aggregates",
]:
    directory.mkdir(parents=True, exist_ok=True)

