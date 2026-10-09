from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="HOMERUN_", env_file=(".env", "../.env"), extra="ignore"
    )

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    auth_token: str = "change-me"

    # Arduino serial
    serial_port: str = "/dev/ttyACM0"
    baud: int = 115200
    serial_enabled: bool = True
    heartbeat_s: float = 5.0

    # Storage
    db_path: str = "./data/homerun.db"
    media_dir: str = "./data"

    # Ollama
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:3b"
    ollama_enabled: bool = True

    # Camera
    camera_backend: str = "auto"  # auto | picamera | opencv | synthetic
    camera_index: int = 0
    camera_width: int = 1280
    camera_height: int = 720
    motion_diff_threshold: int = 25
    motion_min_area: int = 1500
    motion_cooldown_s: int = 20

    # Plants
    soil_threshold: int = 35
    soil_target: int = 55
    water_max_s: int = 60
    water_min_interval_s: int = 1800


@lru_cache
def get_settings() -> Settings:
    return Settings()
