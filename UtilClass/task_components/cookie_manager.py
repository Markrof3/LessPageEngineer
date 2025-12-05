"""
CookieManager - Cookie和Storage管理组件

负责浏览器Cookie、SessionStorage、LocalStorage的增删改操作
"""
from typing import Optional, Dict, Any
from loguru import logger


class CookieManager:
    """
    Cookie和Storage管理器
    
    职责：
    - 清除/设置Cookie
    - 设置SessionStorage
    - 设置LocalStorage
    - 获取Cookie/Storage数据用于返回结果
    """
    
    def __init__(self, chrome=None):
        """
        初始化CookieManager
        
        Args:
            chrome: Chrome浏览器实例（LPE_WebPageTab）
        """
        self._chrome = chrome
    
    def bind_chrome(self, chrome) -> 'CookieManager':
        """
        绑定Chrome实例
        
        Args:
            chrome: Chrome浏览器实例
            
        Returns:
            self，支持链式调用
        """
        self._chrome = chrome
        return self
    
    def clear_cookies(self, should_clear: bool = True) -> None:
        """
        清除浏览器Cookies
        
        Args:
            should_clear: 是否执行清除操作
        """
        if should_clear and self._chrome:
            try:
                self._chrome.set.cookies.clear()
            except Exception as e:
                logger.warning(f"清除cookies失败: {e}")
    
    def set_cookies(self, cookies: Optional[Any] = None) -> None:
        """
        设置浏览器Cookies
        
        Args:
            cookies: 要设置的cookies，格式由DrissionPage决定
        """
        if cookies and self._chrome:
            try:
                self._chrome.set.cookies(cookies)
            except Exception as e:
                logger.warning(f"设置cookies失败: {e}")
    
    def set_session_storage(self, storage_data: Optional[Dict[str, str]] = None) -> None:
        """
        设置SessionStorage
        
        Args:
            storage_data: 键值对字典 {key: value}
        """
        if not storage_data or not self._chrome:
            return
            
        for key, value in storage_data.items():
            try:
                self._chrome.set.session_storage(item=key, value=value)
            except Exception as e:
                logger.warning(f"设置session_storage[{key}]失败: {e}")
    
    def set_local_storage(self, storage_data: Optional[Dict[str, str]] = None) -> None:
        """
        设置LocalStorage
        
        Args:
            storage_data: 键值对字典 {key: value}
        """
        if not storage_data or not self._chrome:
            return
            
        for key, value in storage_data.items():
            try:
                self._chrome.set.local_storage(item=key, value=value)
            except Exception as e:
                logger.warning(f"设置local_storage[{key}]失败: {e}")
    
    def get_cookies(self) -> Optional[Any]:
        """
        获取当前页面的Cookies
        
        Returns:
            Cookies数据，失败返回None
        """
        if not self._chrome:
            return None
        try:
            return self._chrome.cookies()
        except Exception as e:
            logger.warning(f"获取cookies失败: {e}")
            return None
    
    def get_session_storage(self) -> Optional[Any]:
        """
        获取当前页面的SessionStorage
        
        Returns:
            SessionStorage数据，失败返回None
        """
        if not self._chrome:
            return None
        try:
            return self._chrome.session_storage()
        except Exception as e:
            logger.warning(f"获取session_storage失败: {e}")
            return None
    
    def get_local_storage(self) -> Optional[Any]:
        """
        获取当前页面的LocalStorage
        
        Returns:
            LocalStorage数据，失败返回None
        """
        if not self._chrome:
            return None
        try:
            return self._chrome.local_storage()
        except Exception as e:
            logger.warning(f"获取local_storage失败: {e}")
            return None
    
    def setup(self, handle_data: Dict[str, Any]) -> None:
        """
        根据handle_data配置执行初始化设置
        
        Args:
            handle_data: 任务配置数据，包含：
                - clear_cookies: 是否清除cookies
                - set_cookies: 要设置的cookies
        """
        # 清除cookies
        self.clear_cookies(handle_data.get('clear_cookies', False))
        # 设置cookies
        self.set_cookies(handle_data.get('set_cookies'))
    
    def setup_storage(self, handle_data: Dict[str, Any]) -> None:
        """
        根据handle_data配置执行Storage设置（在页面加载后调用）
        
        Args:
            handle_data: 任务配置数据，包含：
                - set_session_storage: 要设置的session_storage
                - set_local_storage: 要设置的local_storage
        """
        self.set_session_storage(handle_data.get('set_session_storage'))
        self.set_local_storage(handle_data.get('set_local_storage'))
    
    def collect_result(self, handle_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        根据handle_data配置收集Cookie/Storage结果
        
        Args:
            handle_data: 任务配置数据，包含：
                - cookies: 是否返回cookies
                - session_storage: 是否返回session_storage
                - local_storage: 是否返回local_storage
                
        Returns:
            包含请求的数据的字典
        """
        result = {}
        
        if handle_data.get('cookies'):
            result['cookies'] = self.get_cookies()
        
        if handle_data.get('session_storage'):
            result['session_storage'] = self.get_session_storage()
        
        if handle_data.get('local_storage'):
            result['local_storage'] = self.get_local_storage()
        
        return result
