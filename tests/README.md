# LessPageEngineering 单节点功能测试

## 测试前准备

### 1. 安装测试依赖
```bash
pip install pytest requests
```

### 2. 启动服务节点
```bash
python -m LessPageEngineering.LessPageEngineeringCreator -p 27888
```

### 3. 确认服务正常
```bash
curl http://127.0.0.1:27888/hello
# 应返回: Hi
```

---

## 测试文件说明

| 文件 | 功能 | 测试项 |
|------|------|--------|
| `test_page_request.py` | 页面请求 | 简单加载、超时、等待元素、等待请求 |
| `test_request_intercept.py` | 请求拦截 | 填充请求、中止请求、修改响应、代理保持 |
| `test_cache.py` | 缓存功能 | key_save、key_replace、缓存加载 |
| `test_script_execution.py` | 脚本执行 | JS执行、元素点击、元素输入、线程脚本 |
| `test_session.py` | Session保持 | 创建/复用Session、Cookie管理、Storage |
| `test_proxy.py` | 代理功能 | 代理保持、全局代理、网络控制、UA设置 |
| `test_advanced_features.py` | 高级功能 | 加载模式、页面刷新、iframe、HTML输出 |

---

## 运行测试

### 运行所有测试
```bash
pytest tests/ -v
```

### 运行单个测试文件
```bash
pytest tests/test_page_request.py -v
```

### 运行单个测试用例
```bash
pytest tests/test_page_request.py::TestBasicPageRequest::test_simple_page_load -v
```

### 跳过需要特殊环境的测试
```bash
pytest tests/ -v -m "not skip"
```

### 生成测试报告
```bash
pytest tests/ -v --html=report.html
```

---

## 测试覆盖的功能

### 1. 页面请求 (`test_page_request.py`)
- [x] 简单页面加载
- [x] 页面加载超时
- [x] 等待单个请求 (wait_urls)
- [x] 等待多个请求
- [x] 等待单个元素 (ensure_eles)
- [x] 等待元素并验证文本长度

### 2. 请求拦截 (`test_request_intercept.py`)
- [x] 用JSON数据填充请求 (fill_data)
- [x] 用字符串填充请求
- [x] 中止指定请求 (abort)
- [x] 修改响应内容 (modify)
- [ ] 代理保持请求 (keep_proxy) - 需要代理环境

### 3. 缓存功能 (`test_cache.py`)
- [x] key_save 创建缓存
- [x] 从缓存加载 (key)
- [x] key_replace 更新缓存
- [x] 缓存与等待链接结合

### 4. 脚本执行 (`test_script_execution.py`)
- [x] 简单JS执行 (run_js)
- [x] 异步JS执行 (wait_async)
- [x] 多个JS脚本执行
- [x] 元素点击 (click)
- [x] 元素输入 (input)
- [x] 通过JS点击元素 (by_js)
- [x] 线程模式执行脚本 (thread_script)

### 5. Session保持 (`test_session.py`)
- [x] 创建Session (session_id)
- [x] 复用Session
- [x] init_session模式
- [x] 获取Cookies
- [x] 设置Cookies (set_cookies)
- [x] 清除Cookies (clear_cookies)
- [x] 获取SessionStorage
- [x] 获取LocalStorage
- [x] 新上下文隔离 (new_context)

### 6. 代理功能 (`test_proxy.py`)
- [ ] 基础代理保持 - 需要代理环境
- [ ] 代理保持+指纹伪装 - 需要代理环境
- [ ] 全局代理设置 - 需要mitmproxy环境
- [x] 禁用图片和字体 (disable_img_font)
- [x] 自定义UA (ua)

### 7. 高级功能 (`test_advanced_features.py`)
- [x] 快速加载模式 (fast)
- [x] 正常加载模式
- [x] 超时刷新 (refresh)
- [ ] iframe元素操作 - 需要测试页面
- [ ] iframe请求拦截 - 需要测试页面
- [x] 返回HTML (html: true)
- [x] 不返回HTML (html: false)
- [x] 失败时返回数据 (fail_return)
- [x] 步骤耗时返回 (step_spend_time)

---

## 注意事项

1. 测试前确保服务节点已启动
2. 部分测试需要网络访问百度等网站
3. 标记为 `skip` 的测试需要特殊环境（代理、mitmproxy等）
4. 缓存测试可能会在本地创建缓存文件
