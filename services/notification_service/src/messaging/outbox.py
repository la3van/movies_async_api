"""Совместимое имя процесса публикации outbox."""

import asyncio

from core.runtime import supervise

from messaging.relay import publish_one, run

__all__ = ["publish_one", "run"]
if __name__ == "__main__":
    asyncio.run(supervise(run))
