"""
缓存功能测试
测试本地缓存读写、key_save、key_replace等功能
"""
import pytest
import requests
import time
import os

BASE_URL = 'http://127.0.0.1:27889'


class TestKeySave:
    """缓存保存测试"""

    def test_key_save_creates_cache(self):
        """测试 key_save 创建缓存"""
        post_data = {
            'url': 'https://www.drissionpage.cn/',
            'timeout': 20,
            'ensure_eles':[{'pattern':'c:h2[id="️-概述123"]'}],
            # 'key_save': True,
            'key': "aHR0cHM6Ly93d3cuZHJpc3Npb25wYWdlLmNuLw==",
        }

        resp = requests.post(f'{BASE_URL}/uploadUrl', json=post_data)
        result = resp.json()
        
        assert result['status'] == 'success'
        assert result.get('key') is not None
        
        # 保存 key 供后续测试使用
        return result['key']

    def test_load_from_cache(self):
        """测试从缓存加载"""
        # 先保存缓存
        post_data_save = {
            'url': 'https://www.baidu.com',
            'timeout': 30,
            'key_save': True,
        }
        
        resp1 = requests.post(f'{BASE_URL}/uploadUrl', json=post_data_save)
        result1 = resp1.json()
        saved_key = result1.get('key')
        
        assert saved_key is not None
        
        # 使用缓存加载
        post_data_load = {
            'url': 'https://www.baidu.com',
            'timeout': 30,
            'key': saved_key,
        }
        
        resp2 = requests.post(f'{BASE_URL}/uploadUrl', json=post_data_load)
        result2 = resp2.json()
        
        assert result2['status'] == 'success'


class TestKeyReplace:
    """缓存替换测试"""

    def test_key_replace_updates_cache(self):
        """测试 key_replace 更新缓存"""
        # 先创建缓存
        post_data_save = {
            'url': 'https://www.baidu.com',
            'timeout': 30,
            'key_save': True,
        }
        
        resp1 = requests.post(f'{BASE_URL}/uploadUrl', json=post_data_save)
        result1 = resp1.json()
        saved_key = result1.get('key')
        
        # 替换缓存
        post_data_replace = {
            'url': 'https://www.baidu.com',
            'timeout': 30,
            'key': saved_key,
            'key_replace': True,
        }
        
        resp2 = requests.post(f'{BASE_URL}/uploadUrl', json=post_data_replace)
        result2 = resp2.json()
        
        assert result2['status'] == 'success'


class TestCacheWithWaitUrls:
    """缓存与等待链接结合测试"""

    def test_cache_with_wait_urls(self):
        """测试缓存模式下等待特定请求"""
        post_data = {
            'url': 'https://www.baidu.com',
            'timeout': 30,
            'key_save': True,
            'wait_urls': ['**/sugrec**'],
        }
        
        resp = requests.post(f'{BASE_URL}/uploadUrl', json=post_data)
        result = resp.json()
        
        assert result['status'] == 'success'
        assert result.get('key') is not None
        assert result.get('wait_urls') is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
