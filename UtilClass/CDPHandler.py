import time
import threading

from re import search
from queue import Queue
from urllib.parse import parse_qs
from loguru import logger
from concurrent.futures import ThreadPoolExecutor
from DrissionPage._base.driver import Driver

from LessPageEngineer.Utils.FetchTimeoutThread import function_with_timeout
from LessPageEngineer.Utils.Utils import url_pattern_cut, reduce_url
from LessPageEngineer.BaseClass.CDPBase import RouteDriver, Request, Response


class GlobalRouteExecutor:
    """全局线程池管理器，根据标签页数量动态调整worker数"""
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._executor = None
        self._route_count = 0
        self._max_workers = 10  # 初始值
        self._resize_lock = threading.Lock()
    
    def register_route(self):
        """注册一个RouteHandler，动态调整线程池大小"""
        with self._resize_lock:
            self._route_count += 1
            new_max = self._route_count * 2
            if self._executor is None:
                self._max_workers = max(new_max, 10)
                self._executor = ThreadPoolExecutor(
                    max_workers=self._max_workers,
                    thread_name_prefix="global_route"
                )
                logger.info(f"全局线程池创建，workers: {self._max_workers}")
            elif new_max > self._max_workers:
                # 需要扩容：创建新的更大的线程池
                old_executor = self._executor
                self._max_workers = new_max
                self._executor = ThreadPoolExecutor(
                    max_workers=self._max_workers,
                    thread_name_prefix="global_route"
                )
                # 旧线程池让它自然完成任务后关闭
                old_executor.shutdown(wait=False)
                logger.info(f"全局线程池扩容，workers: {self._max_workers}")
    
    def unregister_route(self):
        """注销一个RouteHandler"""
        with self._resize_lock:
            self._route_count = max(0, self._route_count - 1)
            # 不缩容，避免频繁重建线程池
    
    def submit(self, fn, *args, **kwargs):
        """提交任务到全局线程池"""
        if self._executor:
            return self._executor.submit(fn, *args, **kwargs)
        return None
    
    def shutdown(self):
        """关闭全局线程池"""
        with self._resize_lock:
            if self._executor:
                self._executor.shutdown(wait=True)
                self._executor = None
                self._route_count = 0
                self._max_workers = 10
                logger.info("全局线程池已关闭")


# 全局单例
_global_route_executor = GlobalRouteExecutor()


class Network(object):
    def __init__(self, driver):
        self._driver = driver
        self._driver.run('Network.enable')
        self._driver.set_callback('Network.loadingFailed', self.loading_failed)
        self.__canceled_list = set()
        self.received_url = []
        self.received_callback_func = None

    def open_response_received(self, call_back_func=None):
        self._driver.set_callback('Network.responseReceived', self.response_received)
        self.received_callback_func = call_back_func

    @property
    def canceled_list(self):
        return self.__canceled_list

    def clear_canceled_list(self):
        self.__canceled_list = set()

    # 当请求被取消时记录
    def loading_failed(self, **kwargs):
        if kwargs.get('canceled'):
            self.__canceled_list.add(kwargs['requestId'])

    # 停止websockets
    def stop(self):
        self._driver.stop()
        self.received_url.clear()

    # 获取响应状态
    def response_received(self, **kwargs):
        try:
            if self.received_callback_func:
                self.received_callback_func(**kwargs)
        except Exception as e:
            print("response_received有误", e)


