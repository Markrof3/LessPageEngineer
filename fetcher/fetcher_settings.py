DEFAULT_TIMEOUT = 120  # 默认超时时间
online = False
PROXY_URL_LIST = [
    'http://192.168.1.10:3006/get_proxy',
    'http://192.168.1.10:3006/get_hw'
]  # 代理获取接口
PROXY_AUTH_USERNAME = "LPEnet2023"  # 代理验证账号
PROXY_AUTH_PASSWORD = "LPEnet@2023"  # 代理验证密码
PROXY_SLEEP_TIME = 3
PROXY_OPEN = True  # 代理总开关(一般测试使用，提高效率，线上需要注释)
PROXY_WHITE_LIST = [
    "(http(s)?://)192.168.\d+\.\d+"
]  # 代理白名单(正则)
