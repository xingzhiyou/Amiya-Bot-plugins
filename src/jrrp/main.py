import os

from amiyabot import Message, Chain, Equal
from core import AmiyaBotPluginInstance

from .database import insert_tb, select_tb_all, select_tb_today, same_week, same_month
from .utils import calculate_luck_level, generate_luck_value, calculate_average_luck, filter_data_by_date
from .time_sync import get_time_sync_manager

curr_dir = os.path.dirname(__file__)

bot = AmiyaBotPluginInstance(
    name='今日人品',
    version='26.05.09',
    plugin_id='amiyabot-jrrp',
    plugin_type='game',
    description='一个功能完善的每日人品查询插件，支持查询今日、本周、本月和历史平均人品，自定义运势，以及数据持久化存储。',
    document=f'{curr_dir}/README.md',
    global_config_schema=f'{curr_dir}/config_schema.json',
    global_config_default=f'{curr_dir}/config_default.yaml',
)


def get_config():
    """获取完整配置"""
    return {
        'ranges': bot.get_config('ranges'),
    }


# 初始化时间同步模块
time_sync_manager = get_time_sync_manager()
time_sync_manager.initialize()


@bot.on_message(
        keywords=[Equal('jrrp'), Equal('今日人品'), Equal('今日运势')],
        check_prefix=False)
async def jrrp_command(data: Message):
    """查询今日人品"""
    user_id = data.user_id
    today_date = time_sync_manager.get_synced_date_string("%y%m%d")
    
    seed = int(today_date) + int(user_id)
    
    config = get_config()
    ranges = config.get("ranges")
    if not isinstance(ranges, list):
        ranges = []
    
    min_luck = 0
    max_luck = 100
    
    # 从 ranges 计算 min_luck/max_luck
    if ranges:
        mins = [r.get("min", 0) for r in ranges if isinstance(r, dict)]
        maxs = [r.get("max", 100) for r in ranges if isinstance(r, dict)]
        min_luck = min(mins) if mins else 0
        max_luck = max(maxs) if maxs else 100
    
    lucknum = generate_luck_value(int(min_luck), int(max_luck), seed)
    
    if not select_tb_today(user_id, today_date):
        insert_tb(user_id, lucknum, today_date)
    
    luck_level, luck_desc = calculate_luck_level(lucknum, ranges)
    
    return Chain(data).text(f'您今日的幸运指数是 {lucknum}，为"{luck_level}"，{luck_desc}')


@bot.on_message(
        keywords=[Equal('alljrrp'), Equal('总人品'), Equal('平均人品'), Equal('平均运势')],
        check_prefix=False)
async def alljrrp_command(data: Message):
    """查询历史平均人品"""
    user_id = data.user_id
    alldata = select_tb_all(user_id)
    
    if not alldata:
        return Chain(data).text('您还没有过历史人品记录！')
    
    times, avg_luck = calculate_average_luck(alldata)
    
    return Chain(data).text(f'您一共使用了 {times} 天 jrrp，您历史平均的幸运指数是 {avg_luck}')


@bot.on_message(
        keywords=[Equal('monthjrrp'), Equal('本月人品'), Equal('本月运势'), Equal('月运势')],
        check_prefix=False)
async def monthjrrp_command(data: Message):
    """查询本月平均人品"""
    user_id = data.user_id
    alldata = select_tb_all(user_id)
    
    month_data = filter_data_by_date(alldata, same_month)
    
    if not month_data:
        return Chain(data).text('您本月还没有过人品记录！')
    
    times, avg_luck = calculate_average_luck(month_data)
    
    return Chain(data).text(f'您本月共使用了 {times} 天 jrrp，平均的幸运指数是 {avg_luck}')


@bot.on_message(
        keywords=[Equal('weekjrrp'), Equal('本周人品'), Equal('本周运势'), Equal('周运势')],
        check_prefix=False)
async def weekjrrp_command(data: Message):
    """查询本周平均人品"""
    user_id = data.user_id
    alldata = select_tb_all(user_id)
    
    if not alldata:
        return Chain(data).text('您还没有过历史人品记录！')
    
    week_data = filter_data_by_date(alldata, same_week)
    
    if not week_data:
        return Chain(data).text('您本周还没有过人品记录！')
    
    times, avg_luck = calculate_average_luck(week_data)
    
    return Chain(data).text(f'您本周共使用了 {times} 天 jrrp，平均的幸运指数是 {avg_luck}')