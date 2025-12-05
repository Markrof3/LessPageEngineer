from threading import Thread
import time
import numpy as np


class RunTimeLogger:

    def __init__(self, time_interval, chrome_manger, server_port=None, chrome_num=10, logger=None):
        self.time_interval = time_interval
        self.chrome_manger = chrome_manger
        self.chrome_num = chrome_num
        # 最近请求耗时事件
        self.recent_request_spend_dict = {}
        # 服务运行端口
        self.server_port = server_port if server_port else 27888
        self.logger = logger

    def logger_info(self):
        for i in self.recent_request_spend_dict.keys():
            self.logger.success(
                f"{i} 最近{self.time_interval}秒内成功请求平均耗时{round(np.mean(self.recent_request_spend_dict[i]), 2)}秒")
        # 清除字典
        self.recent_request_spend_dict.clear()

    # 添加最近请求
    def add_recent_request_spend(self, spend_time=0, post_data=None, status='fail', step_spend_time={}):
        url = post_data['url'] if post_data.get('url') else post_data.get('init_session', {}).get('url', '')
        key = '/'.join(url.split('/')[:3]) if len(url.split('/')) > 3 else url
        if self.recent_request_spend_dict.get(key) and isinstance(self.recent_request_spend_dict.get(key), list):
            self.recent_request_spend_dict[key].append(spend_time)
        else:
            self.recent_request_spend_dict[key] = [spend_time]

    def main(self):
        while True:
            self.logger_info()
            self.show_chrome_free()
            time.sleep(self.time_interval)

    def show_chrome_free(self):
        free_chrome_num = self.chrome_manger.get_free_chrome_queue_size()
        self.logger.debug(f"标签页空闲数量为:{free_chrome_num} 在忙列表为:{self.chrome_num - free_chrome_num}")

    def run(self):
        t1 = Thread(target=self.main)
        t1.daemon = True
        t1.start()
