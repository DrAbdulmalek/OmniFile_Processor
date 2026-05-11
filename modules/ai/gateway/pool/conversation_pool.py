"""Conversation reuse pool — fingerprints and caches conversation context.

Provides stable hashing of conversation state (normalising dynamic tokens
like timestamps, UUIDs, and working directories) so that equivalent
conversations map to the same cache key.  A check-in / check-out interface
prevents concurrent reuse of the same context.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from collections import OrderedDict
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
# Normalisation patterns
# ---------------------------------------------------------------------------

# ISO timestamps:  2025-01-15T14:32:00+00:00
_RE_ISO_TS = re.compile(
    r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(\.\d+)?([+-]\d{2}:?\d{2}|Z)?"
)

# Date-only patterns:  2025-01-15 or Jan 15, 2025
_RE_DATE = re.compile(
    r"\d{4}-\d{2}-\d{2}"
)

# UUIDs
_RE_UUID = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)

# Working directory paths (Unix or Windows)
_RE_CWD = re.compile(r"(?:/home/\S+?|/Users/\S+?|[A-Z]:\\[^\s\"\\]+?)(?=[/\\]?\s|[/\\]?\"|$)")

# Git short hashes (7-9 hex chars)
_RE_GITSHA = re.compile(r"(?<![0-9a-fA-F])[0-9a-fA-F]{7,9}(?![0-9a-fA-F])")

# Meta XML/HTML tags (self-closing or paired)
_RE_META_TAG = re.compile(r"<meta\b[^>]*/?>|</meta\s*>", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ConversationContext:
    """A saved conversation context entry."""

    cascade_id: str
    session_id: str
    provider_key: str
    model_key: str
    step_offset: int
    created_at: float = field(default_factory=time.monotonic)
    last_accessed: float = field(default_factory=time.monotonic)
    ttl_seconds: float = 1800.0


# ---------------------------------------------------------------------------
# Fingerprinting
# ---------------------------------------------------------------------------

def _normalise(text: str) -> str:
    """Replace dynamic tokens with stable placeholders."""
    text = _RE_ISO_TS.sub("<ts>", text)
    text = _RE_DATE.sub("<date>", text)
    text = _RE_UUID.sub("<uuid>", text)
    text = _RE_CWD.sub("<cwd>", text)
    text = _RE_GITSHA.sub("<gitsha>", text)
    text = _RE_META_TAG.sub("", text)

    # Collapse git status blocks — multi-line patterns starting with common
    # git status prefixes.
    text = re.sub(
        r"(?:On branch [^\n]+\n(?:Your branch is[^\n]*\n)?"
        r"(?:nothing to commit[^\n]*\n|(?:\s+[^\n]+\n)+?))",
        "<gitstatus>",
        text,
        flags=re.MULTILINE,
    )
    return text


def _stable_hash(messages: list[dict[str, Any]], model_key: str, provider_key: str) -> str:
    """Create a stable hash from conversation messages, model, and provider.

    * Normalises each text block to remove dynamic tokens.
    * Serialises media references by type only (ignoring volatile data URIs).
    * Includes tool schema digests when present.
    """
    normalised_parts: list[str] = [model_key, provider_key]

    for msg in messages:
        role = msg.get("role", "")
        normalised_parts.append(f"role={role}")

        content = msg.get("content")
        if content is None:
            continue

        if isinstance(content, str):
            normalised_parts.append(_normalise(content))
        elif isinstance(content, list):
            for block in content:
                if not isinstance(block, dict):
                    continue
                block_type = block.get("type", "")
                if block_type == "text":
                    normalised_parts.append(_normalise(block.get("text", "")))
                elif block_type == "image":
                    source = block.get("source", {})
                    media_type = source.get("media_type", "")
                    # Hash media data if available for stability.
                    data = source.get("data", "")
                    if data:
                        digest = hashlib.sha256(data.encode()).hexdigest()[:16]
                        normalised_parts.append(f"image:{media_type}:{digest}")
                    else:
                        normalised_parts.append(f"image:{media_type}")
                elif block_type == "tool_use":
                    tool_name = block.get("name", "")
                    tool_input = block.get("input", {})
                    normalised_parts.append(
                        f"tool:{tool_name}:{_normalise(json.dumps(tool_input, sort_keys=True))}"
                    )
                elif block_type == "tool_result":
                    tool_content = block.get("content", "")
                    normalised_parts.append(
                        f"tool_result:{_normalise(str(tool_content))}"
                    )

    # Include tool schemas when present on the message list.
    for msg in messages:
        tools = msg.get("tools")
        if isinstance(tools, list) and tools:
            schema_strs: list[str] = []
            for tool in tools:
                if isinstance(tool, dict):
                    name = tool.get("name", "")
                    schema = tool.get("input_schema", {})
                    schema_strs.append(f"{name}:{json.dumps(schema, sort_keys=True)}")
            if schema_strs:
                schema_blob = "|".join(sorted(schema_strs))
                normalised_parts.append(f"tools:{hashlib.sha256(schema_blob.encode()).hexdigest()[:16]}")

    blob = "\x00".join(normalised_parts)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Conversation pool
# ---------------------------------------------------------------------------

class ConversationPool:
    """LRU cache of conversation contexts keyed by stable fingerprint.

    Usage::

        pool = ConversationPool()
        fp = pool.fingerprint(messages, "gpt-4o", "open_router")
        ctx = pool.checkout(fp, "open_router")
        if ctx is None:
            ctx = ConversationContext(cascade_id="…", …)
        # ... use ctx ...
        pool.checkin(fp, ctx)
    """

    def __init__(
        self,
        max_size: int | None = None,
        ttl_seconds: float | None = None,
    ) -> None:
        self._max_size: int = (
            max_size if max_size is not None else _env_int("CONVERSATION_POOL_MAX", 500)
        )
        self._ttl_seconds: float = (
            ttl_seconds
            if ttl_seconds is not None
            else _env_float("CONVERSATION_POOL_TTL_SECONDS", 1800)
        )
        # OrderedDict provides O(1) move-to-end for LRU.
        self._store: OrderedDict[str, ConversationContext] = OrderedDict()
        self._hits: int = 0
        self._misses: int = 0
        self._evictions: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fingerprint(
        self,
        messages: list[dict[str, Any]],
        model_key: str,
        provider_key: str,
    ) -> str:
        """Create a stable hash of the conversation state."""
        return _stable_hash(messages, model_key, provider_key)

    def checkout(
        self,
        fingerprint: str,
        provider_key: str,
    ) -> ConversationContext | None:
        """Retrieve a saved context for *fingerprint*.

        The entry is removed from the pool (no concurrent reuse).
        Returns *None* on cache miss or if the entry belongs to a different
        provider.
        """
        self._evict_expired()

        ctx = self._store.pop(fingerprint, None)
        if ctx is None:
            self._misses += 1
            return None

        if ctx.provider_key != provider_key:
            self._misses += 1
            # Re-insert for other providers.
            self._store[fingerprint] = ctx
            return None

        if time.monotonic() - ctx.created_at > self._ttl_seconds:
            self._evictions += 1
            self._misses += 1
            return None

        ctx.last_accessed = time.monotonic()
        self._hits += 1
        return ctx

    def checkin(
        self,
        fingerprint: str,
        context_entry: ConversationContext,
    ) -> None:
        """Save a context entry back into the pool."""
        self._evict_expired()

        # Update last-accessed time.
        context_entry.last_accessed = time.monotonic()

        if fingerprint in self._store:
            # Move to end (most recently used).
            self._store.move_to_end(fingerprint)
            self._store[fingerprint] = context_entry
        else:
            # Evict LRU if at capacity.
            while len(self._store) >= self._max_size:
                self._store.popitem(last=False)
                self._evictions += 1
            self._store[fingerprint] = context_entry

    def invalidate(self, provider_key: str) -> int:
        """Remove all entries belonging to *provider_key*.  Returns count."""
        to_remove = [
            fp
            for fp, ctx in self._store.items()
            if ctx.provider_key == provider_key
        ]
        for fp in to_remove:
            del self._store[fp]
        return len(to_remove)

    def get_stats(self) -> dict[str, Any]:
        """Return hit rate, miss rate, pool size, and eviction count."""
        total = self._hits + self._misses
        hit_rate = (self._hits / total) if total > 0 else 0.0
        miss_rate = (self._misses / total) if total > 0 else 0.0
        return {
            "pool_size": len(self._store),
            "max_size": self._max_size,
            "ttl_seconds": self._ttl_seconds,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(hit_rate, 4),
            "miss_rate": round(miss_rate, 4),
            "evictions": self._evictions,
        }

    def clear(self) -> None:
        """Empty the entire pool."""
        self._store.clear()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _evict_expired(self) -> int:
        """Remove entries that have exceeded their TTL."""
        now = time.monotonic()
        expired: list[str] = [
            fp
            for fp, ctx in self._store.items()
            if now - ctx.created_at > self._ttl_seconds
        ]
        for fp in expired:
            del self._store[fp]
            self._evictions += 1
        return len(expired)
