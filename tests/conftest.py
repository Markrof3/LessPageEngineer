"""
pytest 配置文件 - 共享 fixtures
"""
import pytest
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def base_post_data():
    """基础请求数据"""
    return {
        'url': 'https://www.baidu.com',
        'timeout': 30,
    }


@pytest.fixture
def post_data_with_wait_urls():
    """带等待链接的请求数据"""
    return {
        'url': 'https://www.baidu.com',
        'timeout': 30,
        'wait_urls': ['**/sugrec**'],
    }


@pytest.fixture
def post_data_with_ensure_eles():
    """带等待元素的请求数据"""
    return {
        'url': 'https://www.baidu.com',
        'timeout': 30,
        'ensure_eles': [{'pattern': '#su'}],
    }


@pytest.fixture
def post_data_with_script():
    """带脚本执行的请求数据"""
    return {
        'url': 'https://www.baidu.com',
        'timeout': 30,
        'run_time': True,
        'script': [{'run_js': 'return document.title'}],
    }
