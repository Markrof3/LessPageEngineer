import os

# 导入上游控制配置（保持向后兼容）
from LessPageEngineer.UpstreamSettings import *

''' main.py & CentralControl 服务节点(单个浏览器) '''
# 标签页数量 -- 一个标签页通常代表着一个请求
TABS_NUM = 6
# 捕获请求的日志等级
FETCH_LOG = 0
# 服务节点运行默认端口
SERVER_DEFAULT_PORT = 27888
# 默认缓存代理端口号
SERVER_DEFAULT_CACHE_PROXY = ''
# 服务节点可承受的最大请求数量
SERVER_MAX_REQUEST_NUM = 30
# Mongo
MONGO_HOST = '127.0.0.1'
MONGO_DB = 'LPE_Chrome_Cache'
MONGO_CONNECT = 'ALL'
# 一个浏览器最多开启?个标签页
MAX_CHROME_TABS_NUM = 20
# 标签页最大存活时间
MAX_TAB_LIVE_TIME = 300000
# 浏览器最大存活时间
MAX_CHROME_LIVE_TIME = 30000
# 标签页状态打印时间间隔?s
TABS_STATUS_INTERVAL = 60
# 标签页 Session 保持的最大空闲时间（秒）
# 当标签页绑定某个 session_id 后，若超过此时间没有收到该 session 的请求，则释放绑定
MAX_AFTER_REQUEST_SESSION_TIME = 9000
# 是否展示耗时步骤(运行中)
SHOW_STEP_SPEND = False
# 本地模式 (本地模式下不会上代理以及只会强制一个标签页)
LOCAL = False

''' ChromeManger.py  浏览器初始化设置'''
# 是否启用无头模式
HEADER_LESS = False
# 是否启用无痕模式
INCOGNITO = False
# 插件路径 (绝对路径)
# EXTENSION_PATHS = [r'E:\aaazzl\zzl\dp_extensions\webrtc\0.2.4_0',r'E:\aaazzl\zzl\dp_extensions\click-extension']
EXTENSION_PATHS = []
# EXTENSION_PATH = None
# 是否切换不同的浏览器
CHANGE_BROWSER = False
# 启动项设置 (稳定)
CHROME_STABLE_ARGUMENT = [
    # '--disable-web-security',  # cloudflare检测(检测请求头中origin是否正确)
    '--ignore-certificate-errors',
    '--no-sandbox',
    '--disable-gpu',
    # '--headless=new',
    '--font-cache-shared-handle',
    # '--disable-extensions', # 是否禁用插件
    ('--window-size', '2000,1000'),
]
# 启动项设置 (非稳定)
CHROME_UNSTABLE_ARGUMENT = [
    '--disable-background-timer-throttling',
    '--disable-backing-store-limit',
    '--disable-component-extensions-with-background-pages',
    '--disable-composited-antialiasing',
    '--disable-in-process-stack-traces',
    '--disable-v8-idle-tasks',
    '--disable-stack-profiler',
    # '--auto-open-devtools-for-tabs', # 是否自动打开dev-tool
]
# 实验项
CHROME_FLAGS = [
    ('enable-process-per-site-up-to-main-frame-threshold', '2'),
    ('https-upgrades', '2') # 禁用https自动升级
]
# 用户文件夹存放路径
CHROME_USER_PATH = r'F:\chromeUserDir'
# 浏览器缓存文件存放路径
CHROME_CACHE_SAVE_PATH = r'F:\chromeCache'

''' 本地数据文件 '''
READ_LOCAL_FILE = True  # 是否读取本地数据文件(False的话则从MongoDB读取)
LOCAL_FILE_PATH = os.path.dirname(os.path.abspath(__file__)) + '\\'

''' 共用 '''
# 最大CPU熔断 %
MAX_CPU_USAGE = 95
# 服务节点数量
SERVER_PORT_NUM = 1
# python路径
PYTHON_PATHS = []
# mitmdump路径
MITMDUMP_PATHS = []
# 是否使用上游服务器代理
USE_UPSTREAM = False
# 上游服务器代理
UPSTREAM = None
# fidder默认端口
# UPSTREAM = 'http://127.0.0.1:8888'
# 小黄鸟
# UPSTREAM = 'http://127.0.0.1:9000'
# SAKURA
# UPSTREAM = 'http://127.0.0.1:7897'
# MITMPROXY
# UPSTREAM = 'http://127.0.0.1:28001'
# 获取代理Ip地址
IP_PROXYS = []
# 处理flask接收到的请求体
HANDLE_REQUEST_DATA = None
# 处理flask返回的响应体
HANDLE_RESPONSE_DATA = None
# 浏览器路径
BROWSER_PATH = [
    # {'path': r'E:\Chrome\chrome.exe', 'absolute_path': True},
]
