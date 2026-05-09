import time
import urllib.request
from datetime import datetime, timezone, timedelta
from typing import Optional
from core import log


class TimeSyncManager:
    """时间同步管理器 - 使用 bjtime.org.cn 授时"""
    _instance: Optional['TimeSyncManager'] = None
    _time_offset: float = 0.0
    _initialized: bool = False
    _sync_success: bool = False
    
    def __new__(cls) -> 'TimeSyncManager':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def get_instance(cls) -> 'TimeSyncManager':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def initialize(self) -> None:
        """初始化时间同步模块，尝试从 bjtime.org.cn 获取标准时间"""
        if self._initialized:
            return
        
        try:
            # 使用 urllib 替代 requests，避免第三方依赖
            req = urllib.request.Request(
                'https://www.bjtime.org.cn',
                headers={'User-Agent': 'AmiyaBot-Jrrp/1.0'}
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                server_time_str = response.headers.get('Date')
                if server_time_str:
                    server_time = datetime.strptime(server_time_str, '%a, %d %b %Y %H:%M:%S GMT')
                    server_time = server_time.replace(tzinfo=timezone.utc)
                    # 转换为北京时间 (UTC+8)
                    bj_tz = timezone(timedelta(hours=8))
                    server_time = server_time.astimezone(bj_tz)
                    
                    # 计算时间偏移量
                    local_time = datetime.now(bj_tz)
                    self._time_offset = (server_time - local_time).total_seconds()
                    self._sync_success = True
                    
                    log.info(f"=== 时间同步模块初始化 ===")
                    log.info(f"系统当前时间: {local_time.strftime('%Y-%m-%d %H:%M:%S')}")
                    log.info(f"北京时间: {server_time.strftime('%Y-%m-%d %H:%M:%S')}")
                    log.info(f"时间偏移量: {self._time_offset:+.3f} 秒")
                    log.info(f"=========================")
                else:
                    log.warning("bjtime.org.cn 响应中未找到 Date 头，使用本地时间")
                    self._sync_success = False
        except Exception as e:
            log.warning(f"无法访问 bjtime.org.cn ({e})，使用本地时间")
            self._sync_success = False
        
        self._initialized = True
    
    def get_synced_time(self) -> datetime:
        """获取校正后的北京时间"""
        bj_tz = timezone(timedelta(hours=8))
        if self._sync_success:
            local_time = time.time() + self._time_offset
            return datetime.fromtimestamp(local_time, tz=bj_tz)
        else:
            # 使用本地系统时间
            return datetime.now(bj_tz)
    
    def get_synced_date_string(self, format_str: str = "%y%m%d") -> str:
        """获取校正后的日期字符串"""
        synced_time = self.get_synced_time()
        return synced_time.strftime(format_str)


def get_time_sync_manager() -> TimeSyncManager:
    return TimeSyncManager.get_instance()
