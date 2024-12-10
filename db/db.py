from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
import asyncio

from decouple import config

# Database connection string
DB_USER = config('DB_USER', 'rohanphulkar')
DB_PASSWORD = config('DB_PASSWORD', 'Rohan007')
DB_HOST = config('DB_HOST', 'localhost')
DB_PORT = config('DB_PORT', '3306')
DB_NAME = config('DB_NAME', 'fastapi')

# Using aiomysql as the async driver instead of pymysql
SQLALCHEMY_DATABASE_URL = f"mysql+aiomysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Create async engine
engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
    echo=True  # Enable SQL logging
)

# Create session factory
SessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False
)

# Create declarative base
class Base(DeclarativeBase):
    pass

# Create all tables
async def init_models():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# Run the initialization
loop = asyncio.get_event_loop()
loop.run_until_complete(init_models())
loop.close()

async def get_db():
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            raise e
