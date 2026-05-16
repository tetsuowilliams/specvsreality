"""Process entrypoint."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

from specvsreality_worker.bootstrap import create_queue_consumer
from specvsreality_worker.observability import init_worker_observability


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
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stderr,
    )
    log = logging.getLogger(__name__)
    _load_worker_dotenv()
    init_worker_observability()
    consumer = create_queue_consumer()
    try:
        consumer.run()
    except KeyboardInterrupt:
        log.info("interrupted; stopping")
    finally:
        consumer.stop()


if __name__ == "__main__":
    main()
