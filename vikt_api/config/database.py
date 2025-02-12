from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession
from typing import AsyncGenerator


class DatabaseConnection():
    def __init__(self, db_url: str, db_echo: bool, echo_pool: bool, pool_size: int):
        self.engine = create_async_engine(
            url=db_url,
            echo=db_echo,
            echo_pool=echo_pool,
            pool_size=pool_size
        )
        self.session_factory: AsyncGenerator[AsyncSession, None] = async_sessionmaker(
            bind=self.engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False
        )
    async def sesion_creation(self):
        async with self.session_factory() as session:
            yield session