"""
Конфигурация приложения
"""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Настройки приложения"""
    
    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    DEBUG: bool = False
    LOG_LEVEL: str = "info"
    
    # Database
    DATABASE_URL: str
    
    # FreeSWITCH
    FREESWITCH_HOST: str = "freeswitch"
    FREESWITCH_PORT: int = 8021
    FREESWITCH_PASSWORD: str = "ClueCon"
    
    # SIP Provider
    SIP_PROVIDER_HOST: str
    SIP_USERNAME: str
    SIP_PASSWORD: str
    SIP_PHONE_NUMBER: str
    
    # OpenAI
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4"
    OPENAI_WHISPER_MODEL: str = "whisper-1"
    
    # ElevenLabs
    ELEVENLABS_API_KEY: str
    ELEVENLABS_VOICE_ID: str = "21m00Tcm4TlvDq8ikWAM"
    
    # JWT
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
    ]
    
    # AI Settings
    AI_ROUTING_ENABLED: bool = True
    AI_ROUTING_CONFIDENCE_THRESHOLD: float = 0.7
    AI_SUPERVISOR_ENABLED: bool = True
    AI_SUPERVISOR_UPDATE_INTERVAL: int = 3
    AI_CONSULTANT_ENABLED: bool = True
    AI_CONSULTANT_MAX_TURNS: int = 10
    
    # Recording
    CALL_RECORDING_ENABLED: bool = True
    CALL_RECORDING_PATH: str = "/recordings"
    CALL_RECORDING_FORMAT: str = "wav"
    
    # Language
    DEFAULT_LANGUAGE: str = "ru"
    SUPPORTED_LANGUAGES: List[str] = ["ru", "en"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

