import time
import threading
import argparse
import requests
import base64

import os
from waitress import serve
from flask import Flask, request, jsonify, render_template

from LessPageEngineer.CentralControl import Control
import LessPageEngineer.Settings as base_settings


class LessPageEngineeringCreator:
    def __init__(self, settings=None):
        template_dir = os.path.join(os.path.dirname(__file__), 'templates')
        self.app = Flask(__name__, template_folder=template_dir)
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

        # ========== 缓存管理路由（统一管理，以 MongoDB/Pickle 为主） ==========
        @self.app.route('/cache', methods=['GET'])
        def cache_manager_ui():
            self._init_chrome()
            return render_template('cache_manager.html')

        @self.app.route('/cache/keys', methods=['GET'])
        def list_cache_keys():
            return self._handle_cache_list_keys()

        @self.app.route('/cache/<path:key>', methods=['GET'])
        def get_cache(key):
            return self._handle_cache_get(key)

        @self.app.route('/cache/<path:key>', methods=['POST'])
        def set_cache(key):
            return self._handle_cache_set(key)

        @self.app.route('/cache/<path:key>', methods=['DELETE'])
        def delete_cache(key):
            return self._handle_cache_delete(key)

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

    # ========== 缓存管理方法（统一管理，以 MongoDB/Pickle 为主） ==========
    def _process_bytes_body(self, data):
        """处理数据中的 bytes 类型 body，转为可 JSON 序列化的格式"""
        if not isinstance(data, dict):
            return
        for k, v in data.items():
            if k.startswith('http') and isinstance(v, dict) and 'body' in v:
                if isinstance(v['body'], bytes):
                    v['_body_is_bytes'] = True
                    try:
                        v['body'] = v['body'].decode('utf-8')
                    except UnicodeDecodeError:
                        v['body'] = base64.b64encode(v['body']).decode('utf-8')
                        v['_body_is_base64'] = True

    def _restore_bytes_body(self, data):
        """将标记的 body 转回 bytes 类型"""
        if not isinstance(data, dict):
            return
        for k, v in data.items():
            if k.startswith('http') and isinstance(v, dict) and 'body' in v:
                if v.get('_body_is_bytes'):
                    if v.get('_body_is_base64'):
                        v['body'] = base64.b64decode(v['body'])
                    else:
                        v['body'] = v['body'].encode('utf-8')
                v.pop('_body_is_bytes', None)
                v.pop('_body_is_base64', None)

    def _get_primary_cache(self):
        """获取主缓存实例（MongoDB/Pickle）"""
        if self.control is None:
            self._init_chrome()
        if self.control is None:
            return None, '初始化失败'
        return self.control.data_manger, None

    def _handle_cache_list_keys(self):
        """列出缓存 key（从主缓存获取）"""
        cache, error = self._get_primary_cache()
        if error:
            return jsonify({'status': 'fail', 'message': error}), 400
        
        try:
            keys = cache.list_keys()
            return jsonify({'status': 'success', 'data': keys, 'count': len(keys)}), 200
        except Exception as e:
            return jsonify({'status': 'fail', 'message': str(e)}), 500

    def _handle_cache_get(self, key):
        """获取缓存内容（从主缓存获取）"""
        cache, error = self._get_primary_cache()
        if error:
            return jsonify({'status': 'fail', 'message': error}), 400
        
        try:
            data = cache.load_data(key)
            if data is None:
                return jsonify({'status': 'fail', 'message': f'key不存在: {key}'}), 404
            
            # 处理 MongoDB 的 _id
            if '_id' in data:
                data['_id'] = str(data['_id'])
            # 处理 datetime 对象序列化
            if 'update_time' in data:
                data['update_time'] = str(data['update_time'])
            # 处理 bytes 类型的 body
            self._process_bytes_body(data)
            
            return jsonify({'status': 'success', 'data': data}), 200
        except Exception as e:
            return jsonify({'status': 'fail', 'message': str(e)}), 500

    def _handle_cache_set(self, key):
        """设置缓存内容（同步更新所有缓存）"""
        cache, error = self._get_primary_cache()
        if error:
            return jsonify({'status': 'fail', 'message': error}), 400
        
        data = request.get_json()
        if not data:
            return jsonify({'status': 'fail', 'message': '请求体不能为空'}), 400
        
        try:
            # 移除元数据字段
            data.pop('_id', None)
            data.pop('key', None)
            data.pop('update_time', None)
            
            # 将 body 转回 bytes 类型
            self._restore_bytes_body(data)
            
            # 1. 保存到主缓存（MongoDB/Pickle）
            cache.dump_data(key, data, replace=True)
            
            # 2. 同步到 Runtime 缓存（如果存在相同 key）
            if self.control.run_time_cache.search_source_dict(key):
                self.control.run_time_cache.update_source_dict(key, data)
            
            # 3. 同步到 Redis 缓存（如果启用且存在相同 key 的 URL）
            if self.control.redis_cache:
                for url_key, url_data in data.items():
                    if url_key.startswith('http') and isinstance(url_data, dict):
                        headers = url_data.get('headers', {})
                        body = url_data.get('body', '')
                        if isinstance(body, bytes):
                            body = base64.b64encode(body).decode('utf-8')
                        self.control.redis_cache.set_cache(url_key, headers, body)
            
            return jsonify({'status': 'success', 'message': f'缓存已更新: {key}（已同步到所有缓存）'}), 200
        except Exception as e:
            return jsonify({'status': 'fail', 'message': str(e)}), 500

    def _handle_cache_delete(self, key):
        """删除缓存（同步删除所有缓存）"""
        cache, error = self._get_primary_cache()
        if error:
            return jsonify({'status': 'fail', 'message': error}), 400
        
        try:
            # 先获取数据，用于同步删除 Redis 中的 URL
            data = cache.load_data(key)
            
            # 1. 从主缓存删除
            result = cache.delete_data(key)
            
            # 2. 从 Runtime 缓存删除
            if self.control.run_time_cache.search_source_dict(key):
                self.control.run_time_cache.drop_source_dict(key)
            
            # 3. 从 Redis 缓存删除相关 URL
            if self.control.redis_cache and data:
                for url_key in data.keys():
                    if url_key.startswith('http'):
                        self.control.redis_cache.delete_cache(url_key)
            
            if result:
                return jsonify({'status': 'success', 'message': f'缓存已删除: {key}（已同步删除所有缓存）'}), 200
            return jsonify({'status': 'fail', 'message': f'key不存在: {key}'}), 404
        except Exception as e:
            return jsonify({'status': 'fail', 'message': str(e)}), 500

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
