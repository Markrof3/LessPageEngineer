class FetcherMiddleware:
    """
    请求中间件
    """

    def __init__(self, settings):
        self.settings = settings

    def on_before_fetch(self, task):
        """请求前处理"""
        # 上线后特殊处理
        if self.settings["online"]:
            # 上线后浏览器API接口统一改为http://192.168.1.63:5001/chrome_get
            if task["url"] == 'http://192.168.1.63:5000/chrome_get':
                task["url"] = 'http://192.168.1.63:5001/chrome_get'
        else:
            # 本地浏览器API接口统一改为http://192.168.1.63:5000/chrome_get
            if task["url"] == 'http://192.168.1.63:5001/chrome_get':
                task["url"] = 'http://192.168.1.63:5000/chrome_get'

    def on_after_fetch(self, response, task):
        """结果前处理"""
        # 返回请求中的信息
        meta = dict()
        # 保存本次请求中的参数
        meta.update(task)
        response.meta = meta
