"""
页面请求测试
测试访问URL、等待元素、等待请求等功能
"""
import pytest
import requests
import time

# 测试服务地址（需要先启动服务）
BASE_URL = 'http://127.0.0.1:27888'


class TestBasicPageRequest:
    """基础页面请求测试"""

    def test_simple_page_load(self):
        """测试简单页面加载"""
        post_data = {
            'url': 'https://www.baidu.com',
            'timeout': 30,
        }
        
        resp = requests.post(f'{BASE_URL}/uploadUrl', json=post_data)
        result = resp.json()
        
        assert result['status'] == 'success'
        assert result.get('text') is not None
        assert '百度' in result['text']

    def test_page_load_with_timeout(self):
        """测试页面加载超时"""
        post_data = {
            'url': 'https://www.baidu.com',
            'timeout': 3,
            'ensure_eles': [{'pattern': '#not_exist_element'}],
        }
        
        resp = requests.post(f'{BASE_URL}/uploadUrl', json=post_data)
        result = resp.json()
        
        assert result['status'] == 'fail'
        assert '超时' in result.get('message', '')


class TestWaitUrls:
    """等待请求测试"""

    def test_wait_single_url(self):
        """测试等待单个请求"""
        post_data = {
            'url': 'https://www.baidu.com',
            'timeout': 30,
            'wait_urls': ['**/sugrec**'],
        }
        
        resp = requests.post(f'{BASE_URL}/uploadUrl', json=post_data)
        result = resp.json()
        
        assert result['status'] == 'success'
        assert result.get('wait_urls') is not None

    def test_wait_multiple_urls(self):
        """测试等待多个请求"""
        post_data = {
            'url': 'https://www.baidu.com',
            'timeout': 30,
            'wait_urls': [
                {'url': '**/sugrec**', 'amount': 1},
            ],
        }
        
        resp = requests.post(f'{BASE_URL}/uploadUrl', json=post_data)
        result = resp.json()
        
        assert result['status'] == 'success'


class TestWaitElements:
    """等待元素测试"""

    def test_wait_single_element(self):
        """测试等待单个元素"""
        post_data = {
            'url': 'https://www.baidu.com',
            'timeout': 30,
            'ensure_eles': [{'pattern': '#su'}],
        }
        
        resp = requests.post(f'{BASE_URL}/uploadUrl', json=post_data)
        result = resp.json()
        
        assert result['status'] == 'success'
        assert result.get('wait_eles') is not None

    def test_wait_element_with_text_length(self):
        """测试等待元素并验证文本长度"""
        post_data = {
            'url': 'https://www.baidu.com',
            'timeout': 30,
            'ensure_eles': [{'pattern': '#su', 'ensure_txt_len': 0}],
        }
        
        resp = requests.post(f'{BASE_URL}/uploadUrl', json=post_data)
        result = resp.json()
        
        assert result['status'] == 'success'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
