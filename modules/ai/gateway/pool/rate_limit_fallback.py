"""Smart rate-limit fallback — automatically selects lower-effort model alternatives.

When a model hits a rate limit, this module locates a cheaper or lower-tier
variant (same provider first, then cross-provider) so that requests can
continue without manual intervention.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_TIER_OVERRIDES: dict[str, str] | None = None


def _load_tier_overrides() -> dict[str, str]:
    global _TIER_OVERRIDES
    if _TIER_OVERRIDES is not None:
        return _TIER_OVERRIDES
    raw = os.environ.get("MODEL_TIER_OVERRIDES", "")
    if raw.strip():
        try:
            _TIER_OVERRIDES = json.loads(raw)
        except json.JSONDecodeError:
            _TIER_OVERRIDES = {}
    else:
        _TIER_OVERRIDES = {}
    return _TIER_OVERRIDES


# ---------------------------------------------------------------------------
# Enums & data classes
# ---------------------------------------------------------------------------

class EffortTier(IntEnum):
    """Ordered effort tiers — higher value means more expensive / capable."""

    LOW = 0
    MEDIUM = 1
    HIGH = 2
    XHIGH = 3
    MAX = 4


@dataclass
class ModelTierConfig:
    """Maps a specific model to its effort tier and cost."""

    model_name: str
    tier: EffortTier
    cost_multiplier: float = 1.0
    provider_id: str = ""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_SUFFIX_TO_TIER: dict[str, EffortTier] = {
    "-low": EffortTier.LOW,
    "-medium": EffortTier.MEDIUM,
    "-high": EffortTier.HIGH,
    "-xhigh": EffortTier.XHIGH,
    "-max": EffortTier.MAX,
}

_THINKING_SUFFIXES = ("-thinking", "-extended", "-reasoning")


def _infer_tier(model_name: str) -> EffortTier | None:
    """Guess the effort tier from common naming conventions.

    * Models whose name ends with ``-low``, ``-medium``, etc. get mapped
      directly.
    * ``-thinking`` / ``-extended`` / ``-reasoning`` variants are treated as
      one tier higher than their non-thinking counterpart.
    * Explicit overrides from ``MODEL_TIER_OVERRIDES`` take precedence.
    """
    overrides = _load_tier_overrides()
    if model_name in overrides:
        raw = overrides[model_name].upper()
        try:
            return EffortTier[raw]
        except KeyError:
            pass

    name_lower = model_name.lower()

    # Check for thinking suffix — bump tier by one.
    thinking = False
    for suffix in _THINKING_SUFFIXES:
        if name_lower.endswith(suffix):
            name_lower = name_lower[: -len(suffix)]
            thinking = True
            break

    for suffix, tier in _SUFFIX_TO_TIER.items():
        if name_lower.endswith(suffix):
            if thinking:
                bumped = tier + 1
                if bumped <= EffortTier.MAX:
                    return EffortTier(bumped)
                return EffortTier.MAX
            return tier

    return None


# ---------------------------------------------------------------------------
# Rate-limit event
# ---------------------------------------------------------------------------

@dataclass
class _RateLimitEvent:
    provider_id: str
    model_name: str
    expires_at: float


# ---------------------------------------------------------------------------
# Fallback manager
# ---------------------------------------------------------------------------

class RateLimitFallbackManager:
    """Pick fallback models when the primary choice is rate-limited.

    Example::

        mgr = RateLimitFallbackManager()
        mgr.register_model_tier("gpt-4o", EffortTier.HIGH, cost_multiplier=2.0)
        mgr.register_model_tier("gpt-4o-mini", EffortTier.MEDIUM, cost_multiplier=1.0)
        fallback = mgr.pick_fallback_model("gpt-4o")
        # -> ModelTierConfig(model_name="gpt-4o-mini", tier=<EffortTier.MEDIUM>, …)
    """

    def __init__(self) -> None:
        self._registry: dict[str, ModelTierConfig] = {}
        self._rate_limited: dict[str, list[_RateLimitEvent]] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register_model_tier(
        self,
        model_name: str,
        tier: EffortTier,
        cost_multiplier: float = 1.0,
        provider_id: str = "",
    ) -> ModelTierConfig:
        """Register a model with its effort tier and optional provider."""
        config = ModelTierConfig(
            model_name=model_name,
            tier=tier,
            cost_multiplier=cost_multiplier,
            provider_id=provider_id,
        )
        self._registry[model_name] = config
        return config

    def register_auto_detected(
        self, model_name: str, provider_id: str = "", cost_multiplier: float = 1.0
    ) -> ModelTierConfig | None:
        """Attempt to register a model using automatic tier inference."""
        tier = _infer_tier(model_name)
        if tier is None:
            return None
        return self.register_model_tier(model_name, tier, cost_multiplier, provider_id)

    # ------------------------------------------------------------------
    # Fallback selection
    # ------------------------------------------------------------------

    def pick_fallback_model(
        self, model_name: str, provider_id: str | None = None
    ) -> ModelTierConfig | None:
        """Find the best lower-effort alternative to *model_name*.

        Strategy:
        1. Same provider, same tier family but lower tier.
        2. Same provider, any lower tier.
        3. Cross-provider, same tier family but lower tier.
        4. Cross-provider, any lower tier.
        """
        primary = self._registry.get(model_name)
        if primary is None:
            inferred = _infer_tier(model_name)
            if inferred is None:
                return None
            primary = ModelTierConfig(
                model_name=model_name,
                tier=inferred,
                provider_id=provider_id or "",
            )

        target_provider = primary.provider_id or (provider_id or "")
        primary_tier: int = primary.tier  # type: ignore[assignment]

        # Collect all candidates strictly lower than the primary tier.
        candidates: list[ModelTierConfig] = [
            cfg
            for cfg in self._registry.values()
            if cfg.model_name != model_name
            and cfg.tier < primary_tier
            and not self._is_rate_limited(cfg.model_name, cfg.provider_id)
        ]

        if not candidates:
            return None

        # Phase 1 — same provider, same tier family (closest tier).
        same_provider = [c for c in candidates if c.provider_id == target_provider]
        if same_provider:
            same_provider.sort(key=lambda c: c.tier, reverse=True)
            return same_provider[0]

        # Phase 2 — cross-provider, closest tier, lowest cost.
        candidates.sort(key=lambda c: (-c.tier, c.cost_multiplier))
        return candidates[0]

    # ------------------------------------------------------------------
    # Rate-limit tracking
    # ------------------------------------------------------------------

    def report_rate_limit(
        self,
        model_name: str,
        provider_id: str = "",
        reset_after_seconds: float = 60.0,
    ) -> None:
        """Record that *model_name* on *provider_id* is currently rate-limited."""
        event = _RateLimitEvent(
            provider_id=provider_id,
            model_name=model_name,
            expires_at=time.monotonic() + reset_after_seconds,
        )
        self._rate_limited.setdefault(model_name, []).append(event)

    def get_rate_limit_stats(self) -> dict[str, Any]:
        """Return which models are currently limited and when they will reset."""
        now = time.monotonic()
        active: list[dict[str, Any]] = []
        for model_name, events in self._rate_limited.items():
            # Prune expired events.
            remaining = [
                e
                for e in events
                if e.expires_at > now
            ]
            if remaining:
                soonest = min(e.expires_at for e in remaining)
                active.append({
                    "model_name": model_name,
                    "provider_id": remaining[0].provider_id,
                    "resets_in_seconds": round(soonest - now, 1),
                })
            else:
                del self._rate_limited[model_name]

        return {
            "rate_limited_models": active,
            "total_tracked": len(active),
        }

    def get_all_tiers(self) -> dict[str, dict[str, Any]]:
        """Return all registered model→tier mappings."""
        return {
            name: {
                "tier": cfg.tier.name,
                "cost_multiplier": cfg.cost_multiplier,
                "provider_id": cfg.provider_id,
            }
            for name, cfg in self._registry.items()
        }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _is_rate_limited(self, model_name: str, provider_id: str) -> bool:
        now = time.monotonic()
        events = self._rate_limited.get(model_name, [])
        active = [e for e in events if e.expires_at > now]
        if not active:
            self._rate_limited.pop(model_name, None)
            return False
        return any(e.provider_id == provider_id for e in active)
