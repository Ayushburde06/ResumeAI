"""
Session Cache — process-level in-memory cache for agent pipeline.

Key design principles:
- SHA-256 keyed on (resume_hash, jd_hash, section_name)
- Thread-safe via RLock
- TTL-based expiry (default 1 hour)
- Zero external dependencies
- Shared across requests within the same process lifetime
"""
import hashlib
import threading
import time
from typing import Any


class _CacheEntry:
    __slots__ = ("value", "expires_at", "created_at")

    def __init__(self, value: Any, ttl_seconds: int) -> None:
        self.value = value
        self.created_at = time.monotonic()
        self.expires_at = self.created_at + ttl_seconds


class SessionCache:
    """
    Process-level in-memory cache. One shared instance per server process.
    Stores parsed resume JSON, JD JSON, retrieved RAG chunks, and
    section-level rewrite outputs to avoid duplicate LLM calls.
    """

    def __init__(self, max_size: int = 512) -> None:
        self._store: dict[str, _CacheEntry] = {}
        self._lock = threading.RLock()
        self._max_size = max_size
        self._hits = 0
        self._misses = 0

    # ── Hashing helpers ───────────────────────────────────────────────────────

    @staticmethod
    def hash_text(text: str) -> str:
        """Return a short SHA-256 hex digest of any text."""
        return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:16]

    @staticmethod
    def make_key(*parts: str) -> str:
        """Build a compound cache key from multiple string parts."""
        combined = "|".join(parts)
        return hashlib.sha256(combined.encode()).hexdigest()[:24]

    # ── Core operations ───────────────────────────────────────────────────────

    def get(self, key: str) -> Any | None:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                self._misses += 1
                return None
            if time.monotonic() > entry.expires_at:
                del self._store[key]
                self._misses += 1
                return None
            self._hits += 1
            return entry.value

    def set(self, key: str, value: Any, ttl_seconds: int = 3600) -> None:
        with self._lock:
            # Evict oldest entries if at capacity
            if len(self._store) >= self._max_size:
                self._evict_expired()
                if len(self._store) >= self._max_size:
                    oldest_key = min(
                        self._store, key=lambda k: self._store[k].created_at
                    )
                    del self._store[oldest_key]
            self._store[key] = _CacheEntry(value, ttl_seconds)

    def delete(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)

    def invalidate_section(self, resume_hash: str, section: str) -> None:
        """Invalidate all cached entries for a specific resume section."""
        prefix = self.make_key(resume_hash, section)[:12]
        with self._lock:
            keys_to_delete = [k for k in self._store if k.startswith(prefix)]
            for k in keys_to_delete:
                del self._store[k]

    def invalidate_resume(self, resume_hash: str) -> None:
        """Invalidate all entries for a given resume hash."""
        with self._lock:
            keys_to_delete = [k for k in self._store if resume_hash in k]
            for k in keys_to_delete:
                del self._store[k]

    # ── Convenience section-level helpers ────────────────────────────────────

    def get_section(self, resume_hash: str, jd_hash: str, section: str) -> dict | None:
        key = self.make_key(resume_hash, jd_hash, section)
        return self.get(key)

    def set_section(
        self,
        resume_hash: str,
        jd_hash: str,
        section: str,
        value: dict,
        ttl_seconds: int = 3600,
    ) -> None:
        key = self.make_key(resume_hash, jd_hash, section)
        self.set(key, value, ttl_seconds)

    def get_jd_analysis(self, jd_hash: str) -> dict | None:
        return self.get(f"jd:{jd_hash}")

    def set_jd_analysis(self, jd_hash: str, value: dict, ttl_seconds: int = 7200) -> None:
        self.set(f"jd:{jd_hash}", value, ttl_seconds)

    def get_rag_context(self, jd_hash: str) -> str | None:
        return self.get(f"rag:{jd_hash}")

    def set_rag_context(self, jd_hash: str, value: str, ttl_seconds: int = 7200) -> None:
        self.set(f"rag:{jd_hash}", value, ttl_seconds)

    # ── Maintenance ───────────────────────────────────────────────────────────

    def _evict_expired(self) -> int:
        now = time.monotonic()
        expired = [k for k, e in self._store.items() if now > e.expires_at]
        for k in expired:
            del self._store[k]
        return len(expired)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
            self._hits = 0
            self._misses = 0

    def stats(self) -> dict:
        with self._lock:
            self._evict_expired()
            total = self._hits + self._misses
            return {
                "size": len(self._store),
                "max_size": self._max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(self._hits / total, 3) if total > 0 else 0.0,
            }


# ── Singleton ─────────────────────────────────────────────────────────────────
# One cache instance per process. Import and use directly.
agent_cache = SessionCache(max_size=512)