class RouteHandler(RouteDriver):
    def __init__(self, page, time_out=60, driver=None, source_dict=None, show_log=0, use_cache_proxy=False,
                 get_response=False):
        """
        :param page: ChromiumBase对象
        :param time_out: 超时时间(默认60s)
        :param source_dict: 缓存文件Dict（传入会强制开启save_cache)
        """
        self._page = page
        self._address = page.address
        self._target_id = page._target_id
        self.show_log = show_log
        self.__disable_network = False
        self._timeout = time_out
        self.__route_item_queue = Queue()
        self.__patterns = []
        self._patterns_func = []
        self.__update_source_dict = True
        self.__disable_img_font = False
        self.__disable_source_list = ['Font', 'Image']
        self.__stop_handle_task = False
        super().__init__(self._target_id, 'page', self._address)
        self._driver = self
        # 是否使用缓存代理
        self.__use_cache_proxy = use_cache_proxy
        # self.__use_cache_proxy = False
        # 是否获取cdp响应
        self.__get_response = get_response
        self.source_dict = {} if source_dict == None else source_dict
        self.new_work = Network(self._driver)
        self.__route_id = str(round(time.time() * 1000))[-7:]
        self.__save_cache = False if source_dict == None else True
        if self.__save_cache:
            self.__run_cache()
        self.stop_event = threading.Event()
        self._driver_ids = []
        
        # 使用全局线程池
        _global_route_executor.register_route()
        # 启动单个消费线程，将任务提交到全局线程池
        self._consumer_thread = threading.Thread(
            target=self.__consume_queue, 
            daemon=True,
            name=f"route_consumer_{self.__route_id}"
        )
        self._consumer_thread.start()
        # self._page.browser.driver.set_callback('Target.targetCreated', self.iframe_route_create, immediate=True)


    def add_iframe(self, iframe_id):
        try:
            _driver = RouteDriver(iframe_id, 'page', self._address)
            _driver.replay_cdp_run_history(self._driver.cdp_run_history)
            print(f"添加targetId:{iframe_id}")
            print(self._driver.cdp_run_history)
            return True
        except Exception as e:
            return False

    def iframe_route_create(self, **kwargs):
        # iframe链接
        if kwargs['targetInfo']['type'] == 'iframe':
            _driver = RouteDriver(kwargs['targetInfo']['targetId'], 'page', self._address)
            _driver.replay_cdp_run_history(self._driver.cdp_run_history)
            _r = _driver.run('Page.getResourceTree')
            # self._driver_ids.append(_r)
            print(f"添加targetId:{kwargs['targetInfo']['targetId']}")
            print(self._driver.cdp_run_history)

    def route_start(self, urlPattern: str = None, requestStage: str = 'Request', callback_func=None):
        '''
        :param urlPattern:  过滤链接(伪正则写法)  允许使用通配符（ '*' -> 0 或更多， '?' ->正好为 1）。转义字符是反斜杠。省略等价于 "*"
        :param requestStage:   截获的请求阶段(Request、Response、Both)
        :param callback_func: 接收过滤链接请求/相应的回调函数(函数)
        :return: None
        '''
        # 入参类型检查
        assert callable(callback_func), "类型有误"
        assert isinstance(urlPattern, str), "类型有误"
        assert requestStage == 'Request' or requestStage == 'Response' or requestStage == 'Both', "未知的requestStage值"
        # patterns - 回调函数
        self._patterns_func.append(
            {'pattern': url_pattern_cut(urlPattern), 'func': callback_func,
             'stage': requestStage})
        # 拦截阶段 patterns重新发送
        if requestStage == 'Response':
            self.__patterns.append({'urlPattern': urlPattern, 'requestStage': 'Response'})
        self._driver.run('Fetch.enable', patterns=self.__patterns, record=True, _timeout=self._timeout)
        self._driver.set_callback('Fetch.requestPaused', self._requestPaused)

    def _requestPaused(self, **kwargs):
        if self.stop_event.is_set():
            return
        self.__route_item_queue.put(kwargs)

    def __consume_queue(self):
        """单线程消费队列，将任务提交到全局线程池"""
        while not self.stop_event.is_set():
            if self.__route_item_queue.empty():
                time.sleep(0.05)
                continue
            kwargs = self.__route_item_queue.get()
            _global_route_executor.submit(
                function_with_timeout, 
                self._handle_task, 
                run_timeout=5, 
                fail_func=None, 
                kwargs=kwargs
            )
    def create_route_object(self, kwargs):
        # 将request转换为类
        if not kwargs.get('responseStatusCode'):
            v = Request(**kwargs)
        else:
            # 填充更完整的responseHeaders
            v = Response(**kwargs)
        return v
    def _handle_task(self, kwargs):
        # 将request转换为类
        v = self.create_route_object(kwargs)
        if self.__disable_img_font:
            if v.resource_type in self.__disable_source_list:
                v.abort()
                return
        is_handle = False
        for pattern_func in self._patterns_func:
            # 匹配成功调用对应函数 response模式下 将request阶段的请求继续
            if search(pattern_func['pattern'], v.url) and v.type == pattern_func['stage']:
                pattern_func['func'](v, self.__route_id)
                is_handle = True
                break
            # if search(pattern_func['pattern'], v.url) and v.type == 'Request' and pattern_func[
            #     'stage'] == 'Response':
            #     v.continue_()
            #     is_handle = True
            #     break
            # elif search(pattern_func['pattern'], v.url):
            #     pattern_func['func'](v, self.__route_id)
            #     is_handle = True
            #     break
        # 当Route没有被处理 && 是否缓存为True时
        if not is_handle and self.__save_cache:
            self.__save_cache_request(v)

    # 根据source_dict进行缓存文件返回
    def __save_cache_request(self, route):
        if not self.source_dict.get(route.url):
            url = reduce_url(route.url, route.data)
        else:
            url = route.url
        if self.source_dict.get(url) and route.type == 'Request':
            if self.show_log >= 3:
                print(f"本地缓存 {route.url}")
            # 不使用缓存代理的情况下填充响应
            if not self.__use_cache_proxy:
                route.fullfillRequest(self.source_dict.get(url)['status_code'], self.source_dict.get(url)['headers'],
                                      body=self.source_dict.get(url)['body'])
            # 使用缓存代理的情况下继续响应
            else:
                route.continue_()
            return
        elif self.source_dict.get(url):
            if self.show_log >= 3:
                print(f"代理缓存 {route.url}")
            route.continue_()
            return
        elif route.type == "Response" and not self.source_dict.get(url) and route.body and self.__update_source_dict:
            if str(route.status_code).startswith('2'):
                self.source_dict[url] = {'body': route.body, 'headers': route.response_headers,
                                         'status_code': route.status_code}
            route.continue_()
            if self.show_log >= 2:
                print(f"截获响应 {route.url}")
            return
        else:
            if not self.__disable_network:
                # 拦截没被匹配的请求
                _r = route.continue_()
                if self.show_log >= 2:
                    print(f"继续请求 {route.url}")
            else:
                route.abort()
                if self.show_log >= 1:
                    print(f"请求被截停 {route.url}")

    def clear_cache(self, url):
        '''
        :param url: 清除指定缓存的链接
        :return: None
        '''
        assert isinstance(url, str), "类型有误"
        if self.source_dict.get(url):
            url = url
        elif '?' in url:
            url = url.split('?')[0] + ''.join([k for k, v in parse_qs(url.split('?')[-1]).items()])
        self.source_dict[url] = None

    def consumer_alive(self):
        """检查消费线程是否存活"""
        return self._consumer_thread.is_alive() if self._consumer_thread else False

    def __run_cache(self):
        self.__patterns.append({'urlPattern': "**", 'requestStage': 'Request'})
        # 是否截获Response阶段
        if self.__get_response:
            self.__patterns.append({'urlPattern': "**", 'requestStage': 'Response'})
        if self.__save_cache == True:
            self._driver.run('Fetch.enable', patterns=self.__patterns, _timeout=self._timeout, record=True)
            self._driver.set_callback('Fetch.requestPaused', self._requestPaused)
        else:
            self._driver.run('Fetch.disable', patterns=self.__patterns, _timeout=self._timeout, record=True)
            self._driver.set_callback('Fetch.requestPaused')

    @property
    def save_cache(self):
        return self.__save_cache

    @property
    def disable_network(self):
        return self.__disable_network

    @property
    def disable_img_font(self):
        return self.__disable_img_font

    @disable_img_font.setter
    def disable_img_font(self, value):
        assert isinstance(value, bool), "类型有误"
        self.__disable_img_font = value

    @property
    def update_source_dict(self):
        return self.__update_source_dict

    @update_source_dict.setter
    def update_source_dict(self, value):
        assert isinstance(value, bool), "类型有误"
        self.__update_source_dict = value

    @property
    def stop(self):
        return self.__stop_handle_task

    @stop.setter
    def stop(self, value):
        assert isinstance(value, bool), "期待Bool类型"
        if value:
            result = super().stop()
            if result:
                self.__stop_handle_task = value
                self.stop_event.set()
                # 注销全局线程池中的计数
                _global_route_executor.unregister_route()
                if self.show_log >= 0:
                    # 等待消费线程结束
                    while self.consumer_alive():
                        logger.info(f"{self._page._target_id[-5:]}的消费线程: {self._consumer_thread.ident}:是否存活：{self._consumer_thread.is_alive()}")
                        time.sleep(.5)

    @save_cache.setter
    def save_cache(self, value):
        ''' 缓存浏览器的所有请求至本地 '''
        assert type(value) == bool, "是否缓存本地需要Bool类型的数据"
        if self.__save_cache == value:
            return
        self.__save_cache = value
        self.__run_cache()

    @disable_network.setter
    def disable_network(self, value):
        ''' 缓存浏览器的所有请求至本地 '''
        assert type(value) == bool, "是否禁用网络需要Bool类型的数据"
        self.__disable_network = value



