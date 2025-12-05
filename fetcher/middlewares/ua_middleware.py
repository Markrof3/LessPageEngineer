import random
from fake_useragent import UserAgent


class UAMiddleware:
    """
    UA中间件
    """

    def __init__(self, settings):
        self.settings = settings

        # ua列表(10个)
        self.ua_list = [
            "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2227.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2226.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 6.4; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2225.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2225.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 5.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2224.3 Safari/537.36",
            "Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/37.0.2049.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 4.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/37.0.2049.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/36.0.1985.67 Safari/537.36",
            "Mozilla/5.0 (Windows NT 5.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/36.0.1985.67 Safari/537.36",
            "Mozilla/5.0 (Windows NT 5.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.3319.102 Safari/537.36",
        ]

    def get_random_ua(self, is_fake_ua=False):
        """Return a ua if possible"""
        if is_fake_ua:
            return UserAgent().random
        else:
            return random.choice(self.ua_list)

    def on_before_fetch(self, task):
        """请求前处理"""
        if task.get("auto_ua", False):
            if not isinstance(task["auto_ua"], bool):
                raise Exception("auto_ua值设置错误")
            if "headers" not in task:
                task["headers"] = {}
            # 默认使用fake_useragent
            is_fake_ua = task.get("is_fake_ua", True)
            if not isinstance(is_fake_ua, bool):
                raise Exception("is_fake_ua值设置错误")
            ua = self.get_random_ua(is_fake_ua)
            task["headers"]['User-Agent'] = ua

    def on_after_fetch(self, response, task):
        """结果前处理"""
        # 保存请求中的ua信息
        if task.get("headers", {}).get('User-Agent'):
            response.meta["ua"] = task["headers"]['User-Agent']
