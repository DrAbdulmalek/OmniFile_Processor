"""Provider health scoring — tracks request outcomes and computes live scores.

Each provider's health is continuously evaluated based on recent success rate,
latency distribution, error-type breakdowns, and failure streaks.  Scores
range from 0.0 (completely unhealthy) to 1.0 (perfect).
"""

from __future__ import annotations

import math
import os
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Configuration helpers
# ---------------------------------------------------------------------------

def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except (ValueError, TypeError):
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, str(default)))
    except (ValueError, TypeError):
        return default


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class HealthStats:
    """Snapshot of a provider's health metrics."""

    provider_id: str
    model_name: str
    total_requests: int = 0
    success_count: int = 0
    error_counts: dict[str, int] = field(default_factory=dict)
    avg_latency_ms: float = 0.0
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    last_error_time: float = 0.0
    last_success_time: float = 0.0
    health_score: float = 1.0
    consecutive_failures: int = 0


@dataclass
class _RequestRecord:
    """Single recorded request outcome."""

    timestamp: float
    latency_ms: float
    success: bool
    error_type: str | None
    tokens_used: int


# ---------------------------------------------------------------------------
# Health scorer
# ---------------------------------------------------------------------------

class ProviderHealthScorer:
    """Track per-provider request outcomes and compute health scores.

    The scoring formula is::

        score = w_success * success_rate
             + w_latency * (1 - normalised_latency)
             + w_recency * recency_bonus
             - streak_penalty

    where:
    * *success_rate* is the weighted recent success ratio (more recent
      requests count more).
    * *normalised_latency* is the average latency scaled to [0, 1] using a
      sigmoid-like function anchored at 10 000 ms.
    * *recency_bonus* rewards providers that have been used recently (decays
      exponentially).
    * *streak_penalty* penalises consecutive failure streaks.

    Example::

        scorer = ProviderHealthScorer()
        scorer.record_request("open_router", "gpt-4o", 230, True)
        score = scorer.get_health_score("open_router")
        # -> 1.0 (single successful request)
    """

    def __init__(
        self,
        window: int | None = None,
        success_weight: float | None = None,
        latency_weight: float | None = None,
        recency_weight: float | None = None,
    ) -> None:
        self._window: int = (
            window if window is not None else _env_int("HEALTH_SCORE_WINDOW", 100)
        )
        self._success_weight: float = (
            success_weight
            if success_weight is not None
            else _env_float("HEALTH_SCORE_SUCCESS_WEIGHT", 0.5)
        )
        self._latency_weight: float = (
            latency_weight
            if latency_weight is not None
            else _env_float("HEALTH_SCORE_LATENCY_WEIGHT", 0.3)
        )
        self._recency_weight: float = (
            recency_weight
            if recency_weight is not None
            else _env_float("HEALTH_SCORE_RECENCY_WEIGHT", 0.2)
        )

        # Per-provider request history.
        self._history: dict[str, list[_RequestRecord]] = defaultdict(list)
        # Per-(provider, model) request history.
        self._model_history: dict[str, list[_RequestRecord]] = defaultdict(list)

        # Known error types for structured counting.
        self._known_error_types = frozenset({
            "rate_limit", "timeout", "server_error", "auth_error", "generic",
        })

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record_request(
        self,
        provider_id: str,
        model_name: str,
        latency_ms: float,
        success: bool,
        error_type: str | None = None,
        tokens_used: int = 0,
    ) -> None:
        """Record the outcome of a single request."""
        now = time.monotonic()
        record = _RequestRecord(
            timestamp=now,
            latency_ms=latency_ms,
            success=success,
            error_type=self._normalise_error_type(error_type),
            tokens_used=tokens_used,
        )
        provider_history = self._history[provider_id]
        provider_history.append(record)
        if len(provider_history) > self._window:
            self._history[provider_id] = provider_history[-self._window:]

        model_key = f"{provider_id}::{model_name}"
        model_hist = self._model_history[model_key]
        model_hist.append(record)
        if len(model_hist) > self._window:
            self._model_history[model_key] = model_hist[-self._window:]

    def get_health_score(
        self, provider_id: str, model_name: str | None = None
    ) -> float:
        """Compute a 0.0–1.0 health score for *provider_id* (optionally
        scoped to *model_name*)."""
        records = self._get_records(provider_id, model_name)
        if not records:
            return 1.0  # No data → assume healthy.

        return self._compute_score(records)

    def get_provider_ranking(
        self, model_name: str | None = None
    ) -> list[tuple[str, float]]:
        """Return all providers sorted by health score (descending)."""
        rankings: list[tuple[str, float]] = []
        for provider_id in self._history:
            score = self.get_health_score(provider_id, model_name)
            rankings.append((provider_id, score))
        rankings.sort(key=lambda item: item[1], reverse=True)
        return rankings

    def get_provider_stats(
        self, provider_id: str, model_name: str | None = None
    ) -> HealthStats:
        """Return a detailed stats snapshot for a provider."""
        records = self._get_records(provider_id, model_name)
        if not records:
            return HealthStats(
                provider_id=provider_id,
                model_name=model_name or "*",
            )

        success_count = sum(1 for r in records if r.success)
        error_counts: dict[str, int] = defaultdict(int)
        for r in records:
            if not r.success:
                et = r.error_type or "generic"
                error_counts[et] += 1

        latencies = [r.latency_ms for r in records if r.latency_ms > 0]
        avg_lat = sum(latencies) / len(latencies) if latencies else 0.0
        sorted_lat = sorted(latencies)
        p50 = self._percentile(sorted_lat, 50)
        p95 = self._percentile(sorted_lat, 95)

        last_err = 0.0
        last_ok = 0.0
        for r in reversed(records):
            if last_err == 0.0 and not r.success:
                last_err = r.timestamp
            if last_ok == 0.0 and r.success:
                last_ok = r.timestamp
            if last_err and last_ok:
                break

        consecutive = 0
        for r in reversed(records):
            if r.success:
                break
            consecutive += 1

        score = self._compute_score(records)

        return HealthStats(
            provider_id=provider_id,
            model_name=model_name or "*",
            total_requests=len(records),
            success_count=success_count,
            error_counts=dict(error_counts),
            avg_latency_ms=round(avg_lat, 2),
            p50_latency_ms=round(p50, 2),
            p95_latency_ms=round(p95, 2),
            last_error_time=last_err,
            last_success_time=last_ok,
            health_score=round(score, 4),
            consecutive_failures=consecutive,
        )

    def is_healthy(
        self, provider_id: str, threshold: float | None = None, model_name: str | None = None
    ) -> bool:
        """Quick boolean health check."""
        if threshold is None:
            threshold = _env_float("HEALTH_UNHEALTHY_THRESHOLD", 0.5)
        return self.get_health_score(provider_id, model_name) >= threshold

    # ------------------------------------------------------------------
    # Scoring internals
    # ------------------------------------------------------------------

    def _compute_score(self, records: list[_RequestRecord]) -> float:
        """Apply the health scoring formula."""
        n = len(records)
        if n == 0:
            return 1.0

        # --- Success rate (recency-weighted) ---
        # More recent requests get exponentially more weight.
        now = time.monotonic()
        weights: list[float] = []
        for r in records:
            age = now - r.timestamp
            # Half-life of 60 seconds.
            w = math.exp(-age / 60.0)
            weights.append(w)

        total_weight = sum(weights)
        if total_weight == 0:
            return 0.5  # Indeterminate.

        weighted_success = sum(w * (1.0 if r.success else 0.0) for w, r in zip(weights, records, strict=True))
        success_rate = weighted_success / total_weight

        # --- Normalised latency ---
        latencies = [r.latency_ms for r in records if r.latency_ms > 0]
        if latencies:
            avg_latency = sum(latencies) / len(latencies)
            # Sigmoid-like normalisation: at 10000 ms → ~0.73, at 2000 ms → ~0.18
            normalised_latency = 1.0 - math.exp(-avg_latency / 10000.0)
        else:
            normalised_latency = 0.5

        # --- Recency bonus ---
        # Full bonus if the most recent request was within the last 60s.
        most_recent_age = now - records[-1].timestamp
        recency_bonus = math.exp(-most_recent_age / 120.0)

        # --- Streak penalty ---
        consecutive = 0
        for r in reversed(records):
            if r.success:
                break
            consecutive += 1
        streak_penalty = min(consecutive * 0.1, 0.5)

        # --- Combine ---
        score = (
            self._success_weight * success_rate
            + self._latency_weight * (1.0 - normalised_latency)
            + self._recency_weight * recency_bonus
            - streak_penalty
        )
        return max(0.0, min(1.0, score))

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------

    def _get_records(
        self, provider_id: str, model_name: str | None
    ) -> list[_RequestRecord]:
        if model_name is not None:
            key = f"{provider_id}::{model_name}"
            return list(self._model_history.get(key, []))
        return list(self._history.get(provider_id, []))

    @staticmethod
    def _normalise_error_type(error_type: str | None) -> str | None:
        if error_type is None:
            return None
        mapping = {
            "rate_limit": "rate_limit",
            "rate-limit": "rate_limit",
            "ratelimit": "rate_limit",
            "rate-limit-exceeded": "rate_limit",
            "429": "rate_limit",
            "timeout": "timeout",
            "timed_out": "timeout",
            "timedout": "timeout",
            "504": "timeout",
            "gateway_timeout": "timeout",
            "server_error": "server_error",
            "500": "server_error",
            "502": "server_error",
            "503": "server_error",
            "auth_error": "auth_error",
            "401": "auth_error",
            "403": "auth_error",
            "authentication": "auth_error",
            "forbidden": "auth_error",
        }
        return mapping.get(error_type.lower().strip(), "generic")

    @staticmethod
    def _percentile(sorted_values: list[float], pct: float) -> float:
        if not sorted_values:
            return 0.0
        k = (len(sorted_values) - 1) * (pct / 100.0)
        lower = int(math.floor(k))
        upper = int(math.ceil(k))
        if lower == upper:
            return sorted_values[lower]
        fraction = k - lower
        return sorted_values[lower] * (1.0 - fraction) + sorted_values[upper] * fraction
