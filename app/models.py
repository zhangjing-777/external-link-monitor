"""
Pydantic 数据模型定义
用于请求验证和响应序列化
"""
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional
from datetime import datetime


class CreateSnapshotRequest(BaseModel):
    """创建快照请求"""
    origin_url: str = Field(..., description="原始页面 URL")
    click_type: str = Field(..., description="点击类型: text/css/xpath/aria")
    click_value: str = Field(..., description="点击值: 按钮文本或选择器")
    wait_after_click_ms: int = Field(default=3000, ge=0, description="点击后等待时间（毫秒）")
    full_page: bool = Field(default=True, description="是否全页面截图")
    
    class Config:
        json_schema_extra = {
            "example": {
                "origin_url": "https://example.com",
                "click_type": "text",
                "click_value": "立即下载",
                "wait_after_click_ms": 3000,
                "full_page": True
            }
        }


class CreateSnapshotResponse(BaseModel):
    """创建快照响应"""
    snapshot_id: int = Field(..., description="快照记录 ID")
    status: str = Field(default="ok", description="执行状态")
    
    class Config:
        json_schema_extra = {
            "example": {
                "snapshot_id": 123,
                "status": "ok"
            }
        }


class SnapshotDetail(BaseModel):
    """快照详情"""
    id: int = Field(..., description="快照 ID")
    origin_url: str = Field(..., description="原始页面 URL")
    click_type: str = Field(..., description="点击类型")
    click_value: str = Field(..., description="点击值")
    page_url: Optional[str] = Field(None, description="点击后的最终 URL")
    page_hash: Optional[str] = Field(None, description="页面内容哈希")
    screenshot_path: str = Field(..., description="截图文件路径")
    created_at: datetime = Field(..., description="创建时间")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": 123,
                "origin_url": "https://example.com",
                "click_type": "text",
                "click_value": "立即下载",
                "page_url": "https://download.example.com/file.exe",
                "page_hash": "a1b2c3d4e5f6...",
                "screenshot_path": "20240115_123456_abc123.png",
                "created_at": "2024-01-15T12:34:56"
            }
        }


class ErrorResponse(BaseModel):
    """错误响应"""
    status: str = Field(default="error", description="状态")
    message: str = Field(..., description="错误信息")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "error",
                "message": "快照不存在"
            }
        }

class GetDayRequest(BaseModel):
    """指定日期（YYYY-MM-DD）"""
    day: str = Field(..., description="创建时间")
    
    class Config:
        json_schema_extra = {
            "example": {
                "day": "2026-01-13",
            }
        }

class GetMonthRequest(BaseModel):
    """指定year, month"""
    year: int = Field(..., description="创建年份")
    month: int = Field(..., description="创建月份")
    
    class Config:
        json_schema_extra = {
            "example": {
                "year": 2026,
                "month":1,
            }
        }

class GetRangeRequest(BaseModel):
    """指定year, month"""
    start_time: str = Field(..., description="创建开始时间")
    end_time: str = Field(..., description="创建结束时间")
    
    class Config:
        json_schema_extra = {
            "example": {
                "start_time": "2026-01-01T00:00:00",
                "end_time": "2026-01-31T23:59:59",
            }
        }