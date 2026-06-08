"""Process entrypoint."""

from __future__ import annotations

import logging
import sys

from specvsreality_worker.agents.pydantic_ai_verbose import configure_verbose_loggers
from specvsreality_worker.bootstrap import create_queue_consumer
from specvsreality_worker.config import get_settings
from specvsreality_worker.observability import (
    init_worker_observability,
    shutdown_worker_observability,
)


def main() -> None:
    settings = get_settings()
    log_level = settings.worker_log_level.strip().upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stderr,
    )
    log = logging.getLogger(__name__)
    configure_verbose_loggers(settings)
    init_worker_observability(settings)
    consumer = create_queue_consumer(settings=settings)
    try:
        consumer.run()
    except KeyboardInterrupt:
        log.info("interrupted; stopping")
    finally:
        consumer.stop()
        shutdown_worker_observability()


if __name__ == "__main__":
    main()
