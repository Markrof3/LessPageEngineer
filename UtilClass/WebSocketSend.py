import websocket
import time


class WebSocketClient:
    def __init__(self, url, timeout=10, headers=None,
                 proxy_host=None, proxy_port=None, retries=3):
        """
        WebSocket 同步客户端
        :param url: 连接地址（ws:// 或 wss://）
        :param timeout: 连接超时时间（秒）
        :param headers: 自定义请求头（列表格式）
        :param proxy_host: 代理主机地址
        :param proxy_port: 代理端口
        :param retries: 失败重试次数
        """
        self.url = url
        self.timeout = timeout
        self.headers = headers
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port
        self.retries = retries
        self.ws = None  # WebSocket 连接对象

    def _create_connection(self):
        """创建 WebSocket 连接（内部方法）"""
        try:
            self.ws = websocket.create_connection(
                self.url,
                timeout=self.timeout,
                header=self.headers,
                http_proxy_host=self.proxy_host,
                http_proxy_port=self.proxy_port
            )
            print(f"成功连接到: {self.url}")
            return True
        except Exception as e:
            print(f"连接失败: {str(e)}")
            self.ws = None
            return False

    def _safe_send(self, message):
        """带异常处理的发送（内部方法）"""
        try:
            self.ws.send(message)
            return True
        except websocket.WebSocketConnectionClosedException:
            print("检测到连接已断开")
            self.ws = None
            return False
        except Exception as e:
            print(f"发送异常: {str(e)}")
            self.ws = None
            return False

    def send_message(self, message):
        """
        发送消息（外部调用接口）
        :param message: 要发送的消息内容
        :return: 是否发送成功
        """
        for attempt in range(self.retries + 1):
            # 连接状态检测
            if not self.ws or not self.ws.connected:
                print(f"尝试建立连接（第 {attempt + 1} 次）...")
                if not self._create_connection():
                    time.sleep(1)  # 失败后等待1秒再重试
                    continue

            # 消息发送处理
            if self._safe_send(message):
                print(f"消息发送成功: {message}")
                return True

            time.sleep(0.5)  # 发送失败后短暂等待

        print(f"发送失败，已达最大重试次数 {self.retries}")
        return False

    def close(self):
        """主动关闭连接"""
        if self.ws and self.ws.connected:
            self.ws.close()
            self.ws = None
            print("连接已主动关闭")
