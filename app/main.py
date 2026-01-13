"""
FastAPI 主应用
外链点击篡改监控 / 安全留痕系统
"""
import logging
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import db
from app.services import playwright_service, screenshot_manager
from app.models import (
    CreateSnapshotRequest,
    CreateSnapshotResponse,
    SnapshotDetail,
    ErrorResponse,
    GetDayRequest,
    GetMonthRequest,
    GetRangeRequest
)

# 配置日志
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    启动时创建数据库连接池，关闭时释放资源
    """
    # 启动
    logger.info("应用启动中...")
    await db.connect()
    logger.info("应用启动完成")
    
    yield
    
    # 关闭
    logger.info("应用关闭中...")
    await db.disconnect()
    logger.info("应用已关闭")


# 创建 FastAPI 应用
app = FastAPI(
    root_path="/api/external-link-monitor",
    title="外链点击篡改监控系统",
    description="External Link Click Monitoring & Security Audit System",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", tags=["健康检查"])
async def root():
    """根路径 - 系统信息"""
    return {
        "service": "External Link Click Monitor",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health", tags=["健康检查"])
async def health_check():
    """健康检查接口"""
    return {
        "status": "ok",
        "service": "fastapi-backend"
    }


@app.post(
    "/api/external-link-snapshot",
    response_model=CreateSnapshotResponse,
    responses={
        200: {"model": CreateSnapshotResponse},
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    },
    tags=["快照管理"],
    summary="创建外链点击快照",
    description="执行网页点击操作并记录安全快照"
)
async def create_snapshot(request: CreateSnapshotRequest):
    """
    创建外链点击快照
    
    执行流程:
    1. 调用 Playwright Service 执行点击操作
    2. 接收截图和页面信息
    3. 保存截图文件
    4. 写入数据库
    5. 返回快照 ID
    """
    logger.info("=" * 60)
    logger.info(f"收到创建快照请求: origin_url={request.origin_url}")
    logger.info(f"点击参数: type={request.click_type}, value={request.click_value}")
    logger.info("=" * 60)
    
    try:
        # 1. 调用 Playwright Service
        logger.info("步骤 1/4: 调用 Playwright Service...")
        playwright_result = await playwright_service.render_click(
            url=request.origin_url,
            click_type=request.click_type,
            click_value=request.click_value,
            wait_after_click_ms=request.wait_after_click_ms,
            full_page=request.full_page
        )
        
        page_url = playwright_result.get('page_url')
        page_hash = playwright_result.get('page_hash')
        screenshot_base64 = playwright_result.get('screenshot_base64')
        
        logger.info(f"Playwright 执行完成: page_url={page_url}")
        logger.info(f"page_hash={page_hash[:16] if page_hash else 'None'}...")
        
        # 2. 保存截图文件
        logger.info("步骤 2/4: 保存截图文件...")
        screenshot_path = screenshot_manager.save_screenshot(screenshot_base64)
        logger.info(f"截图已保存: {screenshot_path}")
        
        # 3. 写入数据库
        logger.info("步骤 3/4: 写入数据库...")
        snapshot_id = db.insert_snapshot(
            origin_url=request.origin_url,
            click_type=request.click_type,
            click_value=request.click_value,
            page_url=page_url,
            page_hash=page_hash,
            screenshot_path=screenshot_path
        )
        
        logger.info(f"数据库记录已创建: snapshot_id={snapshot_id}")
        
        # 4. 返回结果
        logger.info("步骤 4/4: 返回结果")
        logger.info("=" * 60)
        logger.info(f"✓ 快照创建成功: snapshot_id={snapshot_id}")
        logger.info("=" * 60)
        
        return CreateSnapshotResponse(
            snapshot_id=snapshot_id,
            status="ok"
        )
        
    except Exception as e:
        logger.error("=" * 60)
        logger.error(f"✗ 快照创建失败: {e}")
        logger.error("=" * 60)
        logger.error("详细错误信息:", exc_info=True)
        
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@app.post("/get-daily-stats-last-60-days")
async def get_daily_stats_last_60_days():
    """
    返回最近 60 天内，
    每天 + 每个 origin_url 的事件总数和 page_hash 去重数
    """
    try:
        res = await db.get_daily_stats_last_60_days()       
        return res
    
    except Exception as e:
        logger.error(f"查询失败: {e}", exc_info=True)       
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")

@app.post("/get-yesterday-events")
async def get_yesterday_events():
    """
    返回昨天所有 origin 的事件明细
    """
    try:
        res = await db.get_yesterday_events()       
        return res
    
    except Exception as e:
        logger.error(f"查询失败: {e}", exc_info=True)       
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")

@app.post("/get-events-by-day")
async def get_events_by_day(request: GetDayRequest):
    """
    返回指定日期（YYYY-MM-DD）当天，
    所有 origin 的事件明细
    """
    try:
        res = await db.get_events_by_day(request.day)       
        return res
    
    except Exception as e:
        logger.error(f"查询失败: {e}", exc_info=True)       
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")
    
@app.post("/get-events-by-month")
async def get_events_by_month(request: GetMonthRequest):
    """
    返回某年某月，
    所有 origin 的事件明细
    """
    try:
        res = await db.get_events_by_month(request.year, request.month)       
        return res
    
    except Exception as e:
        logger.error(f"查询失败: {e}", exc_info=True)       
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")
    
@app.post("/get-events-by-range")
async def get_events_by_range(request: GetRangeRequest):
    """
    返回指定时间区间内，
    所有 origin 的事件明细
    """
    try:
        res = await db.get_events_by_range(request.start_time, request.end_time)       
        return res
    
    except Exception as e:
        logger.error(f"查询失败: {e}", exc_info=True)       
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")