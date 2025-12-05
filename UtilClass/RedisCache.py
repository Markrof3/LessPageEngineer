import threading

import redis
import json

from datetime import datetime
from re import search

from LessPageEngineering.UpstreamSettings import (
    UPSTREAM_CONTROL_ENABLE, UPSTREAM_CACHE_SYNC,
    REDIS_HOST, REDIS_PORT, REDIS_DB, 
    CACHE_PROXY_MAIN_KEY, CACHE_PROXY_HEADERS_KEY,
    CACHE_PROXY_BODY_KEY, GLOBAL_PROXY_KEY
)
from LessPageEngineering.Utils.Utils import url_pattern_cut, get_local_ip, reduce_url, encode_base64_in_chunks


class RedisCache:
    def __init__(self, cache_proxy):
        # 检查上游控制开关
        self._enabled = UPSTREAM_CONTROL_ENABLE and UPSTREAM_CACHE_SYNC
        
        if not self._enabled:
            self.redis_con = None
            return
            
        # 创建链接池
        pool = redis.ConnectionPool(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
        self.redis_con = redis.Redis(connection_pool=pool)
        self.REDIS_KEY = f'{CACHE_PROXY_MAIN_KEY}:'
        self.RESPONSE_HEADERS_KEY = CACHE_PROXY_HEADERS_KEY
        self.RESPONSE_BODY_KEY = CACHE_PROXY_BODY_KEY
        self.GLOBAL_PROXY_KEY = GLOBAL_PROXY_KEY
        self.REDIS_KEY = self.REDIS_KEY.replace(':', f'_{get_local_ip()}:{cache_proxy.split(":")[-1]}:')
        self.del_header_params = ['cache-Control', 'expires', 'pragma', 'etag', 'last-modified', 'vary', 'age', 'date']
        self.lock = threading.Lock()

    def _check_enabled(self):
        """检查是否启用缓存同步"""
        return self._enabled and self.redis_con is not None

    # 放行被wait_urls匹配中的链接
    def delete_cache_from_redis(self, res, wait_urls):
        if not self._check_enabled():
            return
            
        pattern_list = []
        key_list = []
        for i in res.keys():
            if i.startswith('http'):
                key_list.append(i)
        for wait_url in wait_urls:
            if isinstance(wait_url, str):
                pattern_list.append(url_pattern_cut(wait_url))
            elif isinstance(wait_url, dict):
                pattern_list.append(url_pattern_cut(wait_url['url']))
        for key in key_list:
            # 放行被wait_urls匹配中的链接
            for pass_pattern in pattern_list:
                if search(pass_pattern, key):
                    # 被放行则删除对应的redis
                    self.redis_con.hdel(self.REDIS_KEY + self.RESPONSE_BODY_KEY, key)
                    self.redis_con.hdel(self.REDIS_KEY + self.RESPONSE_HEADERS_KEY, key)
                    break

    # 删除相关缓存参数，防止浏览器缓存文件
    def drop_cache_headers(self, source_dict_item):
        lower_headers = [(i, i.lower()) for i in source_dict_item['headers'].keys()]
        for headers in lower_headers:
            if headers[1] in self.del_header_params:
                del source_dict_item['headers'][headers[0]]

    # 向响应头中添加对应信息
    def add_headers(self, source_dict_item, update_time):
        # 添加缓存头，时间：一小时
        source_dict_item['headers']['Cache-Control'] = 'public, max-age=3600'
        # res[key]['headers']['Cache-Control'] = 'no-cache'
        # 添加Update_time 告诉代理缓存是否需要重新读取缓存
        update_time = update_time if update_time else datetime.strptime(
            '2024-01-01',
            '%Y-%m-%d')
        source_dict_item['headers']['LPE_Update_time'] = int(update_time.timestamp())

    # 上传缓存至redis
    def upload_cache_to_redis(self, source_dict):
        if not self._check_enabled():
            return
            
        key_list = []
        for i in source_dict.keys():
            if i.startswith('http'):
                key_list.append(i)
        header_dict = {}
        body_dict = {}
        for key in key_list:
            # r_key = reduce_url(key)
            r_key = key
            self.drop_cache_headers(source_dict[key])
            self.add_headers(source_dict[key], source_dict.get('update_time'))
            header_dict[r_key] = json.dumps(source_dict[key]['headers'], ensure_ascii=False)
            body_dict[r_key] = encode_base64_in_chunks(source_dict[key]['body']).decode() if isinstance(
                source_dict[key]['body'],
                bytes) else encode_base64_in_chunks(
                source_dict[key]['body'].encode()).decode()
        if body_dict:
            self.redis_con.hset(self.REDIS_KEY + self.RESPONSE_BODY_KEY, mapping=body_dict)
        if header_dict:
            self.redis_con.hset(self.REDIS_KEY + self.RESPONSE_HEADERS_KEY, mapping=header_dict)

    # 上传mitmproxy全局代理
    def upload_proxy_to_redis(self, proxy, timeout):
        if not self._check_enabled():
            return
            
        self.redis_con.delete(self.REDIS_KEY + self.GLOBAL_PROXY_KEY)
        self.redis_con.set(self.REDIS_KEY + self.GLOBAL_PROXY_KEY, proxy)
        self.redis_con.expire(self.REDIS_KEY + self.GLOBAL_PROXY_KEY, timeout)
