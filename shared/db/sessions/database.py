import logging
from logging import Logger
from typing import AsyncGenerator, Optional

from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from shared.db.models import EventsBase

# Configure logging
logging.basicConfig(level=logging.INFO)
logger: Logger = logging.getLogger(__name__)

# --------------------- Engine & Session Helpers ---------------------


def create_async_db_engine(db_url: str) -> AsyncEngine:
    """Create and return an asynchronous SQLAlchemy engine from the given URL."""
    print(f"Creating engine with DB URL: {db_url}")
    return create_async_engine(
        url=db_url,
        echo=False,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_pre_ping=True,
        pool_recycle=1800,
        isolation_level="READ COMMITTED",
        future=True,
    )


def create_session_factory(
    engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    """Create and return a sessionmaker bound to the given engine."""
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


def get_db_session_factory(db_url: str) -> async_sessionmaker[AsyncSession]:
    """Helper to create a session factory from a DB URL."""
    engine = create_async_db_engine(db_url)
    return create_session_factory(engine)


# --------------------- Lifecycle Hooks ---------------------


async def init_db(db_url: str) -> None:
    """
    Initialize database using the provided URL.
    Creates all tables defined in EventsBase.metadata.
    """
    engine = create_async_db_engine(db_url)

    try:
        async with engine.begin() as conn:
            logger.info("Creating database tables if they do not exist...")
            await conn.run_sync(EventsBase.metadata.create_all, checkfirst=True)
    except OperationalError as e:
        logger.error("Operational error while connecting to DB: %s", str(e))
        raise
    except Exception as e:
        logger.error("Unexpected error during DB initialization: %s", str(e))
        raise
    finally:
        await engine.dispose()


async def shutdown_db(
    engine: AsyncEngine, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    """Dispose of the engine and session factory resources."""
    try:
        logger.info("Shutting down DB engine and session factory")
        await session_factory().close_all()
        await engine.dispose()
    except Exception as e:
        logger.error("Error during DB shutdown: %s", str(e))
        raise


# --------------------- Global Dependency Support ---------------------

global_session_factory: Optional[async_sessionmaker[AsyncSession]] = None
global_engine: Optional[AsyncEngine] = None


def configure_session_factory(db_url: str) -> async_sessionmaker[AsyncSession]:
    """Configure and store a global session factory and engine (e.g., at app startup)."""
    global global_session_factory, global_engine
    global_engine = create_async_db_engine(db_url)
    global_session_factory = create_session_factory(global_engine)

    return global_session_factory


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(OperationalError),
    after=lambda state: logger.warning(
        f"Retrying DB connection (attempt {state.attempt_number})"
    ),
)
async def get_db_session_from_global_factory() -> (
    AsyncGenerator[AsyncSession, None]
):
    """Get a DB session from the globally configured session factory."""
    if global_session_factory is None:
        raise RuntimeError(
            "Session factory not configured. Call `configure_session_factory()` first."
        )

    async with global_session_factory() as session:
        try:
            yield session
        except Exception as e:
            logger.error("Database session error: %s", str(e))
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI-compatible dependency to provide a DB session."""
    async for session in get_db_session_from_global_factory():
        yield session
