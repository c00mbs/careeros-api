"""Search the public Himalayas remote-jobs feed with a short server cache."""

from __future__ import annotations

from threading import Lock
from time import monotonic
from typing import Any

import httpx

JOBS_API_URL = "https://himalayas.app/jobs/api/search"
CACHE_TTL_SECONDS = 900
_cache: dict[tuple[tuple[str, str], ...], tuple[float, dict[str, Any]]] = {}
_cache_lock = Lock()


class JobProviderError(RuntimeError):
    """The upstream job listing provider could not return valid results."""


def clear_job_cache() -> None:
    """Clear cached job searches. Used by tests and local development."""
    with _cache_lock:
        _cache.clear()


def search_remote_jobs(params: dict[str, str]) -> dict[str, Any]:
    key = tuple(sorted(params.items()))
    now = monotonic()
    with _cache_lock:
        cached = _cache.get(key)
        if cached and now - cached[0] < CACHE_TTL_SECONDS:
            return cached[1]

    try:
        response = httpx.get(JOBS_API_URL, params=params, timeout=12.0, follow_redirects=True)
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise JobProviderError("Live remote job listings are temporarily unavailable. Please try again shortly.") from exc

    if not isinstance(data, dict) or not isinstance(data.get("jobs", []), list):
        raise JobProviderError("The remote job provider returned an unexpected response.")

    result = {
        "source": "Himalayas",
        "source_url": "https://himalayas.app/jobs",
        "updated_at": data.get("updatedAt"),
        "total_count": int(data.get("totalCount", 0) or 0),
        "page": int(data.get("page", params.get("page", "1")) or 1),
        "jobs": data.get("jobs", []),
    }
    with _cache_lock:
        _cache[key] = (now, result)
        if len(_cache) > 256:
            oldest_key = min(_cache, key=lambda entry: _cache[entry][0])
            _cache.pop(oldest_key, None)
    return result

