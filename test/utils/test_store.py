"""
TaskStore 单元测试

测试范围：
  内存后端  — set/get/delete/exists/update
  TTL 过期  — 过期后 get 返回 None
  MAX_SIZE  — 超限时淘汰最旧条目
  Redis 降级— Redis 不可达时静默切换内存
  Redis 后端— mock ping 成功，验证 setex/get 被调用
  update    — 子字段更新正确；key 不存在返回 False
"""

import time
from unittest.mock import MagicMock, patch

import pytest


# ─── fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _no_real_redis(mock_settings):
    """禁止真实 Redis 连接，强制内存后端。"""
    with patch("app.config.get_settings", return_value=mock_settings), \
         patch("redis.Redis", side_effect=ConnectionError("no redis")):
        yield


@pytest.fixture
def store():
    from app.utils.store import TaskStore
    return TaskStore("test", ttl=60)


# ═══════════════════════════════════════════════════════════════════════════════
# 内存后端基本操作
# ═══════════════════════════════════════════════════════════════════════════════

class TestMemoryBackendBasics:

    def test_backend_is_memory(self, store):
        assert store.backend == "memory"

    def test_set_and_get(self, store):
        store.set("k1", {"status": "done"})
        assert store.get("k1") == {"status": "done"}

    def test_get_nonexistent_returns_none(self, store):
        assert store.get("no_such_key") is None

    def test_delete_removes_entry(self, store):
        store.set("k2", "value")
        store.delete("k2")
        assert store.get("k2") is None

    def test_delete_nonexistent_no_error(self, store):
        store.delete("ghost")  # should not raise

    def test_exists_true(self, store):
        store.set("k3", [1, 2, 3])
        assert store.exists("k3") is True

    def test_exists_false(self, store):
        assert store.exists("absent") is False

    def test_overwrite_value(self, store):
        store.set("k4", {"a": 1})
        store.set("k4", {"a": 99})
        assert store.get("k4") == {"a": 99}

    def test_various_value_types(self, store):
        for val in [42, "string", [1, 2], {"nested": True}, None]:
            store.set("typed", val)
            assert store.get("typed") == val


# ═══════════════════════════════════════════════════════════════════════════════
# update 方法
# ═══════════════════════════════════════════════════════════════════════════════

class TestUpdate:

    def test_update_single_field(self, store):
        store.set("task", {"status": "processing", "progress": 0})
        ok = store.update("task", status="completed", progress=100)
        assert ok is True
        data = store.get("task")
        assert data["status"] == "completed"
        assert data["progress"] == 100

    def test_update_preserves_other_fields(self, store):
        store.set("task", {"status": "processing", "error": None, "request": {"id": 1}})
        store.update("task", status="failed", error="boom")
        data = store.get("task")
        assert data["request"] == {"id": 1}

    def test_update_nonexistent_returns_false(self, store):
        assert store.update("ghost", status="x") is False

    def test_update_non_dict_value_returns_false(self, store):
        store.set("plain", "string_value")
        result = store.update("plain", status="x")
        assert result is False


# ═══════════════════════════════════════════════════════════════════════════════
# TTL 过期
# ═══════════════════════════════════════════════════════════════════════════════

class TestTTLExpiry:

    def test_expired_entry_returns_none(self, store):
        fake_now = [0.0]
        with patch("time.monotonic", side_effect=lambda: fake_now[0]):
            fake_now[0] = 0.0
            store.set("expires", {"data": 1}, ttl=10)

            fake_now[0] = 5.0     # 5s 后，未过期
            assert store.get("expires") == {"data": 1}

            fake_now[0] = 11.0    # 11s 后，已过期
            assert store.get("expires") is None

    def test_expired_entry_removed_from_memory(self, store):
        fake_now = [0.0]
        with patch("time.monotonic", side_effect=lambda: fake_now[0]):
            fake_now[0] = 0.0
            store.set("will_expire", "x", ttl=5)

            fake_now[0] = 10.0
            store.get("will_expire")  # 触发懒清理
            assert "will_expire" not in store._mem

    def test_different_ttl_per_key(self, store):
        fake_now = [0.0]
        with patch("time.monotonic", side_effect=lambda: fake_now[0]):
            fake_now[0] = 0.0
            store.set("short", "a", ttl=5)
            store.set("long", "b", ttl=100)

            fake_now[0] = 10.0
            assert store.get("short") is None
            assert store.get("long") == "b"

    def test_custom_ttl_in_set(self, store):
        from app.utils.store import TaskStore
        s = TaskStore("ttl_test", ttl=3600)
        fake_now = [0.0]
        with patch("time.monotonic", side_effect=lambda: fake_now[0]):
            fake_now[0] = 0.0
            s.set("k", "v", ttl=1)  # override default 3600
            fake_now[0] = 2.0
            assert s.get("k") is None


