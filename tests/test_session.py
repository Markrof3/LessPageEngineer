"""
Session保持测试
测试会话复用、Cookie管理等功能
"""
import pytest
import requests
import time

BASE_URL = 'http://127.0.0.1:27888'


class TestSessionKeep:
    """Session保持测试"""

    def test_create_session(self):
        """测试创建Session"""
        session_id = f'test_session_{int(time.time())}'
        
        post_data = {
            'url': 'https://www.baidu.com',
            'timeout': 30,
            'session_id': session_id,
        }
        
        resp = requests.post(f'{BASE_URL}/uploadUrl', json=post_data)
        result = resp.json()
        
        assert result['status'] == 'success'
        return session_id

    def test_reuse_session(self):
        """测试复用Session"""
        session_id = f'test_session_{int(time.time())}'
        
        # 第一次请求创建session
        post_data1 = {
            'url': 'https://www.baidu.com',
            'timeout': 30,
            'session_id': session_id,
        }
        
        resp1 = requests.post(f'{BASE_URL}/uploadUrl', json=post_data1)
        result1 = resp1.json()
        assert result1['status'] == 'success'
        
        # 第二次请求复用session
        post_data2 = {
            'url': 'https://www.baidu.com',
            'timeout': 30,
            'session_id': session_id,
        }
        
        resp2 = requests.post(f'{BASE_URL}/uploadUrl', json=post_data2)
        result2 = resp2.json()
        assert result2['status'] == 'success'

    def test_init_session(self):
        """测试init_session模式"""
        session_id = f'test_session_{int(time.time())}'
        
        post_data = {
            'session_id': session_id,
            'init_session': {
                'url': 'https://www.baidu.com',
                'timeout': 30,
            }
        }
        
        resp = requests.post(f'{BASE_URL}/uploadUrl', json=post_data)
        result = resp.json()
        
        assert result['status'] == 'success'


class TestCookieManagement:
    """Cookie管理测试"""

    def test_get_cookies(self):
        """测试获取Cookies"""
        post_data = {
            'url': 'https://www.baidu.com',
            'timeout': 30,
            'cookies': True,
        }
        
        resp = requests.post(f'{BASE_URL}/uploadUrl', json=post_data)
        result = resp.json()
        
        assert result['status'] == 'success'
        assert result.get('cookies') is not None

    def test_set_cookies(self):
        """测试设置Cookies"""
        post_data = {
            'url': 'https://www.baidu.com',
            'timeout': 30,
            'set_cookies': [
                {'name': 'test_cookie', 'value': 'test_value', 'domain': '.baidu.com'}
            ],
            'cookies': True,
        }
        
        resp = requests.post(f'{BASE_URL}/uploadUrl', json=post_data)
        result = resp.json()
        
        assert result['status'] == 'success'

    def test_clear_cookies(self):
        """测试清除Cookies"""
        post_data = {
            'url': 'https://www.baidu.com',
            'timeout': 30,
            'clear_cookies': True,
            'cookies': True,
        }
        
        resp = requests.post(f'{BASE_URL}/uploadUrl', json=post_data)
        result = resp.json()
        
        assert result['status'] == 'success'


class TestStorageManagement:
    """Storage管理测试"""

    def test_get_session_storage(self):
        """测试获取SessionStorage"""
        post_data = {
            'url': 'https://www.baidu.com',
            'timeout': 30,
            'session_storage': True,
        }
        
        resp = requests.post(f'{BASE_URL}/uploadUrl', json=post_data)
        result = resp.json()
        
        assert result['status'] == 'success'
        # session_storage 可能为空或有值

    def test_get_local_storage(self):
        """测试获取LocalStorage"""
        post_data = {
            'url': 'https://www.baidu.com',
            'timeout': 30,
            'local_storage': True,
        }
        
        resp = requests.post(f'{BASE_URL}/uploadUrl', json=post_data)
        result = resp.json()
        
        assert result['status'] == 'success'


class TestNewContext:
    """新上下文测试"""

    def test_new_context_isolation(self):
        """测试新上下文隔离"""
        post_data = {
            'url': 'https://www.baidu.com',
            'timeout': 30,
            'new_context': True,
            'cookies': True,
        }
        
        resp = requests.post(f'{BASE_URL}/uploadUrl', json=post_data)
        result = resp.json()
        
        assert result['status'] == 'success'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
