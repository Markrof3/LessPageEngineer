#!/usr/bin/python
# -*- encoding: utf-8 -*-
# @File  :   fetcher.py
# @Time  :   2024/04/11 15:23:25
# @Author:   Dada

import requests
from random import randint, shuffle
from curl_cffi import requests as curl_requests
from curl_cffi import CurlOpt
from urllib3.exceptions import InsecureRequestWarning

from LessPageEngineering.fetcher.fetch_timeout_thread import request_with_timeout
from LessPageEngineering.fetcher.middlewares.fetcher_middleware import FetcherMiddleware
from LessPageEngineering.fetcher.middlewares.proxy_middleware import ProxyMiddleware
from LessPageEngineering.fetcher.middlewares.ua_middleware import UAMiddleware

# 禁用安全请求警告
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


class Fetcher:
    """
    请求器
    """

    def __init__(self, settings):
        self.settings = settings

        self.middlewares = [
            FetcherMiddleware(settings),
            UAMiddleware(settings),
            ProxyMiddleware(settings),
        ]
        # # request方法只允许下面的参数
        self.request_keys = [
            "method", "url", "params", "data", "headers", "cookies",
            "files", "auth", "timeout", "allow_redirects", "proxies",
            "hooks", "stream", "verify", "cert", "json"
        ]
        self.cipher_list = [
            'GREASE',
            'TLS_AES_128_GCM_SHA256',
            'TLS_AES_256_GCM_SHA384',
            'TLS_CHACHA20_POLY1305_SHA256',
            'TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256',
            'TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256',
            'TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384',
            'TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384',
            'TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305_SHA256',
            'TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305_SHA256',
            'TLS_ECDHE_RSA_WITH_AES_128_CBC_SHA',
            'TLS_ECDHE_RSA_WITH_AES_256_CBC_SHA',
            'TLS_RSA_WITH_AES_128_GCM_SHA256',
            'TLS_RSA_WITH_AES_256_GCM_SHA384',
            'TLS_RSA_WITH_AES_128_CBC_SHA',
            'TLS_RSA_WITH_AES_256_CBC_SHA',
        ]
        self.extra_fp = {
            "tls_signature_algorithms": [
                "ecdsa_secp256r1_sha256",
                "rsa_pss_rsae_sha256",
                "rsa_pkcs1_sha256",
                "ecdsa_secp384r1_sha384",
                "rsa_pss_rsae_sha384",
                "rsa_pkcs1_sha384",
                "rsa_pss_rsae_sha512",
                "rsa_pkcs1_sha512",
            ],
            "tls_grease": True,
            "tls_permute_extensions": False,
        }

    def on_before_fetch(self, task):
        """请求前处理"""
        for middleware in self.middlewares:
            middleware.on_before_fetch(task)

    def on_fetch(self, task):
        """发起请求前处理"""
        # 默认method为"get"
        if "method" not in task:
            task["method"] = "get"
        else:
            task["method"] = task["method"].upper()
        # 默认去除https认证
        if "verify" not in task:
            task["verify"] = False
        # 设置默认超时时间120秒
        if "timeout" not in task:
            task["timeout"] = self.settings["DEFAULT_TIMEOUT"]
        # 从task中获取请求信息
        new_kwargs = {key: task[key] for key in self.request_keys if key in task}

        # 获取请求器
        fetch = requests.request
        # curl 选项
        curl_options = {}

        # http版本控制
        if task.get("http_version"):
            # V1_0=1  please use HTTP 1.0 in the request */
            # V1_1=2  please use HTTP 1.1 in the request */
            # V2_0=3  please use HTTP 2 in the request */
            # V2TLS=4 use version 2 for HTTPS, version 1.1 for HTTP */
            # V2_PRIOR_KNOWLEDGE=5  please use HTTP 2 without HTTP/1.1 Upgrade */
            # V3=30   Makes use of explicit HTTP/3 without fallback.
            fetch = curl_requests.request
            new_kwargs["http_version"] = task["http_version"]
        elif "http2" in task:
            fetch = curl_requests.request
            if task.get("http2"):
                new_kwargs["http_version"] = 4  # 针对https使用2.0,针对http使用1.1
            else:
                new_kwargs["http_version"] = 2  # 针对http使用1.1
        # tls控制
        if task.get("impersonate"):
            fetch = curl_requests.request
            new_kwargs["impersonate"] = task["impersonate"]
        elif task.get("random_ja3"):
            fetch = curl_requests.request
            new_kwargs["impersonate"] = "chrome120"
        # akamai 指纹随机
        if task.get('akamai_fp_random'):
            fetch = curl_requests.request
            curl_options[CurlOpt.HTTP2_WINDOW_UPDATE] = randint(236455713, 2147483648)
            curl_options[CurlOpt.HTTP2_SETTINGS] = "1:65536;2:0;4:6291456;6:262144"  # chrome120
            curl_options[CurlOpt.HTTP2_PSEUDO_HEADERS_ORDER] = "masp"  # chrome120
            shuffle(self.cipher_list)
            # 椭圆曲线映射
            curve_list = ":".join([
                "X25519",  # 29 (0x1d)
                "prime256v1",  # 23 (0x17)
                "secp384r1"  # 24 (0x18)
            ])
            cipher_list = ":".join(self.cipher_list)
            curl_options[CurlOpt.SSL_CIPHER_LIST] = cipher_list.encode("utf-8")
            curl_options[CurlOpt.SSL_EC_CURVES] = curve_list.encode("utf-8")
            curl_options[CurlOpt.SSL_ENABLE_TICKET] = 1
            new_kwargs['curl_options'] = curl_options
            new_kwargs['extra_fp'] = self.extra_fp
        # 开启一个线程设置强制超时
        if "run_timeout" in task:
            run_timeout = task["run_timeout"]  # 超时时间
            if isinstance(run_timeout, bool) or not isinstance(run_timeout, int) or run_timeout < 0:
                raise Exception(f"run_timeout值设置错误 {run_timeout}")
            return request_with_timeout(fetch, run_timeout, **new_kwargs)
        else:
            return fetch(**new_kwargs)

    def on_after_fetch(self, response, task):
        """结果前处理"""
        for middleware in self.middlewares:
            middleware.on_after_fetch(response, task)

    def fetch(self, **kwargs):
        task = kwargs
        """发起请求"""
        self.on_before_fetch(task)
        response = self.on_fetch(task)
        self.on_after_fetch(response, task)
        return response
