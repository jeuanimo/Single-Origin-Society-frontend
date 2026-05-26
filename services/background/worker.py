from concurrent.futures import ThreadPoolExecutor
import logging

logger = logging.getLogger(__name__)
_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="sos-bg")


def enqueue(func, *args, **kwargs):
    def _runner():
        try:
            return func(*args, **kwargs)
        except Exception:
            logger.exception("Background task failed")
            return None

    return _executor.submit(_runner)
