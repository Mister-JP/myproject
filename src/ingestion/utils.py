from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass
from threading import Lock
from typing import Any, Dict, Optional

import requests


def normalize_license(raw: Optional[str]) -> Optional[str]:
    """Normalize common open licenses to a stable token.

    Returns lowercase simplified identifiers such as:
    - cc-by, cc-by-sa, cc0, public-domain
    Falls back to the lowercased string if unknown.
    """
    if not raw:
        return None
    s = raw.strip().lower()
    cc_map: Dict[str, str] = {
        "cc-by": "cc-by",
        "cc by": "cc-by",
        "creative commons attribution": "cc-by",
        "cc-by-sa": "cc-by-sa",
        "cc by-sa": "cc-by-sa",
        "cc0": "cc0",
        "public domain": "public-domain",
    }
    for k, v in cc_map.items():
        if k in s:
            return v
    return s


def license_permits_pdf_storage(normalized_license: Optional[str]) -> bool:
    if not normalized_license:
        return False
    return normalized_license.startswith(("cc-", "cc0", "public-domain"))


def rate_limit_sleep(seconds: float) -> None:
    if seconds and seconds > 0:
        time.sleep(seconds)


class PerSourceRateLimiter:
    """Simple in-process, per-source rate limiter based on minimum interval between calls.

    Not a hard guarantee under concurrency, but adequate for CLI/worker usage.
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self._last_call_epoch_seconds: Dict[str, float] = {}

    def throttle(self, source_name: str, min_interval_seconds: float) -> None:
        if not source_name or min_interval_seconds <= 0:
            return
        with self._lock:
            now = time.monotonic()
            last = self._last_call_epoch_seconds.get(source_name, 0.0)
            sleep_for = (last + min_interval_seconds) - now
            if sleep_for > 0:
                time.sleep(sleep_for)
            # record call time after sleeping to be conservative
            self._last_call_epoch_seconds[source_name] = time.monotonic()


global_rate_limiter = PerSourceRateLimiter()


def http_get_json(
    url: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    timeout_seconds: int = 30,
    source_name: Optional[str] = None,
    min_interval_seconds: float = 0.0,
) -> Dict[str, Any]:
    """HTTP GET returning JSON with optional per-source throttling.

    Intended for connector APIs that do not require streaming.
    """
    if source_name and min_interval_seconds:
        global_rate_limiter.throttle(source_name, min_interval_seconds)
    r = requests.get(url, params=params, timeout=timeout_seconds)
    r.raise_for_status()
    data = r.json() or {}
    if not isinstance(data, dict):
        # normalize non-dict JSON to dict for caller simplicity
        return {"data": data}
    return data


@dataclass
class TelemetryCounters:
    ingested: int = 0
    skipped: int = 0
    errors: int = 0


@contextmanager
def telemetry_span(name: str, counters: Optional[TelemetryCounters] = None):  # pragma: no cover - trivial
    start = time.time()
    try:
        yield
    finally:
        duration_ms = int((time.time() - start) * 1000)
        # Simple stdout tracing; could be swapped for OpenTelemetry later
        msg = f"telemetry span name={name} duration_ms={duration_ms}"
        if counters is not None:
            msg += f" ingested={counters.ingested} skipped={counters.skipped} errors={counters.errors}"
        print(msg)


