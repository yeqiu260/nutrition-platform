
import asyncio
import logging
from app.core.database import init_db, Base
# 必须导入所有模型以便 SQLAlchemy 能够注册它们
from app.models import *

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    logger.info("Initializing database tables...")
    try:
        await init_db()
        logger.info("Database tables initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
