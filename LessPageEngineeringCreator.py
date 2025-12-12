import time
import threading
import argparse
import requests

from waitress import serve
from flask import Flask, request, jsonify

from LessPageEngineer.CentralControl import Control
import LessPageEngineer.Settings as base_settings


class LessPageEngineeringCreator:
    def __init__(self, settings=None):
        self.app = Flask(__name__)
        self._setup_routes()

        # 实例变量代替全局变量
        self.last_request_time = time.time()
        self.error_continuous = 0
        self.control = None
        self.init_lock = threading.Lock()
        self.chrome_init = False

        self.settings = base_settings.__dict__
        if settings:
            self.settings.update(settings)
        
        # 上游自动销毁开关（从settings获取，settings已包含UpstreamSettings的所有配置）
        self._auto_destroy_enabled = self.settings.get('UPSTREAM_CONTROL_ENABLE', True) and self.settings.get('UPSTREAM_AUTO_DESTROY', True)

    def _setup_routes(self):
        """设置Flask路由"""

        @self.app.route('/hello', methods=['GET'])
        def handle_hello():
            return 'Hi'

        @self.app.route('/uploadUrl', methods=['POST'])
        def handle_upload():
            return self._handle_upload_request()

    def _handle_upload_request(self):
        """处理上传请求的核心逻辑"""
        self.last_request_time = time.time()
        self._init_chrome()

        data = request.get_json()
        start_time = time.time()
        if self.settings.get('HANDLE_REQUEST_DATA'):
            data = self.settings['HANDLE_REQUEST_DATA'](data)
        try:
            result = self._process_request_data(data, start_time)
            if self.settings.get('HANDLE_RESPONSE_DATA'):
                result = self.settings['HANDLE_RESPONSE_DATA'](result)
            return jsonify(result), 200
        except Exception as e:
            self._handle_request_error(e)
            return jsonify({'status': 'error', 'message': str(e)}), 400

    def _init_chrome(self):
        """初始化浏览器控制实例"""
        if self.control is None:
            with self.init_lock:
                if self.control is None:
                    self.control = Control(
                        settings=self.settings,
                        reload_page=True,
                        cache_proxy=self.cache_proxy,
                        server_port=self.port,
                    )
                    self.chrome_init = True

    def _process_request_data(self, data, start_time):
        """处理请求数据并记录日志"""
        html_json = self.control.handle_url(data)

        # 记录运行时日志
        self.control.runtime_logger.add_recent_request_spend(
            post_data=data,
            spend_time=time.time() - start_time,
            status=html_json.get('status'),
            step_spend_time=html_json.get('step_spend_time')
        )

        # 根据状态记录不同日志
        log_method = self.control.logger.success if html_json['status'] == 'success' else self.control.logger.error
        log_message = self._build_log_message(data, start_time, html_json)
        # log_method(log_message)

        self.error_continuous = 0 if html_json['status'] == 'success' else self.error_continuous + 1
        return html_json

    def _build_log_message(self, data, start_time, html_json):
        """构建标准化日志消息"""
        base_info = f"{request.headers.get('X-Real-IP')}耗时：{round(time.time() - start_time, 3)}"
        session_info = f"session:{'Yes' if data.get('session_id') else 'No'}"
        url = data.get('url') or data.get('init_session', {}).get('url', '')
        step_info = f"步骤耗时:{html_json.get('step_spend_time')}" if self.settings['SHOW_STEP_SPEND'] else ''
        return f"{base_info}, {session_info} 链接：{url} {step_info}".strip()

    def _handle_request_error(self, error):
        """处理请求错误"""
        self.control.logger.error(f"{request.headers.get('X-Real-IP')}: {error}")
        self.error_continuous += 1

    def _monitor_exit_conditions(self):
        """监控退出条件的后台线程"""
        while True:
            # 检查是否启用自动销毁
            if self._auto_destroy_enabled:
                shutdown_flag = (
                        time.time() - self.last_request_time >= self.settings.get('SERVER_RELOAD_TIME', 3000)
                        or self.error_continuous > self.settings.get('SERVER_FAIL_RELOAD_TIMES', 15)
                )

                if shutdown_flag:
                    self._shutdown_server()

            time.sleep(10)

    def _shutdown_server(self):
        """执行服务器关闭操作"""
        # 检查上游自动销毁开关
        if not self._auto_destroy_enabled:
            return
            
        resp = requests.get(
            f"http://127.0.0.1:{self.host_port}/destroy_port",
            params={'port': self.port}
        )
        print(f"Shutdown response: {resp.json()}")

    def run(self):
        """启动服务器的主运行方法"""
        # 解析命令行参数
        parser = argparse.ArgumentParser(description="LessPageEngineer")
        parser.add_argument('-p', '--port', type=int, default=self.settings.get('SERVER_DEFAULT_PORT', 27888))
        parser.add_argument('-H', '--host', type=int, default=self.settings.get('HOST_PORT', 27188))
        parser.add_argument('-C', '--cache_proxy', type=str, default=self.settings.get('SERVER_DEFAULT_CACHE_PROXY', ''))

        args = parser.parse_args()

        # 设置实例参数
        self.port = args.port
        self.host_port = args.host
        self.cache_proxy = f"http://127.0.0.1:{args.cache_proxy}" if args.cache_proxy else ''

        # 打印启动信息
        upstream_status = "启用" if self.settings.get('UPSTREAM_CONTROL_ENABLE', True) else "禁用"
        print(f"{'-' * 10} 服务端口: {self.port} 缓存代理: {self.cache_proxy or '无'} 上游控制: {upstream_status} {'-' * 10}")

        # 启动监控线程
        monitor_thread = threading.Thread(target=self._monitor_exit_conditions)
        monitor_thread.daemon = True
        monitor_thread.start()

        # 启动服务器
        serve(self.app, host='0.0.0.0', port=self.port, threads=self.settings.get('SERVER_MAX_REQUEST_NUM', 30))
