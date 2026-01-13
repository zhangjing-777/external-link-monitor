"""
配置管理模块
使用 pydantic-settings 管理环境变量和配置
"""
from pydantic_settings import BaseSettings
from urllib.parse import quote_plus
from typing import Optional


class Settings(BaseSettings):
    """应用配置类"""
    
    # 数据库配置
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "password"
    DB_NAME: str = "url_discovery"

    # 连接池配置
    DB_POOL_MIN_SIZE: int = 1
    DB_POOL_MAX_SIZE: int = 10
    
    # Playwright Service 配置
    PLAYWRIGHT_SERVICE_URL: str = "http://playwright-service:8000"
    
    # 截图存储配置
    SCREENSHOT_DIR: str = "/root/service/external-link-monitor/data/screenshots"
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def database_dsn(self) -> str:
        """构造数据库 DSN"""
        encoded_password = quote_plus(self.DB_PASSWORD)
        return f"postgresql://{self.DB_USER}:{encoded_password}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"


# 创建全局配置实例
settings = Settings()