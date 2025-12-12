import threading
import json
from datetime import datetime
from re import search
from typing import Optional, Dict, List, Any

import redis

from LessPageEngineer.UpstreamSettings import (
    UPSTREAM_CONTROL_ENABLE, UPSTREAM_CACHE_SYNC,
    REDIS_HOST, REDIS_PORT, REDIS_DB,
    CACHE_PROXY_MAIN_KEY, CACHE_PROXY_HEADERS_KEY,
    CACHE_PROXY_BODY_KEY, GLOBAL_PROXY_KEY
)
from LessPageEngineer.Utils.Utils import url_pattern_cut, get_local_ip, encode_base64_in_chunks


class RedisConnectionPool:
    """Redis连接池单例管理器"""
    _instance: Optional['RedisConnectionPool'] = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._pool: Optional[redis.ConnectionPool] = None
        self._pool_lock = threading.Lock()

    def get_pool(self, host: str = REDIS_HOST, port: int = REDIS_PORT, db: int = REDIS_DB,
                 max_connections: int = 50, socket_timeout: int = 5,
                 socket_connect_timeout: int = 5) -> redis.ConnectionPool:
        """获取或创建连接池"""
        if self._pool is None:
            with self._pool_lock:
                if self._pool is None:
                    self._pool = redis.ConnectionPool(
                        host=host,
                        port=port,
                        db=db,
                        max_connections=max_connections,
                        socket_timeout=socket_timeout,
                        socket_connect_timeout=socket_connect_timeout,
                        decode_responses=False,
                        health_check_interval=30
                    )
        return self._pool

    def close(self):
        """关闭连接池"""
        with self._pool_lock:
            if self._pool is not None:
                self._pool.disconnect()
                self._pool = None


# 全局连接池实例
_redis_pool_manager = RedisConnectionPool()


class RedisCache:
    """Redis缓存管理类，支持连接池和上下文管理器"""

    def __init__(self, cache_proxy: str):
        self._enabled = UPSTREAM_CONTROL_ENABLE and UPSTREAM_CACHE_SYNC
        self._cache_proxy = cache_proxy
        self._redis_con: Optional[redis.Redis] = None
        self._lock = threading.Lock()

        # 配置键名
        self.REDIS_KEY = f'{CACHE_PROXY_MAIN_KEY}:'
        self.RESPONSE_HEADERS_KEY = CACHE_PROXY_HEADERS_KEY
        self.RESPONSE_BODY_KEY = CACHE_PROXY_BODY_KEY
        self.GLOBAL_PROXY_KEY = GLOBAL_PROXY_KEY
        self.REDIS_KEY = self.REDIS_KEY.replace(':', f'_{get_local_ip()}:{cache_proxy.split(":")[-1]}:')
        self.del_header_params = ['cache-control', 'expires', 'pragma', 'etag', 'last-modified', 'vary', 'age', 'date']

        # 初始化连接
        if self._enabled:
            self._init_connection()

    def _init_connection(self):
        """初始化Redis连接（使用连接池）"""
        pool = _redis_pool_manager.get_pool()
        self._redis_con = redis.Redis(connection_pool=pool)

    def __enter__(self) -> 'RedisCache':
        """上下文管理器入口"""
        if self._enabled and self._redis_con is None:
            self._init_connection()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """上下文管理器出口 - 连接池模式下不关闭连接，由连接池管理"""
        # 连接池会自动管理连接的回收，这里不需要显式关闭
        return False

    @property
    def redis_con(self) -> Optional[redis.Redis]:
        """获取Redis连接"""
        return self._redis_con

    def _check_enabled(self) -> bool:
        """检查是否启用缓存同步"""
        return self._enabled and self._redis_con is not None

    def _execute_with_retry(self, operation, max_retries: int = 3):
        """带重试的Redis操作执行"""
        last_error = None
        for attempt in range(max_retries):
            try:
                return operation()
            except redis.ConnectionError as e:
                last_error = e
                # 尝试重新获取连接
                self._init_connection()
            except redis.TimeoutError as e:
                last_error = e
        raise last_error

    def delete_cache_from_redis(self, res: Dict, wait_urls: List):
        """放行被wait_urls匹配中的链接"""
        if not self._check_enabled():
            return

        pattern_list = []
        key_list = [i for i in res.keys() if i.startswith('http')]

        for wait_url in wait_urls:
            if isinstance(wait_url, str):
                pattern_list.append(url_pattern_cut(wait_url))
            elif isinstance(wait_url, dict):
                pattern_list.append(url_pattern_cut(wait_url['url']))

        def _delete():
            with self._redis_con.pipeline() as pipe:
                for key in key_list:
                    for pass_pattern in pattern_list:
                        if search(pass_pattern, key):
                            pipe.hdel(self.REDIS_KEY + self.RESPONSE_BODY_KEY, key)
                            pipe.hdel(self.REDIS_KEY + self.RESPONSE_HEADERS_KEY, key)
                            break
                pipe.execute()

        self._execute_with_retry(_delete)

    def drop_cache_headers(self, source_dict_item: Dict):
        """删除相关缓存参数，防止浏览器缓存文件"""
        lower_headers = [(i, i.lower()) for i in list(source_dict_item['headers'].keys())]
        for headers in lower_headers:
            if headers[1] in self.del_header_params:
                del source_dict_item['headers'][headers[0]]

    def add_headers(self, source_dict_item: Dict, update_time: Optional[datetime]):
        """向响应头中添加对应信息"""
        source_dict_item['headers']['Cache-Control'] = 'public, max-age=3600'
        update_time = update_time if update_time else datetime.strptime('2024-01-01', '%Y-%m-%d')
        source_dict_item['headers']['LPE_Update_time'] = int(update_time.timestamp())

    def upload_cache_to_redis(self, source_dict: Dict):
        """上传缓存至redis"""
        if not self._check_enabled():
            return

        key_list = [i for i in source_dict.keys() if i.startswith('http')]
        header_dict = {}
        body_dict = {}

        for key in key_list:
            r_key = key
            self.drop_cache_headers(source_dict[key])
            self.add_headers(source_dict[key], source_dict.get('update_time'))
            header_dict[r_key] = json.dumps(source_dict[key]['headers'], ensure_ascii=False)
            body = source_dict[key]['body']
            if isinstance(body, bytes):
                body_dict[r_key] = encode_base64_in_chunks(body).decode()
            else:
                body_dict[r_key] = encode_base64_in_chunks(body.encode()).decode()

        def _upload():
            with self._redis_con.pipeline() as pipe:
                if body_dict:
                    pipe.hset(self.REDIS_KEY + self.RESPONSE_BODY_KEY, mapping=body_dict)
                if header_dict:
                    pipe.hset(self.REDIS_KEY + self.RESPONSE_HEADERS_KEY, mapping=header_dict)
                pipe.execute()

        self._execute_with_retry(_upload)

    def upload_proxy_to_redis(self, proxy: str, timeout: int):
        """上传mitmproxy全局代理"""
        if not self._check_enabled():
            return

        def _upload():
            key = self.REDIS_KEY + self.GLOBAL_PROXY_KEY
            with self._redis_con.pipeline() as pipe:
                pipe.delete(key)
                pipe.set(key, proxy)
                pipe.expire(key, timeout)
                pipe.execute()

        self._execute_with_retry(_upload)

    def close(self):
        """关闭连接（连接池模式下由池管理，此方法保留兼容性）"""
        pass

    @classmethod
    def close_pool(cls):
        """关闭全局连接池"""
        _redis_pool_manager.close()
