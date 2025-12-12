import threading
from datetime import datetime
from typing import Optional, Dict, Any

import pymongo
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

from LessPageEngineer.Settings import MONGO_HOST, MONGO_DB, MONGO_CONNECT


class MongoConnectionPool:
    """MongoDB连接池单例管理器"""
    _instance: Optional['MongoConnectionPool'] = None
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
        self._client: Optional[MongoClient] = None
        self._client_lock = threading.Lock()

    def get_client(self, host: str = MONGO_HOST, 
                   max_pool_size: int = 50,
                   min_pool_size: int = 5,
                   max_idle_time_ms: int = 30000,
                   server_selection_timeout_ms: int = 5000,
                   connect_timeout_ms: int = 5000,
                   socket_timeout_ms: int = 30000) -> MongoClient:
        """获取或创建MongoDB客户端（内置连接池）"""
        if self._client is None:
            with self._client_lock:
                if self._client is None:
                    self._client = MongoClient(
                        host=host,
                        maxPoolSize=max_pool_size,
                        minPoolSize=min_pool_size,
                        maxIdleTimeMS=max_idle_time_ms,
                        serverSelectionTimeoutMS=server_selection_timeout_ms,
                        connectTimeoutMS=connect_timeout_ms,
                        socketTimeoutMS=socket_timeout_ms,
                        retryWrites=True,
                        retryReads=True
                    )
        return self._client

    def close(self):
        """关闭MongoDB客户端"""
        with self._client_lock:
            if self._client is not None:
                self._client.close()
                self._client = None

    def health_check(self) -> bool:
        """健康检查"""
        if self._client is None:
            return False
        try:
            self._client.admin.command('ping')
            return True
        except (ConnectionFailure, ServerSelectionTimeoutError):
            return False


# 全局连接池实例
_mongo_pool_manager = MongoConnectionPool()


class MongoCache:
    """MongoDB缓存管理类，支持连接池和上下文管理器"""

    def __init__(self, host: str = MONGO_HOST, db: str = MONGO_DB, collection: str = MONGO_CONNECT):
        self._host = host
        self._db_name = db
        self._collection_name = collection
        self._client: Optional[MongoClient] = None
        self._collection: Optional[Collection] = None
        self._lock = threading.Lock()

        # 初始化连接
        self._init_connection()

    def _init_connection(self):
        """初始化MongoDB连接（使用连接池）"""
        self._client = _mongo_pool_manager.get_client(host=self._host)
        self._collection = self._client[self._db_name][self._collection_name]

    def __enter__(self) -> 'MongoCache':
        """上下文管理器入口"""
        if self._collection is None:
            self._init_connection()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """上下文管理器出口 - 连接池模式下不关闭连接，由连接池管理"""
        return False

    @property
    def mong_con(self) -> Collection:
        """获取MongoDB集合（兼容旧代码）"""
        return self._collection

    def _execute_with_retry(self, operation, max_retries: int = 3):
        """带重试的MongoDB操作执行"""
        last_error = None
        for attempt in range(max_retries):
            try:
                return operation()
            except (ConnectionFailure, ServerSelectionTimeoutError) as e:
                last_error = e
                # 尝试重新获取连接
                self._init_connection()
        raise last_error

    def dump_data(self, key: str, source_dict: Dict[str, Any], replace: bool):
        """保存数据到MongoDB"""
        if not isinstance(source_dict, dict):
            raise TypeError("source_dict必须是字典类型")

        source_dict.update({
            'key': key,
            'update_time': datetime.now()
        })

        def _dump():
            existing = self._collection.count_documents({'key': key})
            if existing == 0:
                self._collection.insert_one(source_dict)
            elif replace:
                self._collection.replace_one({'key': key}, source_dict, upsert=True)

        self._execute_with_retry(_dump)

    def load_data(self, key: str) -> Optional[Dict[str, Any]]:
        """从MongoDB加载数据"""
        if not key or not isinstance(key, str):
            return None

        def _load():
            return self._collection.find_one({'key': key})

        return self._execute_with_retry(_load)

    def delete_data(self, key: str) -> bool:
        """删除指定key的数据"""
        if not key or not isinstance(key, str):
            return False

        def _delete():
            result = self._collection.delete_one({'key': key})
            return result.deleted_count > 0

        return self._execute_with_retry(_delete)

    def exists(self, key: str) -> bool:
        """检查key是否存在"""
        if not key or not isinstance(key, str):
            return False

        def _exists():
            return self._collection.count_documents({'key': key}) > 0

        return self._execute_with_retry(_exists)

    def close(self):
        """关闭连接（连接池模式下由池管理，此方法保留兼容性）"""
        pass

    @classmethod
    def close_pool(cls):
        """关闭全局连接池"""
        _mongo_pool_manager.close()

    @classmethod
    def health_check(cls) -> bool:
        """健康检查"""
        return _mongo_pool_manager.health_check()
