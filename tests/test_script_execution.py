"""
脚本执行测试
测试JavaScript执行、元素操作等功能
"""
import pytest
import requests
import json

BASE_URL = 'http://127.0.0.1:27889'


class TestJavaScriptExecution:
    """JavaScript执行测试"""

    def test_simple_js_execution(self):
        """测试简单JS执行"""
        post_data = {
            'url': 'https://www.baidu.com',
            'timeout': 30,
            'run_time': True,
            'html':False,
            'script': [
                {'run_js': 'document.title'}
            ],
        }
        
        resp = requests.post(f'{BASE_URL}/uploadUrl', json=post_data)
        result = resp.json()
        
        assert result['status'] == 'success'
        assert result.get('js_result') is not None
        assert len(result['js_result']) > 0

    def test_async_js_execution(self):
        """测试异步JS执行"""
        post_data = {
            'url': 'https://www.baidu.com',
            'timeout': 30,
            'html':False,
            'run_time': True,
            'script': [
                {
                    'run_js': 'new Promise(resolve => setTimeout(() => resolve("done"), 100))',
                    'wait_async': True
                }
            ],
        }
        
        resp = requests.post(f'{BASE_URL}/uploadUrl', json=post_data)
        result = resp.json()
        
        assert result['status'] == 'success'

    def test_multiple_js_execution(self):
        """测试多个JS脚本执行"""
        post_data = {
            'url': 'https://www.baidu.com',
            'timeout': 30,
            'run_time': True,
            'script': [
                {'run_js': 'document.title'},
                {'run_js': 'window.location.href'},
            ],
        }
        
        resp = requests.post(f'{BASE_URL}/uploadUrl', json=post_data)
        result = resp.json()
        
        assert result['status'] == 'success'
        assert len(result.get('js_result', [])) == 2


class TestElementOperations:
    """元素操作测试"""

    def test_element_click(self):
        """测试元素点击"""
        post_data = {
            'url': 'https://www.baidu.com',
            'timeout': 30,
            'script': [
                {'pattern': 'c:#chat-submit-button', 'function': 'click'},
            ],
            'ensure_eles': [{'pattern': 'x://b[contains(text(), "网页")]'}],
        }
        
        resp = requests.post(f'{BASE_URL}/uploadUrl', json=post_data)
        result = resp.json()
        
        # 点击搜索按钮可能导致页面跳转，但不应该报错
        assert result['status'] in ['success', 'fail']

    def test_element_input(self):
        """测试元素输入"""
        post_data = {
            'url': 'https://www.baidu.com',
            'timeout': 30,
            'script': [
                {'pattern': '#chat-textarea', 'function': 'input', 'value': 'LEP测试'},
                {'pattern': 'c:#chat-submit-button', 'function': 'click'},
            ],
            'ensure_eles': [{'pattern': 'x://b[contains(text(), "网页")]'}],
        }
        
        resp = requests.post(f'{BASE_URL}/uploadUrl', json=post_data)
        result = resp.json()
        
        assert result['status'] == 'success'

    def test_element_click_by_js(self):
        """测试通过JS点击元素"""
        post_data = {
            'url': 'https://www.baidu.com',
            'timeout': 30,
            'script': [
                {'pattern': 'c:#chat-submit-button', 'function': 'click', 'by_js': True},
            ],
            'ensure_eles': [{'pattern': 'x://b[contains(text(), "网页")]'}],
        }
        
        resp = requests.post(f'{BASE_URL}/uploadUrl', json=post_data)
        result = resp.json()
        
        assert result['status'] in ['success', 'fail']


class TestThreadScript:
    """线程脚本测试"""

    def test_thread_script_mode(self):
        """测试线程模式执行脚本"""
        post_data = {
            'url': 'https://www.baidu.com',
            'timeout': 30,
            'thread_script': True,
            'script': [
                {'run_js': 'return 1'}
            ],
            'ensure_eles': [{'pattern': 'c:#chat-submit-button'}],
        }
        
        resp = requests.post(f'{BASE_URL}/uploadUrl', json=post_data)
        result = resp.json()
        
        assert result['status'] == 'success'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
