import os
import time
import atexit

from queue import Queue
from threading import Lock
from DrissionPage import ChromiumOptions

from LessPageEngineer.BaseClass.ChromeBase import LPE_WebPage


class Chrome:
    def __init__(self, settings, headless: bool = False, proxy_need: bool = True):
        self.settings = settings
        self.headless = headless
        self.proxy_need = proxy_need
        assert isinstance(headless, bool), '类型有误'
        assert isinstance(proxy_need, bool), '类型有误'
        # 当程序意外终止/正常结束时 会自动调用注册到atexist中的函数(理论上)
        self.page = None
        self.using_port = None

    def get_chrome(self, proxies: str = ''):
        assert isinstance(proxies, str), '类型有误'
        driver = ChromiumOptions()
        # 开启无头模式
        if self.settings['HEADER_LESS']:
            driver.headless()
        path = None
        for i in self.settings['BROWSER_PATH']:
            r_path = i['path'] if i.get('absolute_path') else os.getcwd() + i['path']
            if os.path.exists(r_path):
                path = r_path
                break
        if path:
            driver.set_browser_path(path)
        driver.set_argument('--disk-cache-dir',
                            value=f'{self.settings["CHROME_CACHE_SAVE_PATH"]}\ChromeUser{len(self.settings["BROWSER_PATH"])}')
        driver.set_user_data_path(f'{self.settings["CHROME_USER_PATH"]}\ChromeUser{len(self.settings["BROWSER_PATH"])}')

        if self.settings["CHANGE_BROWSER"]:
            self.settings['BROWSER_PATH'].remove(i)
        if self.headless:
            driver.headless()
        if self.using_port:
            driver.set_local_port(int(self.using_port))
        else:
            driver.auto_port()
        if self.settings['INCOGNITO']:
            # 无痕模式启动
            driver.incognito()
        # STABLE PART
        for stable_argument in self.settings['CHROME_STABLE_ARGUMENT']:
            if isinstance(stable_argument, tuple):
                driver.set_argument(stable_argument[0], stable_argument[1])
            else:
                driver.set_argument(stable_argument)
        # UPDATE PART
        for unstable_argument in self.settings['CHROME_UNSTABLE_ARGUMENT']:
            if isinstance(unstable_argument, tuple):
                driver.set_argument(unstable_argument[0], unstable_argument[1])
            else:
                driver.set_argument(unstable_argument)
        # FLAGS PART
        for flag in self.settings['CHROME_FLAGS']:
            if isinstance(flag, tuple):
                driver.set_flag(flag[0], flag[1])
            else:
                driver.set_flag(flag)
        if self.settings['EXTENSION_PATHS']:
            for extension_item in self.settings['EXTENSION_PATHS']:
                # 添加插件
                driver.add_extension(extension_item)
        if proxies:
            driver.set_proxy(proxies)
        elif self.proxy_need:
            driver.set_proxy(self.settings['UPSTREAM'])
        # 将quit函数注册到atexist中
        # 默认d模式创建对象
        page = LPE_WebPage(chromium_options=driver)
        print(f"{'-' * 10} 浏览器进程：{page.process_id}  浏览器运行地址：{page.address}   {'-' * 10}")
        # 当程序主进程结束时都会调用注册到atexit.register的函数
        atexit.register(self.__quit, page)
        self.using_port = page.address.split(':')[-1]
        return page

    def __quit(self, page):
        print(f"地址：{page.address} 进程:{page.process_id} 浏览器关闭")
        process_id = page.process_id
        page.quit()


