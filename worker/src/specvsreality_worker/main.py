"""Process entrypoint."""

from __future__ import annotations

import logging
import sys

from specvsreality_worker.bootstrap import create_queue_consumer


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stderr,
    )
    log = logging.getLogger(__name__)
    consumer = create_queue_consumer()
    try:
        consumer.run()
    except KeyboardInterrupt:
        log.info("interrupted; stopping")
    finally:
        consumer.stop()


if __name__ == "__main__":
    main()
