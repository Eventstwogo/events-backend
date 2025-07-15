# db/events.py
import time
from typing import Any

from sqlalchemy import event
from sqlalchemy.engine import Engine

from shared.core.logging_config import get_logger

logger = get_logger(__name__)


def init_db_event_listeners(engine: Engine) -> None:
    """
    Registers SQLAlchemy event listeners for logging DB query execution time.
    Supports both sync and async engines.
    """

    @event.listens_for(engine, "before_cursor_execute")
    def before_cursor_execute(*args: Any) -> None:
        if len(args) >= 5:
            context = args[4]
            setattr(context, "_query_start_time", time.perf_counter())

    @event.listens_for(engine, "after_cursor_execute")
    def after_cursor_execute(*args: Any) -> None:
        if len(args) >= 5:
            statement = args[2]
            parameters = args[3]
            context = args[4]

            duration = time.perf_counter() - getattr(
                context, "_query_start_time", time.perf_counter()
            )
            sql_clean = statement.strip().replace("\n", " ").replace("  ", " ")

            logger.info(
                "[SQL] Query executed in %.4f seconds | SQL: %s | Params: %s",
                duration,
                sql_clean,
                parameters,
            )
