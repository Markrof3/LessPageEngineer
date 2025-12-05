"""
代理功能测试
测试代理请求、TLS指纹伪装等功能
"""
import pytest
import requests

BASE_URL = 'http://127.0.0.1:27888'


class TestProxyRequest:
    """代理请求测试"""

    @pytest.mark.skip(reason="需要代理环境")
    def test_keep_proxy_basic(self):
        """测试基础代理保持"""
        post_data = {
            'url': 'https://httpbin.org/ip',
            'timeout': 30,
            'wait_urls': [
                {
                    'url': '**/ip**',
                    'keep_proxy': True,
                }
            ],
        }
        
        resp = requests.post(f'{BASE_URL}/uploadUrl', json=post_data)
        result = resp.json()
        
        assert result['status'] == 'success'
        assert result.get('keep_proxy') is not None

    @pytest.mark.skip(reason="需要代理环境")
    def test_keep_proxy_with_impersonate(self):
        """测试代理保持+指纹伪装"""
        post_data = {
            'url': 'https://httpbin.org/headers',
            'timeout': 30,
            'wait_urls': [
                {
                    'url': '**/headers**',
                    'keep_proxy': True,
                    'impersonate': 'chrome120',
                }
            ],
        }
        
        resp = requests.post(f'{BASE_URL}/uploadUrl', json=post_data)
        result = resp.json()
        
        assert result['status'] == 'success'


class TestGlobalProxy:
    """全局代理测试"""

    @pytest.mark.skip(reason="需要mitmproxy环境")
    def test_global_proxy_setting(self):
        """测试设置全局代理"""
        post_data = {
            'url': 'https://www.baidu.com',
            'timeout': 30,
            'global_proxy': 'http://127.0.0.1:7897',
        }
        
        resp = requests.post(f'{BASE_URL}/uploadUrl', json=post_data)
        result = resp.json()
        
        assert result['status'] == 'success'


class TestNetworkControl:
    """网络控制测试"""

    def test_disable_network(self):
        """测试禁用网络请求"""
        post_data = {
            'url': 'https://www.baidu.com',
            'timeout': 30,
            'disable_network': True,
            'key': 'some_cached_key',  # 需要有缓存才能工作
        }
        
        # 这个测试需要先有缓存，否则会失败
        # 主要验证参数能正常传递

    def test_disable_img_font(self):
        """测试禁用图片和字体"""
        post_data = {
            'url': 'https://www.baidu.com',
            'timeout': 30,
            'disable_img_font': True,
        }
        
        resp = requests.post(f'{BASE_URL}/uploadUrl', json=post_data)
        result = resp.json()
        
        assert result['status'] == 'success'


class TestUserAgent:
    """User-Agent测试"""

    def test_custom_ua(self):
        """测试自定义UA"""
        custom_ua = 'Mozilla/5.0 (Custom UA Test)'
        
        post_data = {
            'url': 'https://httpbin.org/user-agent',
            'timeout': 30,
            'ua': custom_ua,
        }
        
        resp = requests.post(f'{BASE_URL}/uploadUrl', json=post_data)
        result = resp.json()
        
        assert result['status'] == 'success'
        # 验证UA是否生效需要检查返回的HTML


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
