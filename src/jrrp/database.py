import datetime
from amiyabot.database import *
from core.database import config, is_mysql
from core import log
from typing import Union, List

db = connect_database('amiya_jrrp' if is_mysql else 'database/amiya_jrrp.db', is_mysql, config)


class JrrpBaseModel(ModelClass):
    class Meta:
        database = db


@table
class JrrpData(JrrpBaseModel):
    user_id: Union[CharField, str] = CharField()
    value: int = IntegerField()
    date: str = CharField()

    class Meta:
        primary_key = False
        indexes = (
            (('user_id', 'date'), True),  # 联合唯一索引
        )


def insert_tb(user_id: str, value: int, date: str) -> None:
    """向数据库插入新的人品记录（如果已存在则忽略）"""
    try:
        JrrpData.create(user_id=user_id, value=value, date=date)
    except Exception as e:
        log.error(f"插入数据失败: {e}")


def select_tb_all(user_id: str) -> List[JrrpData]:
    """查询用户的所有历史人品记录"""
    try:
        return list(JrrpData.select().where(JrrpData.user_id == user_id).order_by(JrrpData.date.desc()))
    except Exception as e:
        log.error(f"查询历史数据失败: {e}")
        return []


def select_tb_today(user_id: str, date: str) -> bool:
    """查询用户今日是否已经查询过人品"""
    try:
        return JrrpData.select().where(
            JrrpData.user_id == user_id,
            JrrpData.date == date
        ).exists()
    except Exception as e:
        log.error(f"查询今日数据失败: {e}")
        return False


def same_week(date_string: str) -> bool:
    """判断日期字符串是否为本周"""
    try:
        date_obj = datetime.datetime.strptime(date_string, '%y%m%d')
        from .time_sync import get_time_sync_manager
        synced_time = get_time_sync_manager().get_synced_time()
        return (date_obj.isocalendar()[1] == synced_time.isocalendar()[1] and
                date_obj.year == synced_time.year)
    except ValueError:
        log.error(f"日期格式错误: {date_string}")
        return False


def same_month(date_string: str) -> bool:
    """判断日期字符串是否为本月"""
    try:
        date_obj = datetime.datetime.strptime(date_string, '%y%m%d')
        from .time_sync import get_time_sync_manager
        synced_time = get_time_sync_manager().get_synced_time()
        return (date_obj.month == synced_time.month and
                date_obj.year == synced_time.year)
    except ValueError:
        log.error(f"日期格式错误: {date_string}")
        return False
