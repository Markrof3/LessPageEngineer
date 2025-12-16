import time
from copy import copy
class RunTimeCache:
    def __init__(self, logger):
        # 本地缓存资源字典
        self.all_source_dict = {}
        self.logger = logger

    def clear_all_source_dict(self):
        drop_key = []
        for key in self.all_source_dict.keys():
            if time.time() - self.all_source_dict[key]['update_time'] >= 300:
                drop_key.append(key)
        # 实际删除过期的缓存
        if drop_key:
            self._drop_source_dict(drop_key)

    def _drop_source_dict(self, keys):
        all_source_dict = copy(self.all_source_dict)
        if isinstance(keys, list):
            for key in keys:
                del all_source_dict[key]
                self.logger.debug(f"已清除key:{key}, {all_source_dict.get('key')}")
        else:
            del all_source_dict[keys]
            self.logger.debug(f"已清除key:{keys}, {all_source_dict.get('key')}")
        self.all_source_dict = all_source_dict

    def search_source_dict(self, key):
        if not key or not isinstance(key, str):
            return None
        source_dict = self.all_source_dict.get(key, {}).get('data')
        if source_dict:
            self.all_source_dict[key]['update_time'] = round(time.time(), 1)
        return source_dict

    def add_source_dict(self, key, source_dict):
        self.all_source_dict[key] = {'data': source_dict, 'update_time': round(time.time(), 1)}

    def drop_source_dict(self, key):
        if not key or not isinstance(key, str):
            return None
        if self.all_source_dict.get(key):
            self._drop_source_dict(key)

    def list_keys(self):
        """列出所有缓存key"""
        return list(self.all_source_dict.keys())

    def update_source_dict(self, key, source_dict):
        """更新指定key的缓存内容"""
        if not key or not isinstance(key, str):
            return False
        if key in self.all_source_dict:
            self.all_source_dict[key]['data'] = source_dict
            self.all_source_dict[key]['update_time'] = round(time.time(), 1)
            return True
        return False
