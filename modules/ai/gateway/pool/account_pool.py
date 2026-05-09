"""Account pool manager with automatic rotation, rate-limit distribution, and failover.

Manages a pool of provider accounts and selects the best available one based on
priority, least-recently-used ordering, concurrent request caps, and rate-limit
state.  Accounts that accumulate consecutive failures are temporarily banned.
"""

from __future__ import annotations

import os
import random
import time
from dataclasses import dataclass, field
from enum import Enum
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


def _env_bool(name: str, default: bool) -> bool:
    val = os.environ.get(name, str(default)).lower()
    return val in ("true", "1", "yes", "on")


# ---------------------------------------------------------------------------
# Enums & data classes
# ---------------------------------------------------------------------------

class AccountSelectionStrategy(Enum):
    """Strategy used by the account pool when picking the next account."""

    PRIORITY = "priority"
    ROUND_ROBIN = "round_robin"
    LEAST_RECENTLY_USED = "least_recently_used"
    WEIGHTED_RANDOM = "weighted_random"


@dataclass
class AccountState:
    """Mutable runtime state for a single account in the pool."""

    account_id: str
    provider_id: str
    api_key: str
    base_url: str
    tier: str = "free"
    max_concurrent: int = 1
    current_concurrent: int = 0
    rate_limit_per_minute: int = 10
    priority: int = 0
    last_used: float = 0.0
    total_requests: int = 0
    total_failures: int = 0
    consecutive_failures: int = 0
    rate_limited_until: float = 0.0
    is_banned: bool = False

    # Per-minute rate-limit tracking: monotonic timestamps of recent requests.
    _request_timestamps: list[float] = field(default_factory=list, repr=False)

    # Optional set of model names this account is optimised for.
    model_affinity: set[str] = field(default_factory=set)

    # Round-robin counter (used only by ROUND_ROBIN strategy).
    _rr_counter: int = field(default=0, repr=False)

    # ---- helpers ----

    def is_available(self, now: float) -> bool:
        """Return *True* if the account can accept a new request right now."""
        if self.is_banned:
            return False
        if self.rate_limited_until > now:
            return False
        if self.current_concurrent >= self.max_concurrent:
            return False
        return True

    def touches_rate_limit(self, now: float) -> bool:
        """Return *True* if the account is at its per-minute cap."""
        cutoff = now - 60.0
        self._request_timestamps = [
            ts for ts in self._request_timestamps if ts > cutoff
        ]
        return len(self._request_timestamps) >= self.rate_limit_per_minute

    def record_request(self, now: float) -> None:
        self._request_timestamps.append(now)
        # Keep the list bounded.
        if len(self._request_timestamps) > self.rate_limit_per_minute * 2:
            cutoff = now - 60.0
            self._request_timestamps = [
                ts for ts in self._request_timestamps if ts > cutoff
            ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "account_id": self.account_id,
            "provider_id": self.provider_id,
            "tier": self.tier,
            "max_concurrent": self.max_concurrent,
            "current_concurrent": self.current_concurrent,
            "rate_limit_per_minute": self.rate_limit_per_minute,
            "priority": self.priority,
            "last_used": self.last_used,
            "total_requests": self.total_requests,
            "total_failures": self.total_failures,
            "consecutive_failures": self.consecutive_failures,
            "rate_limited_until": self.rate_limited_until,
            "is_banned": self.is_banned,
            "model_affinity": sorted(self.model_affinity),
        }


# ---------------------------------------------------------------------------
# Account pool
# ---------------------------------------------------------------------------

