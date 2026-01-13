"""
业务逻辑服务层
负责调用 Playwright Service 和处理业务逻辑
"""
import logging
import base64
import os
import uuid
import httpx
from datetime import datetime
from typing import Dict, Any, Optional
from app.config import settings

logger = logging.getLogger(__name__)


class PlaywrightService:
    """Playwright 服务客户端"""
    
    def __init__(self):
        """初始化 Playwright 服务配置"""
        self.base_url = settings.PLAYWRIGHT_SERVICE_URL
        self.timeout = 120.0  # 2分钟超时
        logger.info(f"Playwright Service URL: {self.base_url}")
    
    async def render_click(
        self,
        url: str,
        click_type: str,
        click_value: str,
        wait_after_click_ms: int = 3000,
        full_page: bool = True
    ) -> Dict[str, Any]:
        """
        调用 Playwright Service 执行点击渲染
        
        Args:
            url: 目标页面 URL
            click_type: 点击类型 (text/css/xpath/aria)
            click_value: 点击值
            wait_after_click_ms: 点击后等待时间（毫秒）
            full_page: 是否全页面截图
            
        Returns:
            包含 page_url, page_hash, screenshot_base64 的字典
            
        Raises:
            httpx.HTTPError: HTTP 请求失败
            Exception: 其他错误
        """
        request_data = {
            "url": url,
            "click": {
                "type": click_type,
                "value": click_value
            },
            "wait_after_click_ms": wait_after_click_ms,
            "full_page": full_page
        }
        
        logger.info(f"调用 Playwright Service: {self.base_url}/render-click")
        logger.debug(f"请求参数: url={url}, click_type={click_type}, click_value={click_value}")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/render-click",
                    json=request_data
                )
                
                # 检查响应状态
                if response.status_code != 200:
                    error_msg = f"Playwright Service 返回错误: {response.status_code}"
                    logger.error(error_msg)
                    logger.error(f"响应内容: {response.text}")
                    raise Exception(error_msg)
                
                result = response.json()
                
                # 验证返回数据
                if result.get('status') != 'ok':
                    error_msg = f"Playwright Service 执行失败: {result.get('message', 'Unknown error')}"
                    logger.error(error_msg)
                    raise Exception(error_msg)
                
                logger.info(f"Playwright Service 执行成功")
                logger.debug(f"page_url={result.get('page_url')}, page_hash={result.get('page_hash', '')[:16]}...")
                
                return result
                
        except httpx.TimeoutException as e:
            error_msg = f"Playwright Service 请求超时: {e}"
            logger.error(error_msg, exc_info=True)
            raise Exception(error_msg)
        except httpx.HTTPError as e:
            error_msg = f"Playwright Service HTTP 请求失败: {e}"
            logger.error(error_msg, exc_info=True)
            raise Exception(error_msg)
        except Exception as e:
            logger.error(f"调用 Playwright Service 失败: {e}", exc_info=True)
            raise


class ScreenshotManager:
    """截图文件管理器"""
    
    def __init__(self):
        """初始化截图目录"""
        self.screenshot_dir = settings.SCREENSHOT_DIR
        
        # 确保截图目录存在
        os.makedirs(self.screenshot_dir, exist_ok=True)
        logger.info(f"截图目录: {self.screenshot_dir}")
    
    def save_screenshot(self, screenshot_base64: str) -> str:
        """
        保存截图文件
        
        Args:
            screenshot_base64: Base64 编码的截图数据
            
        Returns:
            截图文件的相对路径
            
        Raises:
            Exception: 保存失败
        """
        try:
            # 生成唯一文件名: timestamp_uuid.png
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = str(uuid.uuid4())[:8]
            filename = f"{timestamp}_{unique_id}.png"
            
            # 完整路径
            filepath = os.path.join(self.screenshot_dir, filename)
            
            logger.info(f"保存截图: {filename}")
            
            # 解码 base64 并保存
            screenshot_data = base64.b64decode(screenshot_base64)
            
            with open(filepath, 'wb') as f:
                f.write(screenshot_data)
            
            logger.info(f"截图保存成功: {filepath} ({len(screenshot_data)} bytes)")
            
            return filepath
            
        except Exception as e:
            logger.error(f"保存截图失败: {e}", exc_info=True)
            raise
    
    def screenshot_exists(self, filepath: str) -> bool:
        """
        检查截图文件是否存在
        
        Args:
            filepath: 数据库中存储的路径
            
        Returns:
            文件是否存在
        """
        exists = os.path.isfile(filepath)
        
        if not exists:
            logger.warning(f"截图文件不存在: {filepath}")
        
        return exists


# 创建全局服务实例
playwright_service = PlaywrightService()
screenshot_manager = ScreenshotManager()