class Runtime(object):
    def __init__(self, page, driver=None, run_time_open=True, time_out=60):
        """
        :param page: ChromiumBase对象
        """
        self._page = page
        self._address = page.address
        self._target_id = page._target_id
        self._driver = Driver(self._target_id, 'page', self._address) if driver == None else driver
        self._time_out = time_out
        self.__run_time_open = run_time_open
        if self.__run_time_open:
            self._driver.run('Runtime.enable')
            self._driver.set_callback('Runtime.executionContextCreated', self.__context_create)
            self._driver.set_callback('Runtime.executionContextDestroyed', self.__context_destroyed)
            self._driver.set_callback('Runtime.exceptionThrown', self.__context_error)
        self._context_id_list = []
        self.__history_context_id_list = set()
        self.__stop = False

    def __context_create(self, **kwargs):
        self._context_id_list.append(kwargs['context']['id'])
        self.__history_context_id_list.add(kwargs['context']['id'])

    def __context_error(self, **kwargs):
        try:
            self._context_id_list.remove(kwargs['exceptionDetails']['executionContextId'])
        except Exception as e:
            logger.warning(e)

    def __context_destroyed(self, **kwargs):
        try:
            print(kwargs)
            self._context_id_list.remove(kwargs['executionContextId'])
        except Exception as e:
            logger.warning(e)

    def evaluate(self, evaluate_string, await_promise=False, timeout=None):
        '''

        :param evaluate_string: 在全局对象执行的js代码
        :param await_promise: 是否等待异步操作
        :param timeout: 暂时无效
        :return:
        '''
        # 不开启run_time_open的情况下不填入上下文
        if not self.__run_time_open:
            result = self._driver.run('Runtime.evaluate', expression=evaluate_string,
                                      awaitPromise=await_promise,
                                      allowUnsafeEvalBlockedByCSP=False, returnByValue=False,
                                      userGesture=True,
                                      # generatePreview=True,
                                      replMode=True,
                                      # contextId=self._context_id_list[-1]
                                      )
        else:
            if len(self._context_id_list) >= 1:
                result = self._driver.run('Runtime.evaluate', expression=evaluate_string,generatePreview=True,
                                          awaitPromise=await_promise,userGesture=True,includeCommandLineAPI=True,
                                          contextId=self._context_id_list[-1])
            else:
                result = {
                    'result': {'subtype': 'error', 'description': 'TypeError: Cannot read properties of undefined'}}
            if result.get('result', {}).get('subtype') == 'error':
                for context_id in self.__history_context_id_list:
                    template_result = self._driver.run('Runtime.evaluate', expression=evaluate_string,
                                                       awaitPromise=await_promise,userGesture=True,
                                                       contextId=context_id)
                    if template_result.get('result') and template_result['result'].get('subtype') != 'error':
                        return template_result
        return result

    @property
    def stop(self):
        return self.__stop

    @stop.setter
    def stop(self, value):
        assert isinstance(value, bool), "期待Bool类型"
        if value:
            result = self._driver.stop()