import threading


class FetchTimeoutThread(threading.Thread):
    """请求超时监控"""

    def __init__(self, target, **kwargs):
        super().__init__()
        self.target = target
        self.kwargs = kwargs
        self.result = None
        self.exception = None

    def run(self):
        # 保存结果
        try:
            self.result = self.target(**self.kwargs)
        except Exception as e:
            self.exception = e


def _function_with_timeout(target, run_timeout, **new_kwargs):
    """
    创建线程检测请求是否超时

    参数:
        :param target:      请求方法.
        :param run_timeout: 强制超时时间.
        :param new_kwargs:  请求参数.

    返回结果: response
    """
    # 创建线程
    thread = FetchTimeoutThread(target=target, **new_kwargs)
    thread.start()
    thread.join(timeout=run_timeout)  # 即使超时结束后,线程仍然会执行完

    if thread.is_alive():
        # 线程仍然存活,超时异常
        raise ValueError(f"线程超时: {run_timeout}秒")
    else:
        # 获取线程执行异常
        if thread.exception:
            raise thread.exception
        # 获取线程执行结果
        return thread.result

def function_with_timeout(target, run_timeout, fail_func, **new_kwargs):
    try:
        _function_with_timeout(target, run_timeout, **new_kwargs)
    except Exception as e:
        # print("超时了", target, new_kwargs)
        # _function_with_timeout(target, run_timeout, **new_kwargs)
        if fail_func:
            fail_func()
            print("执行失败函数")