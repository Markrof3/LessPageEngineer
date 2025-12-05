import json
import time
import copy

from re import search, compile
from requests.utils import dict_from_cookiejar
from threading import Thread, Lock

from LessPageEngineering.fetcher import fetcher_settings
from LessPageEngineering.fetcher.fetcher import Fetcher
from LessPageEngineering.UtilClass.WebSocketSend import WebSocketClient
from LessPageEngineering.Utils.Utils import url_pattern_cut, get_brand_new_proxy, cookie_string_to_dict, decode_base64_in_chunks


class FetchRequest:
    def __init__(self, chrome, source_dict=None, call_back_func=None, logger=None, show_log=0):
        self.wait_url_dict = {}
        self.logger = logger
        # 资源字典， 含有响应内容
        self.source_dict = source_dict if source_dict != None else {}
        self.address = ''
        self.__error_get_data = False
        self.route = None
        # 开始事件
        self.start_time = time.time()
        self.call_back_func = call_back_func
        self.network_ids = {}
        self.show_log = show_log
        self.fetch = Fetcher(fetcher_settings.__dict__).fetch
        self.proxies = False
        self.back_proxies_list = []
        self.cookies = {}
        # 资源列表， 不含有
        self.intercept_urls = []
        self.lock = Lock()
        self.url = chrome.settings['url']
        # 填充数据
        self.fill_data_flag = False
        chrome.route._patterns_func.clear()
        self.__init_wait_urls_dict(chrome.route, chrome.settings)
        # network_received_open
        self.network_received_open = not chrome.settings['key_replace'] and not chrome.settings['key_save']
        # 当key_replace or key_save没有开启时，开启network.received
        if self.network_received_open:
            chrome.route.new_work.open_response_received(call_back_func=self.network_response_received)


    # 获取代理
    def get_proxies(self):
        while not self.__error_get_data:
            try:
                proxies = get_brand_new_proxy()
                if proxies['http'] in self.back_proxies_list:
                    continue
                try:
                    # 强制10秒 寻求优质代理
                    proxies = self.fetch(
                        url=self.url,
                        run_timeout=10,
                        proxies=proxies,
                    ).meta['proxies']
                    if not self.proxies:
                        self.proxies = proxies
                        if self.show_log >= 2:
                            self.logger.debug(f"获取代理成功:{self.proxies}")
                    return
                except Exception as e:
                    if self.proxies:
                        return
                    if self.show_log >= 1:
                        self.logger.error(f"获取代理失败:{e}")
                        self.back_proxies_list.append(proxies['http'])
            except Exception as e:
                time.sleep(1)
                if self.show_log >= 1:
                    self.logger.warning(f"{e}，等待0.5")

    @property
    def error_get_data(self):
        return self.__error_get_data

    # 添加资源字典&计数器更新
    def add_success_count(self, url, wait_url=None, body=None, data=None, headers=None, status_code=200,
                          add_source_dict=True, requestId=None):
        if not wait_url:
            for r_wait_url in self.wait_url_dict:
                if search(r_wait_url['pattern'], url) and (not r_wait_url.get('body_pattern') or (
                        r_wait_url.get('body_pattern') and search(r_wait_url['body_pattern'],
                                                                  data if data else ''))):
                    wait_url = r_wait_url
                    break
        if wait_url:
            wait_url['count'] -= 1
            if self.show_log >= 2:
                self.logger.debug(f"{self.address}, 拦截到响应:{url} 耗时:{round(time.time() - self.start_time, 2)}")
            if add_source_dict:
                self.source_dict[url] = {'body': body, 'headers': headers,
                                         'status_code': status_code, 'data': data, 'requestId': requestId}
        if wait_url:
            self.add_response(wait_url, url, requestId)
        return wait_url if wait_url else {}

    def add_response(self, wait_urls, url, requestId):
        if wait_urls.get('get_response') != True:
            return
        for item in self.intercept_urls:
            if item['url'] == url:
                response_dict = self.route._driver.run('Network.getResponseBody',
                                                       requestId=requestId)
                item['response_b64'] = response_dict

    # 接收Network.responseReceived中的参数&更新计数器
    def network_response_received(self, **kwargs):
        if kwargs['response']['protocol'] == 'data' and not kwargs['response']['url'].startswith('http'):
            return
        self.add_success_count(
            url=kwargs['response']['url'], status_code=kwargs['response']['status'],
            body=None, headers=kwargs['response']['headers'], data=self.network_ids.get(kwargs['requestId'], [""])[-1], requestId=kwargs['requestId']
        )

    # PS：这个函数是启一个线程调用的
    # 对捕获的请求&响应进行处理
    def fetch_request(self, route, route_id):
        # 保持Url
        url = route.url
        if route.type == 'Response':
            # 没有响应体
            if not route.body and 'favicon.ico' not in route.url:
                if self.show_log >= 1:
                    self.logger.error(f"{route.url} 响应体为空")
                self.__error_get_data = True
                return
            else:
                if str(route.status_code).startswith('2'):
                    wait_url = self.add_success_count(url=route.url, body=route.body, data=route.data,
                                                      headers=route.response_headers, status_code=route.status_code)
                    if wait_url.get('modify') and isinstance(wait_url['modify'], dict):
                        _body = route.body.replace(wait_url['modify']['be_replace'].encode(),wait_url['modify']['to_replace'].encode())
                        res = route.fullfillRequest(
                            # 若响应为3开头的状态码，则不允许填充状态码
                            responseCode=route.status_code,
                            responseHeaders=route.response_headers, body=_body
                        )
                        return
            # 填充响应头
            route.continue_()
        else:
            # 添加进network_ids 后续判断该请求是否失败
            self.network_ids[route.network_id] =  (route.url, route.data)
            if self.show_log >= 3:
                self.logger.info(f"{self.address}, 拦截到请求:{route.url} 耗时：{round(time.time() - self.start_time, 2)}")
            # 添加intercept_urls 后续返回至客户端
            self.intercept_urls.append(
                {'url': route.url, 'data': route.data, 'headers': copy.deepcopy(route.headers),
                 'method': route.method})
            for wait_url in self.wait_url_dict:
                if search(wait_url['pattern'], url) and (not wait_url.get('body_pattern') or (
                        wait_url.get('body_pattern') and search(wait_url['body_pattern'],
                                                                route.data if route.data else ''))):
                    # 获取状态码
                    status_code = wait_url.get('status_code')
                    # 有fill_data字段时填充
                    if wait_url.get('fill_data'):
                        if wait_url['fill_amount'] <= 0:
                            continue
                        # 填充响应头
                        if wait_url.get('headers') and isinstance(wait_url.get('headers'), dict):
                            fulfill_headers = wait_url.get('headers')
                        else:
                            fulfill_headers = {'origin': '123', 'content-type': 'application/json; charset=utf-8'}
                        # dict转str
                        if isinstance(wait_url.get('fill_data'), dict):
                            fill_data = json.dumps(wait_url.get('fill_data'), ensure_ascii=False)
                        else:
                            fill_data = wait_url.get('fill_data')
                        res = route.fullfillRequest(
                            # 状态码默认200
                            responseCode=status_code if status_code else 200, responseHeaders=fulfill_headers,
                            body=fill_data,
                            # filldata是否Base64
                            is_base64=True if wait_url.get('fill_data_b64') else False
                        )
                        if self.show_log >= 2:
                            self.logger.debug(f"{self.address}, 填充请求:{route.url}")
                        # 填充成功则 res为 {}
                        if not res and not self.network_received_open:
                            self.add_success_count(url=url, wait_url=wait_url, add_source_dict=False)
                        wait_url['fill_amount'] -= 1
                        return
                    # 有abort字段为True时 禁止该请求
                    elif wait_url.get('abort') == True:
                        self.add_success_count(wait_url=wait_url, url=url, add_source_dict=False)
                        if self.show_log >= 2:
                            self.logger.debug(f"{self.address}, 禁止链接:{route.url}")
                        route.abort()
                        return
                    # 有keep_proxy字段时则使用fetch请求
                    elif wait_url.get('keep_proxy') == True:
                        try:
                            start_time = time.time()
                            # 最大等待时间 20s
                            while not self.proxies:
                                time.sleep(.1)
                                if round(time.time() - start_time) > 10:
                                    break
                            if self.proxies == None:
                                raise ValueError('保持代理获取超时')
                            if route.headers.get('Cookie'):
                                # 更新 self.cookies
                                self.cookies.update(
                                    cookie_string_to_dict(route.headers['Cookie'])
                                )
                                # 删除请求头中的cookie
                                del route.headers['Cookie']
                            resp = self.fetch(
                                url=route.url,
                                data=route.data,
                                headers=route.headers,
                                proxies=self.proxies,
                                cookies=self.cookies,
                                method=route.method,
                                impersonate=wait_url.get('impersonate') if wait_url.get('impersonate') else 'chrome120',
                                random_ja3=True if wait_url.get('random_ja3') else False,
                                akamai_fp_random=False,
                                verify=False,
                                allow_redirects=False,
                                timeout=(30, 30)
                            )
                            r_cookies = {}
                            try:
                                r_cookies = dict_from_cookiejar(resp.cookies)
                            except Exception as e:
                                r_cookies = dict(resp.cookies)
                            self.cookies.update(r_cookies)
                            # headers必须转dict
                            res = route.fullfillRequest(
                                # 若响应为3开头的状态码，则不允许填充状态码
                                responseCode=resp.status_code if not status_code or str(resp.status_code).startswith(
                                    '3') else status_code,
                                responseHeaders=dict(resp.headers) if not wait_url.get('headers') else wait_url.get(
                                    'headers'), body=resp.content
                            )
                            if self.show_log >= 2:
                                self.logger.debug(
                                    f"{self.address} 代理请求数据包成功:{route.url}, 填充状态:{res} 响应状态码:{resp.status_code} 填充状态码:{status_code}")
                            if not res and not self.network_received_open:
                                # 添加进soure_dict中
                                self.add_success_count(wait_url=wait_url, url=route.url, body=resp.content,
                                                       headers=dict(resp.headers), status_code=resp.status_code,
                                                       data=route.data)
                            return
                        except Exception as e:
                            if self.show_log >= 1:
                                self.logger.error(
                                    f"{self.address} {route.url}代理请求数据包有误{e}  {self.__error_get_data}")
                            self.__error_get_data = True
                            route.abort()
                            return
            # 请求继续
            route.continue_()

    # 初始化wait_urls_dict
    def __init_wait_urls_dict(self, route, post_data):
        self.__error_get_data = False
        # 等待链接dict初始化
        self.address = route._page._target_id[-5:]
        self.route = route
        self.wait_url_dict = []
        self.intercept_urls = []
        for wait_url in post_data.get('wait_urls'):
            res_dict = {}
            if isinstance(wait_url, str):
                # key_save or key_replace为True时拦截响应阶段
                route.route_start(urlPattern=wait_url,
                            requestStage='Request',
                            callback_func=self.fetch_request if self.call_back_func == None else self.call_back_func)
                res_dict.update({'pattern': url_pattern_cut(wait_url), 'count': 1})
                self.wait_url_dict.append(
                    res_dict)
            elif isinstance(wait_url, dict):
                route.route_start(urlPattern=wait_url['url'],
                            requestStage='Response' if wait_url.get('modify') else 'Request',
                            callback_func=self.fetch_request if self.call_back_func == None else self.call_back_func,
                            )
                res_dict.update({'pattern': url_pattern_cut(wait_url['url']),
                                 'count': 1 if not wait_url.get('amount') else wait_url.get('amount'),
                                 'body_pattern': url_pattern_cut(wait_url['body']) if wait_url.get('body') else None,
                                 # 默认最大填充99次
                                 'fill_amount': 99
                                 })
                res_dict.update(wait_url)
                self.wait_url_dict.append(res_dict)
                # 填充数据flag
                if wait_url.get('fill_data'):
                    self.fill_data_flag = True
                # 保持代理
                if wait_url.get('keep_proxy') and self.proxies == False:
                    self.proxies = None
                    for _ in range(3):
                        t1 = Thread(target=self.get_proxies)
                        t1.daemon = True
                        t1.start()

    # 清除计数器
    def clear_count(self):
        for wait_url in self.wait_url_dict:
            wait_url['count'] = 1 if not wait_url.get('amount') else wait_url.get('amount')
        self.intercept_urls = []

    # 检查计数器是否为0
    def check_wait_urls(self):
        error_reason = None
        is_pass = True
        network_ids_copy = copy.copy(self.network_ids)
        canceled_list_copy = copy.copy(self.route.new_work.canceled_list)
        for network_id in network_ids_copy.keys():
            # 拷贝一份出来 防止因读取过程中集合仍然在添加 runtimeError
            if network_ids_copy[network_id][0] in canceled_list_copy:
                for wait_url in self.wait_url_dict:
                    if search(wait_url['pattern'], network_id[1]) and wait_url.get('abort') == True:
                        continue
                    if self.show_log >= 1:
                        # self.logger.error(f"有请求被取消了！{network_id[1]}")
                        pass
                    if wait_url['count'] > 0:
                        self.__error_get_data = True
                        return False, f"有请求被取消了！{network_id[1]}"
        for wait_items in self.wait_url_dict:
            if wait_items['count'] > 0:
                is_pass = False
                error_reason = f"条件{wait_items.get('url')}未满足"
                break
        return is_pass, error_reason

    # 搜索source_dict
    def search_source_dict(self, pattern):
        source_list = []
        pattern = compile(pattern.replace('**', '.*').replace('?', '\?'))
        # 拷贝 防止运行时修改字典内部数值报错
        keys_list = copy.copy(list(self.source_dict.keys()))
        for url in keys_list:
            if search(pattern, url):
                if not self.source_dict[url].get('body'):
                    response_dict = self.route._driver.run('Network.getResponseBody',
                                                           requestId=self.source_dict[url]['requestId'])
                    if response_dict.get('base64Encoded'):
                        self.source_dict[url]['body'] = decode_base64_in_chunks(response_dict['body'])
                    else:
                        self.source_dict[url]['body'] = response_dict['body'] if isinstance(response_dict['body'],
                                                                                            bytes) else response_dict[
                            'body'].encode()
                source_list.append(self.source_dict[url])
        return source_list
