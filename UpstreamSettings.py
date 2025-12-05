"""
上游控制配置文件
用于管理与主控节点通信、服务注册、缓存同步等分布式功能
"""

''' 上游控制总开关 '''
# 关闭后禁用所有上游控制功能，节点将以独立模式运行
UPSTREAM_CONTROL_ENABLE = False

''' 细分功能开关（仅在总开关开启时生效）'''
UPSTREAM_AUTO_DESTROY = True      # 节点自动销毁（超时/失败时通知主控销毁本节点）
UPSTREAM_SERVICE_REGISTER = True  # 服务注册到Redis（供主控发现）
UPSTREAM_CACHE_SYNC = True        # 缓存同步到Redis（供代理使用）

''' 主控配置 '''
# 是否作为浏览器客户端
AS_CLIENT = False
# 设置重启服务节点间隔为21700秒，即1/4天
RESTART_INTERVAL = 21700
# 主控IP地址
CONTROL_IP = 'http://127.0.0.1:27188'
# 控制器端口
HOST_PORT = 27188

''' 服务注册配置 '''
# 服务节点ip redis key
SERVER_PORT_KEY = 'LPE_Chrome_RPC:ip_port'

''' 节点自动重启/销毁配置 '''
# 服务节点在?s内没有接受到请求则重启服务节点
SERVER_RELOAD_TIME = 3000
# 服务节点在连续?次失败后重启服务节点
SERVER_FAIL_RELOAD_TIMES = 15

''' Redis配置 '''
REDIS_HOST_IP_UPLOAD = "127.0.0.1"
REDIS_HOST = "127.0.0.1"
REDIS_PORT = 6379
REDIS_DB = 13

''' 缓存代理配置 '''
# 存储缓存代理的主Key
CACHE_PROXY_MAIN_KEY = 'LPE_Chrome_RPC'
# 存储缓存代理响应头
CACHE_PROXY_HEADERS_KEY = 'RESPONSE_HEADERS'
# 存储缓存代理响应体
CACHE_PROXY_BODY_KEY = 'RESPONSE_BODY'
# 存储全局代理
GLOBAL_PROXY_KEY = 'GLOBAL_PROXY'
# TCP穿透-SNI Key
CACHE_PASS_THROUGH_SNI_KEY = 'PASS_THROUGH_SNI_KEY'
# mitmproxy更新PASS SNI时间?s
MITMPROXY_UPDATE_SNI_TIME = 30