class AccountPool:
    """Thread-safe (asyncio-safe) pool of provider accounts.

    Usage::

        pool = AccountPool()
        pool.add_account("acc-1", "open_router", "sk-…", "https://…")
        account = pool.get_next_account()
        # ... make request ...
        pool.report_success(account.account_id)
    """

    def __init__(
        self,
        strategy: AccountSelectionStrategy | None = None,
        max_consecutive_failures: int | None = None,
        ban_duration_seconds: float | None = None,
        enabled: bool | None = None,
    ) -> None:
        raw_strategy = os.environ.get("ACCOUNT_POOL_STRATEGY", "least_recently_used")
        self._strategy: AccountSelectionStrategy = strategy or AccountSelectionStrategy(
            raw_strategy.strip().lower()
        )
        self._max_consecutive_failures: int = (
            max_consecutive_failures
            if max_consecutive_failures is not None
            else _env_int("ACCOUNT_MAX_CONSECUTIVE_FAILURES", 5)
        )
        self._ban_duration_seconds: float = (
            ban_duration_seconds
            if ban_duration_seconds is not None
            else _env_float("ACCOUNT_BAN_DURATION_SECONDS", 300)
        )
        self._enabled: bool = (
            enabled if enabled is not None else _env_bool("ACCOUNT_POOL_ENABLED", True)
        )
        self._accounts: dict[str, AccountState] = {}
        self._global_rr_counter: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def enabled(self) -> bool:
        return self._enabled

    def add_account(
        self,
        account_id: str,
        provider_id: str,
        api_key: str,
        base_url: str,
        tier: str = "free",
        max_concurrent: int = 1,
        rate_limit_per_minute: int = 10,
        priority: int = 0,
        model_affinity: set[str] | None = None,
    ) -> AccountState:
        """Register a new account (or update an existing one)."""
        state = AccountState(
            account_id=account_id,
            provider_id=provider_id,
            api_key=api_key,
            base_url=base_url,
            tier=tier,
            max_concurrent=max_concurrent,
            rate_limit_per_minute=rate_limit_per_minute,
            priority=priority,
            model_affinity=model_affinity or set(),
        )
        self._accounts[account_id] = state
        return state

    def remove_account(self, account_id: str) -> bool:
        """Remove an account from the pool.  Returns *True* if it existed."""
        return self._accounts.pop(account_id, None) is not None

    def get_next_account(
        self,
        provider_id: str | None = None,
        model_name: str | None = None,
    ) -> AccountState | None:
        """Select the best available account.

        Selection criteria depend on the configured *strategy* and always
        respect availability (not banned, not rate-limited, under concurrency
        cap).
        """
        if not self._enabled:
            return self._first_match(provider_id)

        now = time.monotonic()
        candidates = [
            acct
            for acct in self._accounts.values()
            if acct.is_available(now)
            and not acct.touches_rate_limit(now)
            and (provider_id is None or acct.provider_id == provider_id)
        ]

        if not candidates:
            return None

        if model_name is not None:
            affinity_matches = [
                a for a in candidates if model_name in a.model_affinity
            ]
            if affinity_matches:
                candidates = affinity_matches

        if self._strategy == AccountSelectionStrategy.PRIORITY:
            candidates.sort(key=lambda a: a.priority, reverse=True)
            return candidates[0]

        if self._strategy == AccountSelectionStrategy.ROUND_ROBIN:
            candidates.sort(key=lambda a: a.account_id)
            idx = self._global_rr_counter % len(candidates)
            self._global_rr_counter += 1
            selected = candidates[idx]
            selected.last_used = now
            selected.total_requests += 1
            selected.record_request(now)
            return selected

        if self._strategy == AccountSelectionStrategy.WEIGHTED_RANDOM:
            weights = [1.0 / (1 + a.consecutive_failures) for a in candidates]
            total = sum(weights)
            if total == 0:
                return candidates[0]
            r = random.random() * total
            cumulative = 0.0
            for acct, w in zip(candidates, weights, strict=True):
                cumulative += w
                if r <= cumulative:
                    acct.last_used = now
                    acct.total_requests += 1
                    acct.record_request(now)
                    return acct
            selected = candidates[-1]
            selected.last_used = now
            selected.total_requests += 1
            selected.record_request(now)
            return selected

        # Default: LEAST_RECENTLY_USED
        candidates.sort(key=lambda a: a.last_used)
        selected = candidates[0]
        selected.last_used = now
        selected.total_requests += 1
        selected.record_request(now)
        return selected

    def report_success(self, account_id: str) -> None:
        """Reset failure counters after a successful request."""
        acct = self._accounts.get(account_id)
        if acct is None:
            return
        acct.consecutive_failures = 0
        if acct.current_concurrent > 0:
            acct.current_concurrent -= 1

    def report_failure(self, account_id: str, error_type: str = "generic") -> None:
        """Track a failure; auto-ban after *N* consecutive failures."""
        acct = self._accounts.get(account_id)
        if acct is None:
            return
        acct.total_failures += 1
        acct.consecutive_failures += 1
        if acct.current_concurrent > 0:
            acct.current_concurrent -= 1

        if acct.consecutive_failures >= self._max_consecutive_failures:
            acct.is_banned = True
            acct.rate_limited_until = time.monotonic() + self._ban_duration_seconds

    def report_rate_limited(
        self, account_id: str, reset_after_seconds: float = 60
    ) -> None:
        """Mark an account as rate-limited until *reset_after_seconds* from now."""
        acct = self._accounts.get(account_id)
        if acct is None:
            return
        acct.rate_limited_until = time.monotonic() + reset_after_seconds

    def get_pool_stats(self) -> dict[str, Any]:
        """Return aggregate statistics for every account in the pool."""
        accounts = [acct.to_dict() for acct in self._accounts.values()]
        healthy = sum(1 for a in accounts if not a["is_banned"])
        return {
            "strategy": self._strategy.value,
            "enabled": self._enabled,
            "total_accounts": len(accounts),
            "healthy_accounts": healthy,
            "accounts": accounts,
        }

    def get_healthy_accounts(
        self, provider_id: str | None = None
    ) -> list[AccountState]:
        """Return only currently available (non-banned, non-rate-limited) accounts."""
        now = time.monotonic()
        return [
            acct
            for acct in self._accounts.values()
            if acct.is_available(now)
            and (provider_id is None or acct.provider_id == provider_id)
        ]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _first_match(
        self, provider_id: str | None
    ) -> AccountState | None:
        for acct in self._accounts.values():
            if provider_id is None or acct.provider_id == provider_id:
                return acct
        return None
