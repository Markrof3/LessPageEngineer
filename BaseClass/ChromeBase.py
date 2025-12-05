import signal
import threading
import psutil
import os
import time

from DrissionPage import WebPage
from DrissionPage._pages.chromium_tab import WebPageTab
from DrissionPage.errors import PageDisconnectedError
from DrissionPage._base.driver import Driver

# 给WebPage.quit 添加前置函数
WebPage.quit_ = WebPage.quit

def quit(self, *args, **kwargs):
    print(f"地址：{self.address} 进程:{self.process_id} 浏览器关闭")
    process_id = self.process_id
    WebPage.quit_(self, *args, **kwargs)
    def kill_process(pid, sig=signal.SIGTERM):
        try:
            # 向指定PID的进程发送一个信号
            proc = psutil.Process(int(pid))
            # 在Windows上，使用 ctypes 获取进程的可执行文件路径
            proc_info = proc.as_dict(attrs=['pid', 'name', 'exe'])
            if proc_info['name'] == 'chrome.exe':
                print(f"已向PID {pid} 发送信号 {sig}")
                os.kill(int(pid), sig)
            return True, None
        except OSError as e:
            # 如果进程不存在或权限不足，将引发OSError
            print(f"无法杀死进程 {pid}: {e}")
            return False, e
        except Exception as e:
            print(f"杀死浏览器失败:{e}")
    kill_process(self.process_id)
WebPage.quit = quit
# Web类
class LPE_WebPage(WebPage):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.__route = None
        self.__lpe_settings = {}
        self.__fetch_request = None
        self.__url = ''
        self.__run_time = None
        self.__start_time = 0
        self.get_chrome_time = time.time()
        self.__iframe = None
        self.__wait_ele_dict = None
        self.id = self.tab_id
        self.__js_result = None
        self.__route_dict = {}
        '''START 新版本'''
        # 覆盖browser中的_onTargetCreated绑定事件
        self.browser.driver.set_callback('Target.targetCreated', None)
        '''END'''

    def browser_new_tab(self, new_window=False, background=False, new_context=False):
        """新建一个标签页
        :param new_window: 是否在新窗口打开标签页
        :param background: 是否不激活新标签页，如new_window为True则无效
        :param new_context: 是否创建新的上下文
        :return: 新标签页id
        """
        bid = None
        if new_context:
            bid = self.browser.run_cdp('Target.createBrowserContext')['browserContextId']

        kwargs = {'url': ''}
        if new_window:
            kwargs['newWindow'] = True
        if background:
            kwargs['background'] = True
        if bid:
            kwargs['browserContextId'] = bid

        tid = self.browser.run_cdp('Target.createTarget', **kwargs)['targetId']
        return tid

    def _onTargetCreated(self, tab):
        """标签页创建时执行"""
        tab_id = tab.id
        d = tab.driver
        self.browser._drivers[tab_id] = d
        self.browser._all_drivers.setdefault(tab_id, set()).add(d)

    def new_tab(self, url=None, new_window=False, background=False, new_context=False):
        """新建一个标签页
        :param url: 新标签页跳转到的网址
        :param new_window: 是否在新窗口打开标签页
        :param background: 是否不激活新标签页，如new_window为True则无效
        :param new_context: 是否创建新的上下文
        :return: 新标签页对象
        """
        '''START 旧版本'''
        # tab = LPE_WebPageTab(self, tab_id= self.browser.new_tab(new_window, background, new_context))
        '''END'''
        '''START 新版本'''
        tab = LPE_WebPageTab(self, tab_id=self.browser_new_tab(new_window, background, new_context))
        self._onTargetCreated(tab)
        '''END'''
        if url:
            tab.get(url)
        return tab

    def stop(self):
        self.stop_loading()
        if self.__route:
            # 检查route中线程是否结束
            while self.__route.threadings_alive():
                time.sleep(0.1)
            self.__route.stop = True
        if self.__run_time:
            self.__run_time.stop = True

    @property
    def route(self):
        '''
        :return:  Route类(监听以及篡改请求)
        '''
        return self.__route

    @route.setter
    def route(self, route):
        self.__route = route

    @property
    def run_time(self):
        '''
        :return:  开始时间
        '''
        return self.__run_time

    @run_time.setter
    def run_time(self, run_time):
        self.__run_time = run_time

    @property
    def start_time(self):
        '''
        :return:  开始时间
        '''
        return self.__start_time

    @start_time.setter
    def start_time(self, start_time):
        self.__start_time = start_time

    @property
    def url(self):
        '''
        :return:  请求的链接
        '''
        return self.__url

    @property
    def fetch_request(self):
        '''
        :return:  FetchRequest类(用于捕获链接)
        '''
        return self.__fetch_request

    @fetch_request.setter
    def fetch_request(self, fetch_request):
        self.__fetch_request = fetch_request

    @property
    def settings(self):
        '''
        :return: wait_urls ensure_eles等设置
        '''
        return self.__lpe_settings

    @settings.setter
    def settings(self, settings):
        assert isinstance(settings, dict), "类型有误"
        self.__lpe_settings = settings
        self.__url = self.__lpe_settings.get('url')

    @property
    def iframe(self):
        '''
        :return: wait_urls ensure_eles等设置
        '''
        return self.__iframe

    @iframe.setter
    def iframe(self, iframe):
        self.__iframe = iframe

    @property
    def wait_ele_dict(self):
        return self.__wait_ele_dict

    @wait_ele_dict.setter
    def wait_ele_dict(self, wait_ele_dict):
        self.__wait_ele_dict = wait_ele_dict

    @property
    def js_result(self):
        return self.__js_result

    @js_result.setter
    def js_result(self, js_result):
        self.__js_result = js_result

