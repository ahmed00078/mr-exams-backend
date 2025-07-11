from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
import redis.asyncio as redis
from config import settings

# Sync database
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Async database  
async_engine = create_async_engine(settings.database_url_async)
AsyncSessionLocal = sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False
)

Base = declarative_base()

# Redis connection
redis_client = redis.from_url(settings.redis_url, decode_responses=True)

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_async_db():
    async with AsyncSessionLocal() as session:
        yield session

async def get_redis():
    return redis_client