from __future__ import annotations


class MemoryCache:
    def __init__(self) -> None:
        self._data: dict[str, dict[str, object]] = {}

    def get_bucket(self, key: str) -> dict[str, object]:
        bucket_key = str(key or "default")
        if bucket_key not in self._data:
            self._data[bucket_key] = {}
        return self._data[bucket_key]