# tab类
class LPE_WebPageTab(WebPageTab):
    def __init__(self, page, tab_id):
        super().__init__(page, tab_id)
        self.__route = None
        self.__lpe_settings = {}
        self.__fetch_request = None
        self.__url = ''
        self.__run_time = None
        self.__start_time = 0
        self.get_chrome_time = time.time()
        self.__iframe = None
        self.__wait_ele_dict = None
        self.id = self.tab_id
        self.__js_result = None
        self.__iframe_route = None
        self.__iframe_ele = None
        self.__iframe_fetch_request = None
        self.__iframe_s_eles = None
        self.__error_reason = None
        self.__step_spend_time = None

    def quit(self):
        """关闭当前标签页"""
        '''旧版本 START'''
        # self.page.close_tabs(self.id)
        '''END'''

        '''新版本 START'''
        try:
            self.run_cdp('Target.closeTarget', targetId=self.id)
        except PageDisconnectedError as e:
            try:
                if self.driver._stopped.is_set():
                    self.driver.stop()
                    self._driver = Driver(self.id, 'page', self.page.address)
                    self.run_cdp('Target.closeTarget', targetId=self.id)
            except Exception as e:
                # print(e)
                self.driver.stop()
        except Exception as e:
            print(f"退出标签页有误！{e}")
        # 检查driver是否关闭
        while not self.driver._stopped.is_set() and self.id in self.page.tab_ids:
            time.sleep(.01)
        '''END'''
        self._session.close()
        if self._response is not None:
            self._response.close()

    def _stop(self, success_func=None, fake_stop=False, **kwargs):
        self.stop_loading()
        if not fake_stop:
            if self.__route:
                self.__route.stop = True
                self.__route = None
            if self.__run_time:
                self.__run_time.stop = True
                self.__run_time = None

        if success_func:
            success_func(**kwargs)

    def stop(self, success_func=None, join=False, fake_stop=False, **kwargs):
        stop_th = threading.Thread(target=self._stop,
                                   kwargs={'success_func': success_func, 'fake_stop': fake_stop, **kwargs})
        stop_th.setDaemon(True)
        stop_th.start()
        if join:
            stop_th.join()

    @property
    def route(self):
        '''
        :return:  Route类(监听以及篡改请求)
        '''
        return self.__route

    @route.setter
    def route(self, route):
        self.__route = route

    @property
    def run_time(self):
        '''
        :return:  开始时间
        '''
        return self.__run_time

    @run_time.setter
    def run_time(self, run_time):
        self.__run_time = run_time

    @property
    def start_time(self):
        '''
        :return:  开始时间
        '''
        return self.__start_time

    @start_time.setter
    def start_time(self, start_time):
        self.__start_time = start_time

    @property
    def url(self):
        '''
        :return:  请求的链接
        '''
        return self.__url

    @property
    def fetch_request(self):
        '''
        :return:  FetchRequest类(用于捕获链接)
        '''
        return self.__fetch_request

    @fetch_request.setter
    def fetch_request(self, fetch_request):
        self.__fetch_request = fetch_request

    @property
    def settings(self):
        '''
        :return: wait_urls ensure_eles等设置
        '''
        return self.__lpe_settings

    @settings.setter
    def settings(self, settings):
        assert isinstance(settings, dict), "类型有误"
        self.__lpe_settings = settings
        self.__url = self.__lpe_settings.get('url')

    @property
    def iframe(self):
        '''
        :return: iframe
        '''
        return self.__iframe

    @iframe.setter
    def iframe(self, iframe):
        self.__iframe = iframe

    @property
    def iframe_route(self):
        '''
        :return: iframe
        '''
        return self.__iframe_route

    @iframe_route.setter
    def iframe_route(self, iframe_route):
        self.__iframe_route = iframe_route

    @property
    def iframe_ele(self):
        '''
        :return: iframe
        '''
        return self.__iframe_ele

    @iframe_ele.setter
    def iframe_ele(self, iframe_ele):
        self.__iframe_ele = iframe_ele

    @property
    def iframe_s_eles(self):
        '''
        :return: iframe
        '''
        return self.__iframe_s_eles

    @iframe_s_eles.setter
    def iframe_s_eles(self, iframe_s_eles):
        self.__iframe_s_eles = iframe_s_eles

    @property
    def iframe_fetch_request(self):
        '''
        :return: iframe的fetch_requests
        '''
        return self.__iframe_fetch_request

    @iframe_fetch_request.setter
    def iframe_fetch_request(self, iframe_fetch_request):
        self.__iframe_fetch_request = iframe_fetch_request

    @property
    def wait_ele_dict(self):
        '''
        :return: 等待元素的情况(字典)
        '''
        return self.__wait_ele_dict

    @wait_ele_dict.setter
    def wait_ele_dict(self, wait_ele_dict):
        self.__wait_ele_dict = wait_ele_dict

    @property
    def js_result(self):
        '''
        :return: 执行JS的情况(字典)
        '''
        return self.__js_result

    @js_result.setter
    def js_result(self, js_result):
        self.__js_result = js_result

    @property
    def error_reason(self):
        '''
        :return: 导致超时的原因(字符串)
        '''
        return self.__error_reason

    @error_reason.setter
    def error_reason(self, error_reason):
        self.__error_reason = error_reason

    @property
    def step_spend_time(self):
        '''
        :return: 步骤耗时(字典)
        '''
        return self.__step_spend_time

    @step_spend_time.setter
    def step_spend_time(self, value):
        self.__step_spend_time = value