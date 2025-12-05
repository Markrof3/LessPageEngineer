import threading
import time
import json
import functools

import os
# from PIL import Image
# from io import BytesIO
from copy import deepcopy
from queue import Queue

from LessPageEngineering.UtilClass.CDPHandler import  RouteHandler, Runtime
from LessPageEngineering.UtilClass.FetchRequest import FetchRequest
from LessPageEngineering.UtilClass.task_components import CookieManager
# from LessPageEngineering.JavaScriptFunc.Slide import SLIDE_FUNC as slide_js
# from LessPageEngineering.JavaScriptFunc.SlideByClassName import SLIDE_FUNC as slide_js_class
from LessPageEngineering.Utils.Utils import b64encode


# 超时装饰器
def check_time_out_decorator(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        while True:
            chrome = self.chrome
            is_time_out = self.check_timeout()
            if is_time_out:
                result = self.stop_chrome_loading(False, func_name='超时了')
                if result:
                    result.update({'status': 'fail', 'message': '超时了', 'step_spend_time': chrome.step_spend_time,
                                   'error_reason': chrome.error_reason, })
                else:
                    result = {'status': 'fail', 'message': '超时了', 'error_reason': chrome.error_reason,
                              'step_spend_time': chrome.step_spend_time}
                return result
            result = func(self, *args, **kwargs)
            if result != None:
                return result
    return wrapper

class TaskHandle:
    def __init__(self, handle_data, run_time_cache, data_manger, redis_cache, cache_proxy, fetch_show_log, logger, det):
        self._handle_data = handle_data
        self.init_handle_data()  # 初始化chrome_class
        self.is_keep_session = False
        self.run_time_cache = run_time_cache
        self.data_manger = data_manger
        self.redis_cache = redis_cache
        self.cache_proxy = cache_proxy
        self.show_log_level = fetch_show_log
        self.logger = logger
        self.det = det
        self.step_spend_time = {}
        # 线程script running
        self.script_thread_stop_event = None
        self.chrome = None
        # 关注的iframe list
        self.focus_iframe_id = Queue()
        self.focus_iframe_event = threading.Event()
        self.focus_iframe_threading = threading.Thread(target=self.add_iframe_to_route)
        self.focus_iframe_event.set()
        
        # 组件初始化
        self.cookie_manager = CookieManager()

    # 设定mitmproxy全局代理
    def set_mitmproxy_global_proxy(self):
        if self.handle_data.get('global_proxy') and self.redis_cache:
            self.redis_cache.upload_proxy_to_redis(self.handle_data['global_proxy'], self.handle_data['timeout'])

    # 是否加载iframe route
    @property
    def iframe_load_status(self):
        return False if self.focus_iframe_event.is_set() else True

    def add_iframe_to_route(self):
        while not self.focus_iframe_event.is_set():
            i = self.focus_iframe_id.get()
            is_success = self.chrome.route.add_iframe(i['id'])

    def init_chrome_class(self, chrome, chrome_session_id):
        chrome.fetch_request = None
        chrome.settings = {}
        chrome.iframe = None
        chrome.iframe_route = None
        chrome.iframe_ele = None
        chrome.iframe_s_eles = None
        chrome.iframe_fetch_request = None
        chrome.wait_ele_dict = None
        chrome.js_result = None
        chrome.error_reason = None
        chrome.step_spend_time = self.step_spend_time
        # 重置错误原因
        chrome.error_reason = None
        chrome.settings = self.handle_data
        self.is_keep_session = self.handle_data.get('session_id') != None and self.handle_data.get('session_id') == \
                               chrome_session_id
        self.after_session_init_handle_data()
        self.chrome = chrome
        # 线程script running
        self.script_thread_stop_event = threading.Event() if self.handle_data.get('thread_script') == True else None

    # 初始化handle_data
    def init_handle_data(self):
        init_data = {
            'url': 'about:blank',  # 请求链接
            'disable_network': False,  # 禁止非拦截的链接网络请求
            'disable_img_font': False,  # 禁止图片、css文件加载
            'timeout': 60,  # 默认超时时间
            'key_replace': False,  # 是否替换key
            'key_save': False,  # 是否保存key
            'ensure_all': True,  # 是否确认所有元素正确加载
            'run_time_enable': True,  # 是否开启cdp Runtime.enable
            'thread_script': False,  # script是否以线程模式启动
            'new_context': False,  # 是否创建新的上下文(不同上下文之间cookie不会共享)
            'html': False,  # 是否需要html
            'iframe_ele': None,  #  页面中的iframe 当请求链接有iframe时，防止因元素嵌套在iframe导致ensure_eles无法正常运行
            'iframe_route':False, # 是否需要监听iframe中的请求
            'script_error_reload_page': True,  # 执行script脚本出错时是否重新加载页面
            'cookies': False,  # 是否返回页面的Cookies
            'session_storage': False,  # 是否返回页面的session_storage
            'local_storage': False,  # 是否返回页面的local_storage
            'global_proxy': None,  # 是否使用mitmproxy全局代理
            'reset_tcp_connect': False,  # 重置浏览器所有tcp链接 注意 启动该项会极大影响请求速度
        }
        init_data.update(self._handle_data)
        self.handle_data = init_data

    # 第二次初始化
    def after_session_init_handle_data(self):
        init_data = {
            'clear_cookies': not (self.is_keep_session and self._handle_data.get('clear_cookies') in (False,None)) and (self._handle_data.get('clear_cookies') in (True, None))
        }
        self.handle_data.update(init_data)


    # 检查是否超时
    def check_timeout(self):
        if time.time() - self.chrome.start_time >= self.handle_data['timeout']:
            return True
        return False

    # 清理cookies（委托给CookieManager）
    def clear_cookies(self):
        self.cookie_manager.clear_cookies(self.handle_data.get('clear_cookies', False))

    # 设置cookies（委托给CookieManager）
    def set_cookies(self):
        self.cookie_manager.set_cookies(self.handle_data.get('set_cookies'))

    # 重置浏览器所有的TCP(注意是所有！！！！)
    def reset_tcp_connect(self):
        if self.handle_data['reset_tcp_connect']:
            if not self.chrome.page._url == 'chrome://net-internals#sockets':
                self.chrome.page.get('chrome://net-internals#sockets')
                self.chrome.page.run_time = Runtime(self.chrome.page, run_time_open=False)
            _r = self.chrome.page.run_time.evaluate("document.getElementById('sockets-view-flush-button').click()")

    # 设置session_storage（委托给CookieManager）
    def set_session_storage(self):
        self.cookie_manager.set_session_storage(self.handle_data.get('set_session_storage'))

    # 设置local_storage（委托给CookieManager）
    def set_local_storage(self):
        self.cookie_manager.set_local_storage(self.handle_data.get('set_local_storage'))

    def _init_route_settings(self, route):
        # 禁用图片
        if self.handle_data.get('disable_img_font'):
            route.disable_img_font = True
        # 禁用网络请求
        if self.handle_data.get('disable_network'):
            route.disable_network = True

    def _load_route(self, chrome):
        source_dict = None
        # 有线上缓存(初始化)
        if self.handle_data.get('key'):
            r_source_dict = self.run_time_cache.search_source_dict(self.handle_data['key'])
            if r_source_dict:
                source_dict = r_source_dict
            else:
                source_dict = self.data_manger.load_data(self.handle_data['key'])
                self.run_time_cache.add_source_dict(self.handle_data['key'], source_dict)
                if source_dict and self.cache_proxy and self.redis_cache:
                    # 使用代理缓存时，需要删除放行链接匹配的缓存
                    self.redis_cache.upload_cache_to_redis(deepcopy(source_dict))
                    wait_urls = self.handle_data.get('wait_urls', [])
                    self.redis_cache.delete_cache_from_redis(source_dict, wait_urls)
        if source_dict:
            # 使用deepcopy 防止污染source_dict
            route = RouteHandler(chrome, source_dict=deepcopy(source_dict),
                          show_log=0,
                          use_cache_proxy=True if self.cache_proxy else False,
                          get_response=self.handle_data['key_save'] or self.handle_data['key_replace'],
                          )
        else:
            route = RouteHandler(chrome, source_dict={},
                          show_log=0,
                          use_cache_proxy=True if self.cache_proxy else False,
                          get_response=self.handle_data['key_save'] or self.handle_data['key_replace'],
                          )
        self._init_route_settings(route)
        return route

    # 加载route类
    def load_route(self):
        if (self.handle_data['key_save'] or self.handle_data.get('wait_urls') or self.handle_data[
            'key_replace'] or self.handle_data.get('key')) and not self.chrome.route:
            self.chrome.route = self._load_route(self.chrome)
        elif self.chrome.route:
            self._init_route_settings(self.chrome.route)
    # 加载iframe route
    def load_iframe_route(self):
        if not self.chrome.route or  not self.handle_data.get('iframe_route'):
            return
        self.focus_iframe_event.clear()
        self.focus_iframe_threading.start()

    # 加载fetch_request类
    def load_fetch_request(self):
        # 要等待的链接
        if self.handle_data.get('wait_urls'):
            self.chrome.fetch_request = FetchRequest(self.chrome,
                                                     show_log=self.show_log_level,
                                                     logger=self.logger)

    # 加载run_time类
    def load_run_time(self):
        # Runtime
        if self.handle_data.get('run_time') and not self.chrome.run_time:
            self.chrome.run_time = Runtime(self.chrome, run_time_open=self.handle_data['run_time_enable'])
            self.chrome.set.load_mode.normal()
        else:
            self.chrome.set.load_mode.none()

    # 切换iframe以及route(不稳定，测试)
    def change_iframe_route(self):
        iframe_ele = self.handle_data.get('iframe_ele')
        while True:
            try:
                if self.chrome.get_frames(iframe_ele):
                    iframe = self.chrome.get_frames(iframe_ele)[0]
                    break
            except Exception as e:
                pass
        self.chrome.iframe_route = RouteHandler(iframe, driver=iframe._driver,
                                         source_dict=deepcopy(self.chrome.route.source_dict),
                                         show_log=0,
                                         use_cache_proxy=True if self.cache_proxy else False,
                                         get_response=self.handle_data['key_save'] or self.handle_data['key_replace'],
                                         )
        self.chrome.iframe_fetch_request = FetchRequest(self.chrome,
                                                        show_log=self.show_log_level,
                                                        logger=self.logger)
        self.chrome.iframe = iframe
        self.chrome.iframe_ele = iframe.ele
        self.chrome.iframe_s_eles = iframe.s_eles
        self.logger.debug(f"{self.chrome._target_id[-5:]} 已切换iframe Route")

    # 切换请求页面加载模式
    def load_run_mode(self):
        # 强制加载模式
        if self.handle_data.get('fast') == True:
            self.chrome.set.load_mode.none()
        elif self.handle_data.get('fast') == False:
            self.chrome.set.load_mode.normal()

    # 启动切换iframe
    def load_iframe(self):
        # iframe
        if self.handle_data.get('iframe_ele'):
            t1 = threading.Thread(target=self.change_iframe_route)
            t1.daemon = True
            t1.start()

    # 设置浏览器UA
    def set_ua(self):
        # 设置UA
        if self.handle_data.get('ua'):
            self.chrome.set.user_agent(self.handle_data.get('ua'))
        # 无头模式
        elif 'Headless' in self.chrome.user_agent:
            self.chrome.set.user_agent(self.chrome.user_agent.replace('Headless',''))
    # 获取/生成Key
    def get_key(self):
        key = None
        # 没有key的情况下导出 source_dict
        if not self.handle_data.get('key'):
            # key_save 是否保存key
            if self.handle_data.get('key_save') or self.handle_data.get('key_replace'):
                key = b64encode(str(self.chrome.url).encode('utf-8')).decode('utf-8')
                source_dict = self.chrome.route.source_dict
                # 更新wait_urls中的响应
                if self.chrome.fetch_request:
                    source_dict.update(self.chrome.fetch_request.source_dict)
                self.data_manger.dump_data(key, self.chrome.route.source_dict, self.handle_data['key_replace'])
        else:
            key = self.handle_data.get('key')
            if self.handle_data.get('key_replace'):
                self.data_manger.dump_data(key, self.chrome.route.source_dict, self.handle_data['key_replace'])
        if self.handle_data['key_replace']:
            self.run_time_cache.drop_source_dict(key)
        return key

    # 请求空白页面
    def get_blank_page(self):
        if not self.is_keep_session:
            self.chrome.get('about:blank')

    # 请求页面
    def get_url(self):
        if not self.is_keep_session:
            self.chrome.get(url=self.handle_data['url'])

    # task任务失败
    def fail_reload(self):
        if self.chrome:
            # 停止浏览器的加载
            self.chrome.stop(join=True)

    # 线程 请求页面
    def threading_get_url(self):
        self.chrome.refresh(ignore_cache=True)

    # 刷新页面
    def refresh_chrome(self):
        # 停止浏览器的加载, 阻塞模式
        self.chrome.stop(join=True)
        if self.chrome.route:
            # 初始化Route
            self.chrome.route = self.load_route()
        if self.chrome.fetch_request:
            source_dict = self.chrome.fetch_request.source_dict
            self.chrome.fetch_request = FetchRequest(self.chrome,
                                                     show_log=self.show_log_level,
                                                     source_dict=source_dict, logger=self.logger)
        self.logger.debug(f"{self.chrome._target_id[-5:]} 刷新页面")
        t1 = threading.Thread(target=self.threading_get_url)
        t1.start()
        get_url_time = time.time()
        return get_url_time

    # 线程任务 启动run_script
    def _run_script_threading(self):
        while not self.script_thread_stop_event.is_set():
            self._run_script(error_retry=False)
            time.sleep(.3)
        return

    # 等待iframe的元素加载
    @check_time_out_decorator
    def wait_iframe_pattern(self):
        if self.chrome.iframe:
            return True

    # 等待指定的资源链接
    @check_time_out_decorator
    def wait_img_url_source(self, script_item):
        source_list = self.chrome.fetch_request.search_source_dict(
            script_item.get('img_urls'))
        if script_item.get('img_urls') and len(source_list) >= 2:
            return source_list

    @check_time_out_decorator
    def _run_script(self, error_retry=True):
        time_sleep = .1
        try:
            if isinstance(self.handle_data.get('script'), list):
                for script_item in self.handle_data['script']:
                    # 元素事件
                    if script_item.get('pattern'):
                        if script_item.get('after_iframe') and self.handle_data.get('iframe_ele'):
                            self.wait_iframe_pattern()
                        # 有after_iframe参数时使用iframe_ele
                        ele = self.chrome.ele(script_item['pattern'], timeout=10) if not script_item.get(
                            'after_iframe') else self.chrome.iframe_ele(script_item['pattern'], timeout=10)
                        # 点击事件
                        if script_item['function'] == 'click':
                            ele.click(by_js=True if script_item.get('by_js') else False)
                        elif script_item['function'] == 'double_click':
                            ele.click.multi(2)
                        elif script_item['function'] == 'input':
                            if script_item.get('value') == 'activate':
                                file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f'_r.{"jpg" if not script_item.get("suffix") else script_item.get("suffix")}')
                                with open(file_path, 'wb') as fp:
                                    fp.write(b'000000000000')
                                ele.input(file_path, clear=True)
                            else:
                                ele.input(script_item.get('value'), clear=True)
                        # 滑块事件
                        # if script_item['function'] == 'slide':
                        #     source_list = self.wait_img_url_source(script_item)
                        #     back_img, slide_img = (source_list[-1]['body'], source_list[-2]['body']) if len(
                        #         source_list[-1]['body']) > len(source_list[-2]['body']) else (
                        #         source_list[-2]['body'], source_list[-1]['body'])
                        #     # 图片原始大小
                        #     origin_width, _ = Image.open(BytesIO(back_img)).size
                        #     back_img_size_width = None
                        #     if script_item.get('background_img_pattern'):
                        #         # 图片在页面中的大小
                        #         back_img_size_width = \
                        #             self.chrome.ele(script_item.get('background_img_pattern')).rect.size[0]
                        #     slide_target = self.det.slide_match(slide_img, back_img, True)['target']
                        #     # 缩放系数- 有scale参数时使用scale，无则使用计算出来的系数，否则默认1
                        #     scale = script_item.get('scale') if script_item.get(
                        #         'scale') else back_img_size_width / origin_width if script_item.get(
                        #         'background_img_pattern') else 1
                        #     if script_item.get('run_js'):
                        #         slide_way = round(slide_target[0] * scale)
                        #         r_js = ''
                        #         if script_item.get('slide_button_id'):
                        #             r_js = slide_js.replace('id_value', script_item['slide_button_id']).replace(
                        #                 'slide_way', str(slide_way))
                        #         elif script_item.get('slide_button_class'):
                        #             r_js = slide_js_class.replace('id_value', script_item['slide_button_class']).replace(
                        #                 'slide_way', str(slide_way))
                        #         self.chrome.run_time.evaluate(r_js)
                        #     else:
                        #         ele.drag(round(slide_target[0] * scale), 1, 1)
                    # js事件
                    elif script_item.get('run_js'):
                        if script_item.get('wait_async') == True:
                            result = json.dumps(
                                self.chrome.run_time.evaluate(script_item.get('run_js'), await_promise=True))
                        else:
                            result = json.dumps(
                                self.chrome.run_time.evaluate(script_item.get('run_js'), await_promise=False))
                        # if 'exception' in result or 'error' in result:  # 暂时停止
                        if 'exception' in result:  # 暂时停止
                            raise ValueError(f"js: {script_item.get('run_js')}执行有误 {result}")
                        if not self.chrome.js_result:
                            self.chrome.js_result = [{'js': script_item.get('run_js'), 'result': result}]
                        else:
                            self.chrome.js_result.append({'js': script_item.get('run_js'), 'result': result})
                        time.sleep(0.1)
                    else:
                        return {'status': 'error', 'message': '未知的script类型'}
                    time.sleep(time_sleep)
                return True
            else:
                return {'status': 'error', 'message': 'script必须是list类型'}
        except Exception as e:
            # self.logger.error(f"执行script出错{e}")
            if error_retry:
                if self.handle_data['script_error_reload_page']:
                    self.chrome.get(url=self.chrome.url)
            else:
                return

    # 等待数据填充
    @check_time_out_decorator
    def wait_fill_data(self):
        is_pass, error_reason = self.chrome.fetch_request.check_wait_urls()
        self.chrome.error_reason = error_reason
        if is_pass:
            return True

    # 停止浏览器加载并且获取请求结果
    def stop_chrome_loading(self, status, func_name=''):
        self.chrome.stop(fake_stop=True)
        if status or (not status and self.handle_data.get('fail_return')):
            key = self.get_key()
            result = {
                # 浏览器页面
                'text': self.chrome.html if self.handle_data['html'] else None,
                # 过程使用的key or 生成的key
                'key': key,
                # 等待链接情况
                'wait_urls': self.chrome.fetch_request.intercept_urls if self.chrome.fetch_request else None,
                # 等待元素情况
                'wait_eles': self.chrome.wait_ele_dict if self.chrome.wait_ele_dict else None,
                # js执行结果
                'js_result': self.chrome.js_result if self.chrome.js_result else None,
                # 保持代理ip
                'keep_proxy': self.chrome.fetch_request.proxies if self.chrome.fetch_request and self.chrome.fetch_request.proxies else None,
                # 错误原因
                'error_reason': self.chrome.error_reason,
                # 步骤耗时
                'step_spend_time': self.chrome.step_spend_time
            }
            # 使用CookieManager收集Cookie/Storage结果
            result.update(self.cookie_manager.collect_result(self.handle_data))
        else:
            result = None
        return result

    # 判断页面是否加载成功
    def get_load_status(self):
        is_pass = False
        if not self.handle_data.get('ensure_eles') and not self.handle_data.get('wait_urls'):
            is_pass = True
        wait_eles = self.handle_data['ensure_eles'] if self.handle_data.get('ensure_eles') else []
        ele_error_reason = None
        wait_urls_error_reason = None
        # 等待元素策略
        if wait_eles:
            ensure_all = self.handle_data.get('ensure_all')
            if ensure_all:
                wait_count = 0
            else:
                wait_count = len(wait_eles) - 1
            wait_ele_dict = {}
            for wait_ele in wait_eles:
                try:
                    # 使用两种匹配模式 (仅仅使用s_eles模式可能出现bug，即eles能查找到，但s_eles查找不到的情况)
                    ele = self.chrome.s_eles(wait_ele['pattern']) or self.chrome.eles(wait_ele['pattern'], timeout=3)
                    ele = ele[0]
                    # self.logger.debug(f"获取元素:{wait_ele['pattern']}:{len(ele.text)}")
                    if not wait_ele.get('ensure_txt_len'):
                        wait_count += 1 if ele else 0
                        wait_ele_dict[wait_ele['pattern']] = {'load': True} if ele else {'load': False}
                    else:
                        ensure_txt_len = wait_ele.get('ensure_txt_len')
                        wait_count += 1 if len(ele.text) >= ensure_txt_len else 0
                        wait_ele_dict[wait_ele['pattern']] = {'load': True, 'txt_len': len(ele.text)} if len(
                            ele.text) >= ensure_txt_len else {'load': False}
                    if wait_count >= len(wait_eles):
                        self.chrome.wait_ele_dict = wait_ele_dict
                        is_pass = True
                        break
                except Exception as e:
                    ele_error_reason = f"条件{wait_ele}不满足"
        # 等待链接策略
        elif self.handle_data.get('wait_urls'):
            is_pass, wait_urls_error_reason = self.chrome.fetch_request.check_wait_urls()
        self.chrome.error_reason = ele_error_reason if ele_error_reason else wait_urls_error_reason
        return is_pass

    # 执行用户脚本
    def run_script(self):
        if self.handle_data.get('script'):
            if self.handle_data.get('thread_script') == True:
                script_thread = threading.Thread(target=self._run_script_threading)
                script_thread.daemon = True
                script_thread.start()
            else:
                is_success = self._run_script()
                if is_success != True:
                    return is_success

    # 等待 等待条件完成
    @check_time_out_decorator
    def rendering_html(self):
        get_url_time = time.time()
        # 间隔刷新
        if self.handle_data.get('refresh'):
            # 请求链接间隔
            if time.time() - get_url_time >= self.handle_data.get('refresh_time') if self.handle_data.get(
                    'refresh_time') else time.time() - get_url_time >= 20:
                get_url_time = self.refresh_chrome()
        is_pass = self.get_load_status()
        # 数据包请求失败时立刻重试
        if self.chrome.fetch_request and self.chrome.fetch_request.error_get_data and not is_pass:
            self.logger.error("数据包请求异常")
            if self.handle_data.get('refresh'):
                get_url_time = self.refresh_chrome()
            else:
                result = self.stop_chrome_loading(status=False, func_name='数据包异常')
                if result:
                    result.update({'status': 'fail', 'message': '数据包请求异常'})
                else:
                    result = {'status': 'fail', 'message': '数据包请求异常', 'error_reason': self.chrome.error_reason}
                return result
        if is_pass:
            result = self.stop_chrome_loading(status=True, func_name='渲染成功')
            result.update({'status': 'success'})
            return result

    def _record_step(self, step_name):
        """记录步骤耗时（相对于上一步骤）"""
        current_time = time.time()
        duration = round(current_time - self._last_step_time, 3)
        self.step_spend_time[step_name] = duration
        self._last_step_time = current_time

    def init_run(self, chrome, chrome_session_id):
        self._start_time = time.time()
        self._last_step_time = self._start_time
        
        self.init_chrome_class(chrome, chrome_session_id)
        # 绑定CookieManager到chrome实例
        self.cookie_manager.bind_chrome(chrome)
        # self.get_blank_page()
        self._record_step('init_chrome')
        
        # 使用CookieManager处理Cookie初始化
        self.cookie_manager.setup(self.handle_data)
        self._record_step('cookie_setup')
        
        self.load_route()
        self._record_step('load_route')
        
        self.load_iframe_route()
        self._record_step('load_iframe_route')
        
        self.load_fetch_request()
        self._record_step('load_fetch_request')
        
        self.load_run_time()
        self._record_step('load_run_time')
        
        if not chrome.settings.get('ensure_eles') and not chrome.settings.get('wait_urls'):
            chrome.set.load_mode.normal()
        self.load_run_mode()
        self._record_step('load_run_mode')
        
        self.set_ua()
        self._record_step('set_ua')
        
        self.load_iframe()
        self._record_step('load_iframe')
        
        self.set_mitmproxy_global_proxy()
        self._record_step('set_mitmproxy_global_proxy')
        
        self.reset_tcp_connect()
        self._record_step('reset_tcp_connect')
    def _run(self, chrome):
        self.get_url()
        self._record_step('get_url')
        
        # 使用CookieManager处理Storage设置
        self.cookie_manager.setup_storage(self.handle_data)
        self._record_step('storage_setup')
        
        result = self.run_script()
        self._record_step('run_script')
        if result:
            return result
        
        # 有fill_data时需要等待
        if chrome.fetch_request and chrome.fetch_request.fill_data_flag:
            result = self.wait_fill_data()
            if isinstance(result, dict):
                return result
        self._record_step('wait_fill_data')
        
        result = self.rendering_html()
        self._record_step('rendering_html')
        
        # 计算总耗时
        self.step_spend_time['_total'] = round(time.time() - self._start_time, 3)
        return result

    # 主函数
    def run(self, chrome):
        result = self._run(chrome)
        if self.script_thread_stop_event:
            self.script_thread_stop_event.set()
        self.focus_iframe_event.set()
        return result