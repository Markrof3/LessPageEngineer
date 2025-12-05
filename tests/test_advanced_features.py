"""
高级功能测试
测试iframe、页面刷新、加载模式等功能
"""
import pytest
import requests

BASE_URL = 'http://127.0.0.1:27888'


class TestLoadMode:
    """加载模式测试"""

    def test_fast_mode(self):
        """测试快速加载模式"""
        post_data = {
            'url': 'https://www.baidu.com',
            'timeout': 30,
            'fast': True,
            'ensure_eles': [{'pattern': '#su'}],
        }
        
        resp = requests.post(f'{BASE_URL}/uploadUrl', json=post_data)
        result = resp.json()
        
        assert result['status'] == 'success'

    def test_normal_mode(self):
        """测试正常加载模式"""
        post_data = {
            'url': 'https://www.baidu.com',
            'timeout': 30,
            'fast': False,
        }
        
        resp = requests.post(f'{BASE_URL}/uploadUrl', json=post_data)
        result = resp.json()
        
        assert result['status'] == 'success'


class TestPageRefresh:
    """页面刷新测试"""

    def test_refresh_on_timeout(self):
        """测试超时刷新"""
        post_data = {
            'url': 'https://www.baidu.com',
            'timeout': 60,
            'refresh': True,
            'refresh_time': 10,
            'ensure_eles': [{'pattern': '#su'}],
        }
        
        resp = requests.post(f'{BASE_URL}/uploadUrl', json=post_data)
        result = resp.json()
        
        assert result['status'] == 'success'


class TestIframe:
    """Iframe测试"""

    @pytest.mark.skip(reason="需要包含iframe的测试页面")
    def test_iframe_element(self):
        """测试iframe内元素操作"""
        post_data = {
            'url': 'https://example.com/page-with-iframe',
            'timeout': 30,
            'iframe_ele': '#iframe_id',
            'ensure_eles': [{'pattern': '#element_in_iframe'}],
        }
        
        resp = requests.post(f'{BASE_URL}/uploadUrl', json=post_data)
        result = resp.json()
        
        assert result['status'] == 'success'

    @pytest.mark.skip(reason="需要包含iframe的测试页面")
    def test_iframe_route(self):
        """测试iframe请求拦截"""
        post_data = {
            'url': 'https://example.com/page-with-iframe',
            'timeout': 30,
            'iframe_route': True,
            'wait_urls': ['**/iframe_api/**'],
        }
        
        resp = requests.post(f'{BASE_URL}/uploadUrl', json=post_data)
        result = resp.json()
        
        assert result['status'] == 'success'


class TestHtmlOutput:
    """HTML输出测试"""

    def test_with_html(self):
        """测试返回HTML"""
        post_data = {
            'url': 'https://www.baidu.com',
            'timeout': 30,
            'html': True,
        }
        
        resp = requests.post(f'{BASE_URL}/uploadUrl', json=post_data)
        result = resp.json()
        
        assert result['status'] == 'success'
        assert result.get('text') is not None
        assert '<html' in result['text'].lower()

    def test_without_html(self):
        """测试不返回HTML"""
        post_data = {
            'url': 'https://www.baidu.com',
            'timeout': 30,
            'html': False,
        }
        
        resp = requests.post(f'{BASE_URL}/uploadUrl', json=post_data)
        result = resp.json()
        
        assert result['status'] == 'success'
        assert result.get('text') is None


class TestFailReturn:
    """失败返回测试"""

    def test_fail_return_enabled(self):
        """测试失败时返回数据"""
        post_data = {
            'url': 'https://www.baidu.com',
            'timeout': 5,
            'ensure_eles': [{'pattern': '#not_exist'}],
            'fail_return': True,
        }
        
        resp = requests.post(f'{BASE_URL}/uploadUrl', json=post_data)
        result = resp.json()
        
        assert result['status'] == 'fail'
        # fail_return=True 时应该返回部分数据
        assert result.get('text') is not None or result.get('wait_urls') is not None


class TestStepSpendTime:
    """步骤耗时测试"""

    def test_step_spend_time_returned(self):
        """测试返回步骤耗时"""
        post_data = {
            'url': 'https://www.baidu.com',
            'timeout': 30,
        }
        
        resp = requests.post(f'{BASE_URL}/uploadUrl', json=post_data)
        result = resp.json()
        
        assert result['status'] == 'success'
        assert result.get('step_spend_time') is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
