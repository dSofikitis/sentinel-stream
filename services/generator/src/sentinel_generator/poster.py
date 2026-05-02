from __future__ import annotations

import logging
from typing import Iterable

import httpx

logger = logging.getLogger(__name__)


class Poster:
    """Posts events to the ingest service. Caller controls batching and pacing."""

    def __init__(self, target: str, timeout_s: float = 5.0) -> None:
        self._target = target
        self._client = httpx.Client(timeout=timeout_s)
        self._sent = 0
        self._failed = 0

    def post(self, event: dict) -> bool:
        try:
            response = self._client.post(self._target, json=event)
        except httpx.HTTPError as exc:
            logger.warning("post_failed", extra={"error": str(exc)})
            self._failed += 1
            return False
        if response.status_code >= 400:
            logger.warning(
                "post_rejected",
                extra={"status": response.status_code, "body": response.text[:200]},
            )
            self._failed += 1
            return False
        self._sent += 1
        return True

    def post_many(self, events: Iterable[dict]) -> tuple[int, int]:
        for event in events:
            self.post(event)
        return self._sent, self._failed

    @property
    def sent(self) -> int:
        return self._sent

    @property
    def failed(self) -> int:
        return self._failed

    def close(self) -> None:
        self._client.close()