class ChromeCreator:

    def __init__(self, settings, proxy_need, local, tab_mode, cache_proxy, reload_page_flag,
                 target_create_callback):
        self.proxy_need = proxy_need
        self.settings = settings
        self.local = local
        self.tab_mode = tab_mode
        self.pages_list = []
        self.max_chrome_tab = self.settings['MAX_CHROME_TABS_NUM']
        self.cache_proxy = cache_proxy
        self.reload_page_flag = reload_page_flag
        self.max_page_exist_time = self.settings['MAX_CHROME_LIVE_TIME']
        self.max_chrome_num = self.settings['TABS_NUM']
        self.max_chrome_exist_time = self.settings['MAX_TAB_LIVE_TIME']  # 标签页最大存活?秒

        self.add_session_lock = Lock()
        # 浏览器session_id列表
        self.chrome_session_id = set()
        # 浏览器空闲队列
        self.chrome_free_queue = Queue()
        # 浏览器列表
        self.chrome_list = []
        # TargetCreated 回调函数
        self.target_create_callback = target_create_callback

    # 获取chrome
    def get_chrome(self):
        chrome = Chrome(settings=self.settings, proxy_need=self.proxy_need if not self.local else False)
        if self.tab_mode:
            page = self.get_page()
            page.set.auto_handle_alert(all_tabs=True)
            return page.new_tab(), page
        else:
            page = chrome.get_chrome()
            page.browser.driver.set_callback('Target.targetCreated', self.target_create_callback, immediate=True)
            page.set.auto_handle_alert(all_tabs=True)
            return page, page

    # 获取chromium
    def get_page(self):
        for i in self.pages_list:
            if i['tab_count'] < self.max_chrome_tab:
                i['tab_count'] += 1
                return i['page']
        chrome = Chrome(settings=self.settings, proxy_need=self.proxy_need if not self.local else False)
        page = chrome.get_chrome(proxies=self.cache_proxy)
        page.browser.driver.set_callback('Target.targetCreated', self.target_create_callback, immediate=True)
        self.pages_list.append({'tab_count': 1, 'page': page, 'start_time': round(time.time())})
        return page

    # 重启chromium
    def reload_page(self, page_dict):
        print("重启浏览器")
        chrome = Chrome(settings=self.settings, proxy_need=self.proxy_need if not self.local else False)
        old_page = page_dict['page']
        page = chrome.get_chrome()
        page.browser.driver.set_callback('Target.targetCreated', self.target_create_callback, immediate=True)
        for chrome_dict in self.chrome_list:
            if chrome_dict['page'] == old_page:
                chrome_dict['page'] = page
                while True:
                    r_chrome_dict = self.chrome_free_queue.get()
                    if r_chrome_dict == chrome_dict:
                        self.reload_chrome(r_chrome_dict, immediately=True)
                        self.chrome_free_queue.put(r_chrome_dict)
                        break
                    self.chrome_free_queue.put(r_chrome_dict)
        old_page.quit()
        page_dict['start_time'] = round(time.time())
        page_dict['page'] = page

    # 重启超时chromium
    def reload_free_page(self):
        if not self.reload_page_flag:
            return
        for page_dict in self.pages_list:
            if time.time() - page_dict['start_time'] > self.max_page_exist_time:
                self.reload_page(page_dict)

    # 创建chrome
    def create_chrome(self):
        id = 0
        # Local模式下只会创建一个页面
        chrome_num = self.max_chrome_num if not self.local else 1
        for _ in range(chrome_num):
            # 自动处理弹窗
            chrome, page = self.get_chrome()
            chrome.set.auto_handle_alert()
            chrome_item = {'on_lock': 0, 'chrome': chrome, 'page': page, 'history_list': [], 'id': str(id),
                           'is_new_context': False, 'session_id': None, 'last_session_request_time': 0}
            id += 1
            self.chrome_list.append(chrome_item)
            # 添加进入空闲队列
            self.chrome_free_queue.put(chrome_item)

    # 重启chrome(会重置session_id)
    def reload_chrome(self, chrome_dict, immediately=False, new_context=None):
        # 重启页面
        if time.time() - chrome_dict['chrome'].get_chrome_time >= self.max_chrome_exist_time or immediately:
            # 继承start_time
            r_start_time = chrome_dict['chrome'].start_time
            chrome_dict['chrome'].quit()
            if not self.tab_mode:
                chrome_dict['chrome'], chrome_dict['page'] = self.get_chrome()
                chrome_dict['chrome'].start_time = r_start_time
            else:
                chrome_dict['chrome'] = chrome_dict['page'].new_tab(new_context=True if new_context else False)
                # 重置chrome_dict的session_id 当标签页重启时
                if chrome_dict['session_id'] and chrome_dict['session_id'] in self.chrome_session_id:
                    self.chrome_session_id.remove(chrome_dict['session_id'])
                chrome_dict['session_id'] = None
                chrome_dict['chrome'].start_time = r_start_time

    # 获取空闲chrome
    def get_free_chrome(self, timeout, session_id=None):
        start_time = time.time()
        while True:
            if timeout and time.time() - start_time > timeout:
                return None
            if self.chrome_free_queue.empty():
                time.sleep(0.01)
                continue
            chrome_dict = self.chrome_free_queue.get()
            # 当请求携带session_id && session_id 没有被标签页保持 && 当前标签页没有保持任何状态时
            if session_id and session_id not in self.chrome_session_id and not chrome_dict['session_id']:
                chrome_dict['chrome'].start_time = start_time
                return chrome_dict
            # 标签页保持
            elif chrome_dict['session_id'] == session_id:
                chrome_dict['chrome'].start_time = start_time
                return chrome_dict
            # 标签页保持超时
            elif time.time() - chrome_dict[
                'last_session_request_time'] > self.settings[
                'MAX_AFTER_REQUEST_SESSION_TIME'] and session_id not in self.chrome_session_id:
                chrome_dict['chrome'].start_time = start_time
                return chrome_dict
            self.chrome_free_queue.put(chrome_dict)

    # 添加session_id
    def handle_session_id(self, chrome_dict, session_id):
        with self.add_session_lock:
            chrome_dict['last_session_request_time'] = time.time()
            if session_id in self.chrome_session_id:
                return
            self.chrome_session_id.add(session_id)
            chrome_dict['session_id'] = session_id

    # 放入空闲chrome
    def put_free_chrome_queue(self, chrome_dict):
        self.chrome_free_queue.put(chrome_dict)

    # 获取空闲chrome数量
    def get_free_chrome_queue_size(self):
        return self.chrome_free_queue.qsize()

    # 检查session_id是否已添加
    def check_exist_session_id(self, session_id):
        return session_id not in self.chrome_session_id
