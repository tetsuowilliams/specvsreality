"""Process entrypoint."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from specvsreality_worker.bootstrap import create_queue_consumer
from specvsreality_worker.agents.pydantic_ai_verbose import configure_verbose_loggers
from specvsreality_worker.observability import (
    init_worker_observability,
    shutdown_worker_observability,
)


def _load_worker_dotenv() -> None:
    """Put ``worker/.env`` keys into ``os.environ`` before observability reads them.

    ``WorkerSettings`` only merges dotenv into RabbitMQ fields; it does not export
    arbitrary keys like ``OPIK_URL_OVERRIDE`` to the process environment.
    """
    here = Path(__file__).resolve()
    for candidate in (here.parents[2] / ".env", Path.cwd() / ".env"):
        if candidate.is_file():
            load_dotenv(candidate, override=False)
            return


def main() -> None:
    _load_worker_dotenv()
    log_level = os.environ.get("WORKER_LOG_LEVEL", "INFO").strip().upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stderr,
    )
    log = logging.getLogger(__name__)
    configure_verbose_loggers()
    init_worker_observability()
    consumer = create_queue_consumer()
    try:
        consumer.run()
    except KeyboardInterrupt:
        log.info("interrupted; stopping")
    finally:
        consumer.stop()
        shutdown_worker_observability()


if __name__ == "__main__":
    main()
