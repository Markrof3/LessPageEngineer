"""
请求拦截测试
测试Route拦截、请求填充、请求中止等功能
"""
import pytest
import requests
import json

BASE_URL = 'http://127.0.0.1:27888'


class TestRequestFill:
    """请求填充测试"""

    def test_fill_request_with_json(self):
        """测试用JSON数据填充请求"""
        post_data = {
            'url': 'https://www.baidu.com',
            'timeout': 30,
            'wait_urls': [
                {
                    'url': '**/sugrec**',
                    'fill_data': {'code': 0, 'data': 'mocked'},
                    'headers': {'Content-Type': 'application/json'},
                }
            ],
        }
        
        resp = requests.post(f'{BASE_URL}/uploadUrl', json=post_data)
        result = resp.json()
        
        assert result['status'] == 'success'

    def test_fill_request_with_string(self):
        """测试用字符串填充请求"""
        post_data = {
            'url': 'https://www.baidu.com',
            'timeout': 30,
            'wait_urls': [
                {
                    'url': '**/sugrec**',
                    'fill_data': '{"code": 0}',
                    'headers': {'Content-Type': 'application/json'},
                }
            ],
        }
        
        resp = requests.post(f'{BASE_URL}/uploadUrl', json=post_data)
        result = resp.json()
        
        assert result['status'] == 'success'


class TestRequestAbort:
    """请求中止测试"""

    def test_abort_request(self):
        """测试中止指定请求"""
        post_data = {
            'url': 'https://www.baidu.com',
            'timeout': 30,
            'wait_urls': [
                {
                    'url': '**/sugrec**',
                    'abort': True,
                }
            ],
        }
        
        resp = requests.post(f'{BASE_URL}/uploadUrl', json=post_data)
        result = resp.json()
        
        assert result['status'] == 'success'


class TestRequestModify:
    """请求修改测试"""

    def test_modify_response(self):
        """测试修改响应内容"""
        post_data = {
            'url': 'https://www.baidu.com',
            'timeout': 30,
            'wait_urls': [
                {
                    'url': '**/sugrec**',
                    'modify': {
                        'be_replace': 'old_text',
                        'to_replace': 'new_text',
                    }
                }
            ],
        }
        
        resp = requests.post(f'{BASE_URL}/uploadUrl', json=post_data)
        result = resp.json()
        
        # 即使没有匹配到替换内容，也应该成功
        assert result['status'] == 'success'


class TestKeepProxy:
    """代理保持测试"""

    @pytest.mark.skip(reason="需要代理环境")
    def test_keep_proxy_request(self):
        """测试保持代理请求"""
        post_data = {
            'url': 'https://www.baidu.com',
            'timeout': 30,
            'wait_urls': [
                {
                    'url': '**/api/**',
                    'keep_proxy': True,
                }
            ],
        }
        
        resp = requests.post(f'{BASE_URL}/uploadUrl', json=post_data)
        result = resp.json()
        
        assert result.get('keep_proxy') is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
