import time
import threading

from DrissionPage._base.driver import Driver

from LessPageEngineer.Utils.Utils import encode_base64_in_chunks, decode_base64_in_chunks

class RouteDriver(Driver):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__cdp_run_history = []
        self.requestPause_func = None

    @property
    def cdp_run_history(self):
        return self.__cdp_run_history

    def clear_cdp_run_history(self):
        self.__cdp_run_history.clear()

    def replay_cdp_run_history(self, cdp_run_history):
        for cdp_item in cdp_run_history:
            if cdp_item.get('_method'):
                self.run(**cdp_item)
            elif cdp_item.get('event'):
                self.set_callback(**cdp_item)
                if cdp_item.get('event') and cdp_item['event'] == 'Fetch.requestPaused':
                    self.requestPause_func = cdp_item['callback']
            else:
                raise ValueError("未知的CDP ITEM类型")

    def run(self, _method, **kwargs):
        record = True if kwargs.get('record') == True else False
        if record:
            self.__cdp_run_history.append({
                '_method':_method, **kwargs
            })
        return super().run(_method, **kwargs)

    def set_callback(self, event, callback, immediate = False):
        self.__cdp_run_history.append({
            'event':event, 'callback':callback, 'immediate':immediate
        })
        if event == 'Fetch.requestPaused':
            self.requestPause_func = callback
            callback = self._hook_requestPaused
        return super().set_callback(event, callback, immediate)

    def _hook_requestPaused(self, **kwargs):
        kwargs['driver'] = self
        self.requestPause_func(**kwargs)

class FuncClass:
    def __init__(self, driver, timeout, requestId):
        self._driver = driver
        self._timeout = timeout
        self._request_id = requestId

    def continue_(self):
        self._driver.run('Fetch.continueRequest', requestId=self._request_id, _timeout=self._timeout)

    def abort(self):
        self._driver.run('Fetch.failRequest', requestId=self._request_id, errorReason='ConnectionAborted',
                         _timeout=self._timeout)

    # 解析响应头
    def __parse_response_headers(self, headers):
        response_headers_list = []
        if isinstance(headers, dict):
            for k, v in headers.items():
                if isinstance(v, list):
                    for _v in v:
                        response_headers_list.append({'name': k.lower(), 'value': _v})
                else:
                    if k.lower() == 'set-cookie':
                        for set_item in v.split(', '):
                            response_headers_list.append({'name': k.lower(), 'value': set_item})
                    else:
                        response_headers_list.append({'name': k.lower(), 'value': v})
                        continue
        return response_headers_list

    # 解析响应体
    def __parse_response_body(self, body, is_base64):
        if not is_base64:
            if isinstance(body, bytes):
                body = encode_base64_in_chunks(body).decode()
            elif isinstance(body, str):
                body = encode_base64_in_chunks(body.encode()).decode()
        return body

    def fullfillRequest(self, responseCode: int = None, responseHeaders: dict = {},
                        body: str = None, is_base64=False, **kwargs):
        assert isinstance(responseCode, int), "状态码有误"
        body = self.__parse_response_body(body, is_base64)
        response_headers_list = self.__parse_response_headers(responseHeaders)
        result = self._driver.run('Fetch.fulfillRequest', requestId=self._request_id,
                                  responseCode=responseCode if responseCode else self.status_code,
                                  responseHeaders=response_headers_list if responseHeaders else self.response_headers_list,
                                  body=body, _timeout=self._timeout)
        return result


class Request(FuncClass):
    def __init__(self, driver=None, timeout=60, requestId='', request={}, frameId='', resourceType='', networkId='',
                 **kwargs):
        super().__init__(driver, timeout, requestId)
        assert requestId != '', 'requestId错误'
        self.__request = request
        self.__frameId = frameId
        self.__resourceType = resourceType
        self.__networkId = networkId
        self.__post_data = self.__request.get('postData')

    @property
    def url(self) -> str:
        return self.__request['url']

    @property
    def resource_type(self) -> str:
        return self.__resourceType

    @property
    def network_id(self) -> str:
        return self.__networkId

    @property
    def method(self) -> str:
        return self.__request['method']

    @property
    def headers(self) -> str:
        return self.__request['headers']

    @property
    def type(self) -> str:
        return 'Request'

    @property
    def data(self) -> str:
        return self.__post_data


class Response(Request):
    def __init__(self, driver, timeout=60, requestId='', request={}, frameId='',
                 resourceType='',
                 responseStatusCode=200,
                 responseStatusText='', responseHeaders=[], responseErrorReason='', origin_response_headers=[],
                 **kwargs):
        assert requestId != '', 'requestId错误'
        super().__init__(driver=driver, timeout=timeout, requestId=requestId, request=request, frameId=frameId,
                         resourceType=resourceType)
        self.__responseStatusCode = responseStatusCode
        self.__responseStatusText = responseStatusText
        self.__origin_response_headers = origin_response_headers
        self.__responseHeaders = responseHeaders
        self.__responseErrorReason = responseErrorReason
        self.__response_done = False
        t1 = threading.Thread(target=self.__getResponse)
        t1.setDaemon(True)
        t1.start()
        # self.__getResponse()

    @property
    def type(self) -> str:
        return 'Response'

    @property
    def status_code(self):
        return self.__responseStatusCode

    @property
    def status_text(self):
        return self.__responseStatusText

    @property
    def response_error_reason(self):
        return self.__responseErrorReason

    @property
    def response_headers(self):
        headers = {}
        if isinstance(self.__responseHeaders, list):
            for i in self.__responseHeaders:
                headers[i['name']] = i['value']
            return headers
        elif isinstance(self.__responseHeaders, dict):
            return self.__responseHeaders

    @property
    def response_headers_list(self):
        return self.__responseHeaders

    @property
    def body(self):
        while not self.__response_done:
            time.sleep(0.1)
        return self.__body

    @property
    def origin_response_headers(self):
        return self.__origin_response_headers

    def __getResponse(self):
        if self.response_error_reason:
            print("该链接无法进行请求体捕获，将继续请求")
            self.continue_()
            return None
        result = self._driver.run('Fetch.getResponseBody', requestId=self._request_id, _timeout=self._timeout)
        if not result.get('body'):
            # if True:
            if '.jpg' in self.url or '.png' in self.url:
                self.__body = ' '
            else:
                self.__body = None
        elif result.get('base64Encoded') and result.get('base64Encoded') == True:
            self.__body = decode_base64_in_chunks(result['body'])
        else:
            self.__body = result['body']
        self.__response_done = True

