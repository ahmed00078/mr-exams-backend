import json
import hashlib
from typing import Any, Optional
from database import get_redis
from config import settings
import logging

logger = logging.getLogger(__name__)

class CacheManager:
    def __init__(self):
        self.redis = None
        self.cache_enabled = False  # ❌ Désactivé temporairement
    
    async def get_redis(self):
        if not self.cache_enabled:
            return None
        try:
            if not self.redis:
                self.redis = await get_redis()
            return self.redis
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
            return None  # ✅ Graceful fallback
    
    def _generate_key(self, prefix: str, **kwargs) -> str:
        key_data = json.dumps(kwargs, sort_keys=True, default=str)
        key_hash = hashlib.md5(key_data.encode()).hexdigest()[:8]
        return f"{prefix}:{key_hash}"
    
    async def get(self, key: str) -> Optional[Any]:
        redis = await self.get_redis()
        if not redis:
            return None
        try:
            value = await redis.get(key)
            if value:
                return json.loads(value)
        except Exception as e:
            logger.warning(f"Cache get error: {e}")
        return None
    
    async def set(self, key: str, value: Any, ttl: int = 3600):
        redis = await self.get_redis()
        if not redis:
            return
        try:
            value = json.dumps(value, default=str)
            await redis.setex(key, ttl, value)
        except Exception as e:
            logger.warning(f"Cache set error: {e}")
    
    async def cache_search_results(self, search_params: dict, results: dict):
        key = self._generate_key("search", **search_params)
        await self.set(key, results, settings.cache_ttl_results)
    
    async def get_cached_search(self, search_params: dict) -> Optional[dict]:
        key = self._generate_key("search", **search_params)
        return await self.get(key)

cache_manager = CacheManager()