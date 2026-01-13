"""
数据库连接池管理
使用 psycopg (v3) 直接操作 openGauss / PostgreSQL
"""
import logging
from typing import Optional
import asyncio
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.config import settings

logger = logging.getLogger(__name__)


class Database:
    """数据库连接池管理器（psycopg async）"""

    def __init__(self):
        self.pool: Optional[AsyncConnectionPool] = None

    async def connect(self):
        """创建连接池"""
        logger.info(
            f"正在连接数据库: "
            f"{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
        )

        try:
            # psycopg 使用连接字符串（dsn）
            self.pool = AsyncConnectionPool(
                conninfo=settings.database_dsn,
                min_size=settings.DB_POOL_MIN_SIZE,
                max_size=settings.DB_POOL_MAX_SIZE,
                timeout=60,
                open=True,
            )

            logger.info("数据库连接池创建成功")

            # ⚠️ 强烈建议：DDL 不放在应用启动
            # 如果你现在还想保留，也可以用
            await self._init_tables()

        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            raise

    async def disconnect(self):
        """关闭连接池"""
        if self.pool:
            await self.pool.close()
            logger.info("数据库连接池已关闭")

    async def _init_tables(self):
        """初始化数据库表结构（可选）"""
        logger.info("开始初始化数据库表...")

        create_table = """
        CREATE TABLE IF NOT EXISTS external_link_snapshot (
            id              BIGSERIAL PRIMARY KEY,
            origin_url      TEXT NOT NULL,
            click_type      TEXT NOT NULL,
            click_value     TEXT NOT NULL,
            page_url        TEXT,
            page_hash       TEXT,
            screenshot_path TEXT NOT NULL,
            created_at      TIMESTAMP DEFAULT NOW()
        );
        """

        create_indexes = """
        CREATE INDEX IF NOT EXISTS idx_external_link_snapshot_origin ON external_link_snapshot(origin_url);
        CREATE INDEX IF NOT EXISTS idx_external_link_snapshot_id ON external_link_snapshot(id);
        """

        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(create_table)
                await cur.execute(create_indexes)

        logger.info("数据库表初始化完成")

    async def insert_snapshot(
        self,
        origin_url: str,
        click_type: str,
        click_value: str,
        page_url: Optional[str],
        page_hash: Optional[str],
        screenshot_path: str
    ) -> int:
        """
        插入一条快照记录
        
        Args:
            origin_url: 原始页面 URL
            click_type: 点击类型
            click_value: 点击值
            page_url: 点击后的最终 URL
            page_hash: 页面内容哈希
            screenshot_path: 截图文件路径
            
        Returns:
            插入记录的 ID
        """
        
        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                insert_sql = """
                INSERT INTO external_link_snapshot 
                (origin_url, click_type, click_value, page_url, page_hash, screenshot_path)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id;
                """

                await cur.execute(
                    insert_sql,
                    (
                    origin_url, click_type, click_value, page_url, page_hash, screenshot_path
                    ),
                )

    async def get_daily_stats_last_60_days(self):
        """
        返回最近 60 天内，
        每天 + 每个 origin_url 的事件总数和 page_hash 去重数
        """
        sql = """
        SELECT
            date_trunc('day', created_at) AS day,
            origin_url,
            COUNT(id) AS total_events,
            COUNT(DISTINCT page_hash) AS unique_pages
        FROM external_link_snapshot
        WHERE created_at >= NOW() - INTERVAL '60 days'
        GROUP BY day, origin_url
        ORDER BY day ASC, origin_url ASC;
        """

        async with self.pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(sql)
                return await cur.fetchall()

    async def get_yesterday_events(self):
        """
        返回昨天所有 origin 的事件明细
        """
        sql = """
        SELECT *
        FROM external_link_snapshot
        WHERE created_at >= date_trunc('day', NOW() - INTERVAL '1 day')
        AND created_at < date_trunc('day', NOW())
        ORDER BY created_at ASC;
        """

        async with self.pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(sql)
                return await cur.fetchall()

    async def get_events_by_day(self, day: str):
        """
        返回指定日期（YYYY-MM-DD）当天，
        所有 origin 的事件明细
        """
        sql = """
        SELECT *
        FROM external_link_snapshot
        WHERE created_at >= %s::date
        AND created_at < (%s::date + INTERVAL '1 day')
        ORDER BY origin_url ASC, created_at ASC;
        """

        async with self.pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(sql, (day, day))
                return await cur.fetchall()

    async def get_events_by_month(self, year: int, month: int):
        """
        返回某年某月，
        所有 origin 的事件明细
        """
        sql = """
        SELECT *
        FROM external_link_snapshot
        WHERE created_at >= make_date(%s, %s, 1)
        AND created_at < (make_date(%s, %s, 1) + INTERVAL '1 month')
        ORDER BY origin_url ASC, created_at ASC;
        """

        async with self.pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    sql,
                    (year, month, year, month)
                )
                return await cur.fetchall()

    async def get_events_by_range(
        self,
        start_time: str,
        end_time: str
    ):
        """
        返回指定时间区间内，
        所有 origin 的事件明细
        """
        sql = """
        SELECT *
        FROM external_link_snapshot
        WHERE created_at >= %s
        AND created_at <= %s
        ORDER BY origin_url ASC, created_at ASC;
        """

        async with self.pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    sql,
                    (start_time, end_time)
                )
                return await cur.fetchall()


# 全局数据库实例
db = Database()
