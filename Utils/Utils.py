import requests
import socket
import time

from re import compile, findall
from random import choice
from base64 import b64encode, b64decode
from urllib.parse import parse_qs

from LessPageEngineer.Settings import IP_PROXYS

LAST_UPDATE_TIME = 0
PROXY_POOL = []


def update_proxy_pool():
    global PROXY_POOL
    proxies_list = requests.get(url=choice(IP_PROXYS)).json()['data']
    PROXY_POOL = proxies_list


# 获取长代理
def get_brand_new_proxy():
    try:
        # global LAST_UPDATE_TIME
        # if round(time.time()) - LAST_UPDATE_TIME >= 30:
        #     update_proxy_pool()
        #     LAST_UPDATE_TIME = time.time()
        # proxies_item = choice(PROXY_POOL)
        # return {
        #     'http': f"http://{proxies_item['host']}",
        #     'https': f"http://{proxies_item['host']}",
        # }
        return {
            'http': f"http://127.0.0.1:9002",
            'https': f"http://127.0.0.1:9002",
        }
    except Exception as e:
        raise Exception("获取代理失败")


# 写入到本地文件
def write_to_local_html(content):
    with open('../res.html', 'w', encoding='utf-8') as fp:
        fp.write(str(content))


# 字符串cookies转dict
def cookie_string_to_dict(cookie_string):
    # 使用正则表达式匹配键值对
    pattern = r'(\w+)=([^;]+)'
    cookies = dict(findall(pattern, cookie_string))
    return cookies


# 流式编码Base64
def encode_base64_in_chunks(binary_data, chunk_size=1023 * 1023):
    # 将二进制数据分块
    chunks = [binary_data[i:i + chunk_size] for i in range(0, len(binary_data), chunk_size)]
    # 对每个块进行base64编码
    encoded_data = b''.join([b64encode(chunk).replace(b'\n', b'') for chunk in chunks])
    return encoded_data


# 流式解码Base64
def decode_base64_in_chunks(encoded_data, chunk_size=1024 * 1024):
    # 将编码后的数据分块
    chunks = [encoded_data[i:i + chunk_size] for i in range(0, len(encoded_data), chunk_size)]
    # 对每个块进行base64解码，并合并结果
    decoded_data = b''.join(b64decode(chunk) for chunk in chunks)
    return decoded_data


# wait_urls中链接规则转 re.pattern
def url_pattern_cut(urlPattern):
    if not urlPattern.endswith('**'):
        urlPattern = urlPattern + '$'
    if not urlPattern.startswith('**'):
        urlPattern = '^' + urlPattern
    urlPattern = urlPattern.replace('**', '.*').replace('?', '\?')
    return compile(urlPattern)


# 缩减url
def reduce_url(url, data=None):
    if '?' in url:
        url = url.split('?')[0] + ''.join([k for k, v in parse_qs(url.split('?')[-1]).items()])
    return url

# 获取本地Ip
def get_local_ip():
    try:
        # 创建一个 UDP 套接字
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # 连接到外部地址，不会真正发送数据
        sock.connect(("8.8.8.8", 80))
        # 获取本地 IP 地址
        local_ip = sock.getsockname()[0]
        # 关闭套接字
        sock.close()
        return local_ip
    except Exception as e:
        print(f"获取 IP 地址时出错: {e}")
        return None