# ═══════════════════════════════════════════════════════════════════════════════
# MAX_SIZE 淘汰
# ═══════════════════════════════════════════════════════════════════════════════

class TestMaxSizeEviction:

    def test_max_size_not_exceeded(self):
        from app.utils.store import TaskStore
        s = TaskStore("evict_test", ttl=3600)
        s.MAX_SIZE = 5

        for i in range(7):
            s.set(f"key_{i}", i)

        assert len(s._mem) <= 5

    def test_oldest_evicted_first(self):
        from app.utils.store import TaskStore
        s = TaskStore("evict_order", ttl=3600)
        s.MAX_SIZE = 3

        fake_now = [0.0]
        with patch("time.monotonic", side_effect=lambda: fake_now[0]):
            for i in range(5):
                fake_now[0] = float(i)
                s.set(f"k{i}", i)

        # After inserting 5 with MAX_SIZE=3, the 2 oldest (k0, k1) should be gone
        assert s.get("k0") is None
        assert s.get("k1") is None
        assert s.get("k4") is not None

    def test_expired_entries_removed_before_eviction(self):
        from app.utils.store import TaskStore
        s = TaskStore("evict_expired", ttl=3600)
        s.MAX_SIZE = 3

        fake_now = [0.0]
        with patch("time.monotonic", side_effect=lambda: fake_now[0]):
            # Write 2 entries that will expire
            fake_now[0] = 0.0
            s.set("expire1", "a", ttl=5)
            s.set("expire2", "b", ttl=5)

            # Advance time past expiry
            fake_now[0] = 10.0

            # Write 3 more; expired ones should be purged first
            for i in range(3):
                fake_now[0] = 10.0 + i
                s.set(f"fresh_{i}", i)

        # 2 expired + 3 fresh = 5 total initially, but expired get cleaned
        assert len(s._mem) <= s.MAX_SIZE


# ═══════════════════════════════════════════════════════════════════════════════
# Redis 降级
# ═══════════════════════════════════════════════════════════════════════════════

class TestRedisFallback:

    def test_redis_unavailable_uses_memory(self):
        from app.utils.store import TaskStore
        s = TaskStore("fallback_test", ttl=60)
        assert s.backend == "memory"
        s.set("k", "v")
        assert s.get("k") == "v"

    def test_redis_set_failure_falls_back_to_memory(self):
        """Redis 已连接，但 setex 抛异常 → 降级写内存。"""
        from app.utils.store import TaskStore

        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis.setex.side_effect = ConnectionError("redis down")
        mock_redis.get.side_effect = ConnectionError("redis down")

        s = TaskStore("redis_fail", ttl=60, redis_client=mock_redis)
        s.set("k", "v")
        assert s.get("k") == "v"      # 从内存中读
        assert "k" in s._mem


# ═══════════════════════════════════════════════════════════════════════════════
# Redis 后端（mock 成功）
# ═══════════════════════════════════════════════════════════════════════════════

class TestRedisBackend:

    @pytest.fixture
    def redis_store(self):
        from app.utils.store import TaskStore
        import json

        mock_redis = MagicMock()
        mock_redis.ping.return_value = True

        _data = {}

        def fake_setex(key, ttl, val):
            _data[key] = val

        def fake_get(key):
            return _data.get(key)

        def fake_delete(key):
            _data.pop(key, None)

        mock_redis.setex.side_effect = fake_setex
        mock_redis.get.side_effect = fake_get
        mock_redis.delete.side_effect = fake_delete

        s = TaskStore("redis_test", ttl=60, redis_client=mock_redis)
        return s, mock_redis

    def test_backend_is_redis(self, redis_store):
        s, _ = redis_store
        assert s.backend == "redis"

    def test_set_calls_setex(self, redis_store):
        s, mock_redis = redis_store
        s.set("k", {"a": 1})
        mock_redis.setex.assert_called_once()
        args = mock_redis.setex.call_args[0]
        assert "k" in args[0]   # key contains prefix
        assert args[1] == 60    # ttl

    def test_get_reads_from_redis(self, redis_store):
        s, _ = redis_store
        s.set("k2", {"status": "done"})
        result = s.get("k2")
        assert result == {"status": "done"}

    def test_delete_calls_redis_delete(self, redis_store):
        s, mock_redis = redis_store
        s.set("del_me", "x")
        s.delete("del_me")
        mock_redis.delete.assert_called_once()
        assert s.get("del_me") is None

    def test_full_key_uses_prefix(self, redis_store):
        s, mock_redis = redis_store
        s.set("mykey", "val")
        called_key = mock_redis.setex.call_args[0][0]
        assert called_key == "redis_test:mykey"
