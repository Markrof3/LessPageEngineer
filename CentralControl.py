import threading
import time

from loguru import logger
# from ddddocr import DdddOcr

from .UtilClass.ChromeManger import ChromeCreator
from .UtilClass.RunTimeLogger import RunTimeLogger
from .UtilClass.RedisCache import RedisCache
from .UtilClass.MongoCache import MongoCache
from .UtilClass.PickleHandler import PickleHandler
from .UtilClass.TaskHandler import TaskHandle
from .UtilClass.RunTimeCache import RunTimeCache
from .Memory.CheckMemory import CheckMemory
from .UpstreamSettings import UPSTREAM_CONTROL_ENABLE, UPSTREAM_CACHE_SYNC

class Control:

    def __init__(self, settings=None, reload_page=True, all_show_log=0, route_log=0,
                 use_old_chrome=False, cache_proxy='', server_port=None):
        self.PROXY_NEED = True
        self.chrome_process_dict = {}
        # 缓存代理
        self.cache_proxy = cache_proxy
        # 日志等级
        self.all_show_log = all_show_log
        # 日志输出
        self.logger = logger
        # 服务运行端口
        self.server_port = server_port
        self.settings = settings
        self.fetch_log = self.settings['FETCH_LOG']
        self.route_log = route_log
        # 使用历史版本Chrome
        self.use_old_chrome = use_old_chrome
        # 任务列表
        self.task_list = []
        self.TAB_MODE = True
        self.check_memory = False
        if self.check_memory:
            c = CheckMemory()
            c.run()
        self.LOCAL = self.settings['LOCAL']
        self.RELOAD_PAGE = reload_page
        # self.det = DdddOcr(det=False, ocr=False, show_ad=False)
        # 浏览器创建器
        self.chrome_manger = ChromeCreator(proxy_need=self.PROXY_NEED, local=self.LOCAL, tab_mode=self.TAB_MODE,
                                           use_old_chrome=self.use_old_chrome,
                                           cache_proxy=self.cache_proxy, reload_page_flag=self.RELOAD_PAGE,
                                           settings=self.settings, target_create_callback=self.target_create)
        self.chrome_manger.create_chrome()
        
        # redis缓存上传 - 检查上游控制开关
        if UPSTREAM_CONTROL_ENABLE and UPSTREAM_CACHE_SYNC and cache_proxy:
            self.redis_cache = RedisCache(cache_proxy)
        else:
            self.redis_cache = None
            
        # 数据持久化管理
        self.data_manger = MongoCache() if not self.settings['READ_LOCAL_FILE'] else PickleHandler(self.settings['LOCAL_FILE_PATH'])
        # 运行缓存
        self.run_time_cache = RunTimeCache(logger=self.logger)
        # 开启清理source_dict
        t1 = threading.Thread(target=self.main_threaing_task)
        t1.daemon = True
        t1.start()
        self.show_chrome_free_flag = True
        if self.show_chrome_free_flag:
            self.runtime_logger = RunTimeLogger(self.settings['TABS_STATUS_INTERVAL'],
                                                chrome_manger=self.chrome_manger,
                                                chrome_num=self.settings['TABS_NUM'],
                                                server_port=self.server_port,
                                                logger=self.logger)
            self.runtime_logger.run()

    def main_threaing_task(self):
        while True:
            # 清理空闲source_dict
            self.run_time_cache.clear_all_source_dict()
            # 清理page
            self.chrome_manger.reload_free_page()
            time.sleep(10)

    # 初始化task
    def init_task(self, post_data):
        handle_data_ = self.handle_init_session_data(post_data)
        task = TaskHandle(handle_data_, data_manger=self.data_manger, redis_cache=self.redis_cache,
                          logger=self.logger, det=None,
                          run_time_cache=self.run_time_cache, cache_proxy=self.cache_proxy,
                          fetch_show_log=self.fetch_log if self.fetch_log else self.all_show_log,
                          )
        return task

    # 处理post_data(如果有init_session情况)
    def handle_init_session_data(self, post_data):
        handle_data_ = post_data
        if post_data.get('session_id') and self.chrome_manger.check_exist_session_id(post_data['session_id']):
            if not post_data.get('init_session'):
                return {'status': 'fail', 'message': 'session_id必须配合init_session使用'}
            handle_data_ = post_data['init_session']
            handle_data_['session_id'] = post_data['session_id']
            if not isinstance(handle_data_['session_id'], str):
                return {'status': 'fail', 'message': '"session_id必须为str类型"'}
        return handle_data_

    def get_free_chrome(self, task):
        start_time = time.time()
        # 获取空闲浏览器
        chrome_dict = self.chrome_manger.get_free_chrome(task.handle_data.get('timeout'),
                                                         task.handle_data.get('session_id'))
        task.step_spend_time['get_chrome_time'] = round(time.time() - start_time, 3)
        # 超时
        if chrome_dict == None:
            return {'status': 'fail', 'message': '在获取空闲浏览器步骤超时了'}
        return chrome_dict

    def reload_chrome(self, task, chrome_dict):
        r_l_immediately = chrome_dict['session_id'] and chrome_dict['session_id'] != task.handle_data.get('session_id')
        r_l_immediately = r_l_immediately or task.handle_data['new_context'] != chrome_dict['is_new_context']
        # 是否创建新上下文标签页
        self.chrome_manger.reload_chrome(chrome_dict, new_context=task.handle_data['new_context'],
                                         immediately=r_l_immediately)
        chrome_dict['is_new_context'] = task.handle_data['new_context']

    def handle_url(self, post_data):
        try:
            # 初始化任务
            task = self.init_task(post_data)
            self.task_list.append(task)
            # 获取空闲chrome_dict
            chrome_dict = self.get_free_chrome(task)
            if not chrome_dict.get('chrome'):
                return chrome_dict
            # 重启/不重启 chrome
            self.reload_chrome(task, chrome_dict)
            chrome = chrome_dict['chrome']
            try:
                task.init_run(chrome=chrome, chrome_session_id=chrome_dict['session_id'])
                result = task.run(chrome=chrome)
                if result.get('status') and result.get('status') == 'success' and task.handle_data.get('session_id'):
                    self.chrome_manger.handle_session_id(chrome_dict, task.handle_data['session_id'])
                else:
                    task.get_blank_page()
                    if chrome.route:
                        chrome.route.clear_cdp_run_history()
                # 放入队列
                self.chrome_manger.put_free_chrome_queue(chrome_dict)
                self.task_list.remove(task)
                return result
            except Exception as e:
                self.logger.error(f"加载页面时有误： {e}")
                task.fail_reload()
                # if isinstance(e, PageDisconnectedError):
                #     chrome_dict['chrome']._driver = Driver(chrome_dict['chrome'].id, 'page', chrome_dict['chrome'].address)
                self.chrome_manger.reload_chrome(chrome_dict, immediately=True)
                # 放回队列
                self.chrome_manger.put_free_chrome_queue(chrome_dict)
                self.task_list.remove(task)
                return {'status': 'fail', 'message': str(e), 'step_spend_time': task.step_spend_time}
        except Exception as e:
            self.logger.warning(f"初始化过程中有误： {e}")
            try:
                self.task_list.remove(task)
            except Exception as b:
                pass
            return {'status': 'fail', 'message': str(e), 'step_spend_time': {}}

    # 广播
    def target_create(self, **kwargs):
        if kwargs['targetInfo']['type'] == 'iframe':
            for task in self.task_list:
                if task.iframe_load_status:
                    task.focus_iframe_id.put({'id':kwargs['targetInfo']['targetId']})
