"""
TaskStore — Redis/内存双后端 KV 存储

解决控制器中裸 dict 的内存泄漏问题：
  - 内存后端：TTL 自动过期 + MAX_SIZE 淘汰，进程内条目有上界
  - Redis 后端：生产环境首选，TTL 由 Redis 管理；若 Redis 不可达，静默降级

使用方式：
    store = TaskStore("analysis", ttl=3600)
    store.set("task_123", {"status": "processing"})
    store.update("task_123", status="completed", result={...})
    data = store.get("task_123")     # None if expired or not found
    store.delete("task_123")
"""

import json
import threading
import time
from typing import Any, Dict, Optional, Tuple

from app.utils.logger import logger


class TaskStore:
    """
    双后端 KV 存储，默认 TTL 1 小时，最大内存条目 10,000。
    构造时自动尝试连接 Redis（来自 settings）；失败则静默降级到内存后端。
    """

    DEFAULT_TTL = 3600
    MAX_SIZE = 10_000

    def __init__(
        self,
        prefix: str,
        ttl: int = DEFAULT_TTL,
        redis_client=None,
    ):
        self.prefix = prefix
        self.default_ttl = ttl
        self._redis = redis_client
        self._mem: Dict[str, Tuple[Any, float]] = {}
        self._lock = threading.Lock()

        if self._redis is None:
            self._try_connect_redis()

        logger.debug(f"TaskStore '{prefix}' 初始化，backend={self.backend}")

    # ─── 后端检测 ──────────────────────────────────────────────────────────────

    def _try_connect_redis(self) -> None:
        try:
            import redis as redis_lib
            from app.config import get_settings
            s = get_settings()
            client = redis_lib.Redis(
                host=s.REDIS_HOST,
                port=s.REDIS_PORT,
                db=s.REDIS_DB,
                password=s.REDIS_PASSWORD or None,
                socket_connect_timeout=2,
                decode_responses=True,
            )
            client.ping()
            self._redis = client
            logger.info(f"TaskStore '{self.prefix}' 使用 Redis 后端 ({s.REDIS_HOST}:{s.REDIS_PORT})")
        except Exception:
            pass  # 静默降级到内存后端

    @property
    def backend(self) -> str:
        return "redis" if self._redis else "memory"

    def _full_key(self, key: str) -> str:
        return f"{self.prefix}:{key}"

    # ─── 公开接口 ──────────────────────────────────────────────────────────────

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        ttl = ttl if ttl is not None else self.default_ttl
        if self._redis:
            try:
                self._redis.setex(self._full_key(key), ttl, json.dumps(value, default=str))
                return
            except Exception as e:
                logger.warning(f"Redis set 失败，降级到内存: {e}")
        with self._lock:
            self._evict_if_needed()
            self._mem[key] = (value, time.monotonic() + ttl)

    def get(self, key: str) -> Optional[Any]:
        if self._redis:
            try:
                raw = self._redis.get(self._full_key(key))
                return json.loads(raw) if raw else None
            except Exception as e:
                logger.warning(f"Redis get 失败，降级到内存: {e}")
        with self._lock:
            self._lazy_expire(key)
            entry = self._mem.get(key)
            return entry[0] if entry else None

    def delete(self, key: str) -> None:
        if self._redis:
            try:
                self._redis.delete(self._full_key(key))
                return
            except Exception as e:
                logger.warning(f"Redis delete 失败，降级到内存: {e}")
        with self._lock:
            self._mem.pop(key, None)

    def exists(self, key: str) -> bool:
        return self.get(key) is not None

    def update(self, key: str, **fields: Any) -> bool:
        """更新已存在 dict 条目的子字段。key 不存在时返回 False。"""
        current = self.get(key)
        if current is None:
            return False
        if isinstance(current, dict):
            current.update(fields)
            self.set(key, current)
            return True
        return False

    # ─── 内存后端内部方法（需在 lock 内调用）──────────────────────────────────

    def _lazy_expire(self, key: str) -> None:
        entry = self._mem.get(key)
        if entry and time.monotonic() > entry[1]:
            del self._mem[key]

    def _evict_if_needed(self) -> None:
        now = time.monotonic()
        # 1. 清除所有已过期条目
        expired = [k for k, (_, exp) in self._mem.items() if now > exp]
        for k in expired:
            del self._mem[k]
        # 2. 超出 MAX_SIZE 时淘汰最旧的（按 expire_at 升序）
        overflow = len(self._mem) - self.MAX_SIZE + 1
        if overflow > 0:
            oldest = sorted(self._mem.items(), key=lambda x: x[1][1])[:overflow]
            for k, _ in oldest:
                del self._mem[k]
