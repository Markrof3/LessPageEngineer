import re
import json
import time
import requests
from hashlib import md5

from LessPageEngineer.Utils.FetchTimeoutThread import function_with_timeout


class ProxyMiddleware:
    """
    代理中间件
    """

    def __init__(self, settings):
        self.settings = settings

        self.proxy_auth = requests.auth.HTTPProxyAuth(
            settings["PROXY_AUTH_USERNAME"],
            settings["PROXY_AUTH_PASSWORD"]
        )
        self.proxy_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"}
        # 代理黑名单队列
        self.black_proxy_list = {"common": set()}

    def _update_proxy(self, auth):
        """更新代理"""
        proxy = None

        for idx, proxy_url in enumerate(self.settings["PROXY_URL_LIST"]):
            try:
                response = requests.get(proxy_url, headers=self.proxy_headers)
                if not response or response.status_code != 200:
                    raise Exception(response.status_code)
                proxy = response.text
                break
            except Exception as e:
                print(f"访问代理URL{idx + 1}出错：{repr(e)}")
        # 空代理检测
        if not proxy or str(proxy) == "0":
            print("代理不可用，等待3秒")
            raise ValueError("代理不可用，等待3秒")
        # 黑名单检测
        if proxy in self.black_proxy_list["common"]:
            raise ValueError(f"代理黑名单: {proxy}")
        if auth:
            proxies = {
                'http': "http://{}:{}@{}".format(self.settings["PROXY_AUTH_USERNAME"],
                                                 self.settings["PROXY_AUTH_PASSWORD"], proxy),
                'https': "http://{}:{}@{}".format(self.settings["PROXY_AUTH_USERNAME"],
                                                  self.settings["PROXY_AUTH_PASSWORD"], proxy),
            }
        else:
            proxies = {
                'http': "http://{}".format(proxy),
                'https': "http://{}".format(proxy),
            }
        return proxies

    def test_proxy(self, _proxies, auto_proxy_test):
        """测试代理"""
        # 初始化黑名单队列
        url_md5 = md5(auto_proxy_test['url'].encode()).hexdigest()
        if url_md5 not in self.black_proxy_list:
            self.black_proxy_list[url_md5] = set()
        # 判断代理是否存在黑名单中
        _proxies_md5 = md5(json.dumps(_proxies, sort_keys=True).encode()).hexdigest()
        if _proxies_md5 in self.black_proxy_list[url_md5]:
            # 黑名单不要打印
            raise ValueError(f"黑名单代理: {auto_proxy_test['url']}, 代理: {_proxies}")
        # 设置代理
        auto_proxy_test["proxies"] = _proxies
        # auto_proxy_test["auth"] = self.proxy_auth
        # 代理域名测试
        try:
            function_with_timeout(requests.request, auto_proxy_test["timeout"], **auto_proxy_test)
            print(f"代理成功: {auto_proxy_test['url']}, 代理: {_proxies}")
        except Exception:
            self.black_proxy_list[url_md5].add(_proxies_md5)
            print(f"代理域名测试失败: {auto_proxy_test['url']}, 代理: {_proxies}")
            raise ValueError(f"代理域名测试失败: {auto_proxy_test['url']}, 代理: {_proxies}")

    def get_proxy(self, auto_proxy_retry=True, auto_proxy_test={}, auth=True):
        """获取代理"""
        while True:
            try:
                # 获取代理
                _proxies = self._update_proxy(auth)
                # 代理域名测试
                if auto_proxy_test:
                    self.test_proxy(_proxies, auto_proxy_test)
                return _proxies
            except Exception as e:
                # 自动重试
                if auto_proxy_retry:
                    time.sleep(self.settings["PROXY_SLEEP_TIME"])
                    continue
                else:
                    print("无法获取可用代理")
                    raise e

    def on_before_fetch(self, task):
        """请求前处理"""
        # 代理白名单检测
        for white_proxy in self.settings["PROXY_WHITE_LIST"]:
            if re.search(white_proxy, task["url"]):
                return
        if task.get("proxies"):
            # task中已携带proxies
            # if "auth" not in task:
            #     task["auth"] = self.proxy_auth
            pass
        elif task.get("auto_proxy", False) and self.settings.get("PROXY_OPEN", True):
            # 代理值设置校验
            if not isinstance(task["auto_proxy"], bool):
                raise Exception("auto_proxy值设置错误")

            # 代理是否自动重试
            auto_proxy_retry = task.get("auto_proxy_retry", True)
            if not isinstance(auto_proxy_retry, bool):
                raise Exception("auto_proxy_retry值设置错误")

            # 代理是否需要域名测试
            auto_proxy_test = task.get("auto_proxy_test", {})
            if isinstance(auto_proxy_test, dict):
                if auto_proxy_test:
                    # 默认method为"get"
                    if "method" not in auto_proxy_test:
                        auto_proxy_test["method"] = "get"
                    # 默认去除https认证
                    if "verify" not in auto_proxy_test:
                        auto_proxy_test["verify"] = False
                    # url值校验
                    if not isinstance(auto_proxy_test.get("url"), str):
                        raise Exception("auto_proxy_test项url值设置错误")
                    # timeout值校验
                    if not auto_proxy_test.get("timeout"):
                        # 设置默认值
                        if task.get("run_timeout"):
                            auto_proxy_test["timeout"] = task["run_timeout"]
                        elif task.get("timeout"):
                            auto_proxy_test["timeout"] = task["timeout"]
                        else:
                            auto_proxy_test["timeout"] = self.settings["DEFAULT_TIMEOUT"]
                    # headers值校验
                    if not auto_proxy_test.get("headers"):
                        # 默认取当前任务中的headers
                        if task.get("headers", {}).get("User-Agent"):
                            auto_proxy_test["headers"] = {
                                "User-Agent": task["headers"]["User-Agent"]
                            }
            else:
                raise Exception("auto_proxy_test值设置错误")

            # 更新task中的代理
            if any([True for key in ["http2", "random_ja3", "http_version", "impersonate"] if key in task]):
                # 使用curl_cffi不支持字符串验证代理账号密码
                task.update({
                    "proxies": self.get_proxy(auto_proxy_retry, auto_proxy_test, auth=False),
                    "proxy_auth": (self.settings["PROXY_AUTH_USERNAME"], self.settings["PROXY_AUTH_PASSWORD"])
                })
            else:
                task.update({
                    "proxies": self.get_proxy(auto_proxy_retry, auto_proxy_test, auth=True)
                })

    def on_after_fetch(self, response, task):
        """结果前处理"""
        # 保存请求中的代理信息
        response.meta['proxies'] = task.get("proxies")
        # if "auth" in task:
        #     response.meta['auth'] = task["auth"]

        # 以下会被当成超时异常,让爬虫无限重试
        if response.meta.get("proxies"):
            proxy = response.meta["proxies"]["http"].split("@")[-1]
            proxy = proxy.split("//")[-1]
        # 代理返回码校验
        if response.status_code == 407:
            self.black_proxy_list["common"].add(proxy)
            raise ValueError("407 Proxy Authentication Required")
        # 代理返回内容异常
        if response.text.strip() in [
            "已经超过了您购买的时长",
            "连接目标地址超时",
            "目标地址不可用,或传输数据时发生错误,请重试."
        ]:
            self.black_proxy_list["common"].add(proxy)
            raise ValueError(response.text.strip())
