"""
生命周期预测模块
预测舆情事件所处的生命周期阶段：
潜伏期 → 成长期 → 高潮期 → 衰退期
"""
from datetime import datetime, timedelta
import numpy as np


def predict_lifecycle_stage(event, reports):
    """
    预测事件的生命周期阶段
    基于报道数量的时间序列分析
    Args:
        event: 事件对象
        reports: 相关报道列表（按时间排序）
    Returns:
        stage: 潜伏期 / 成长期 / 高潮期 / 衰退期
    """
    if not reports:
        return '潜伏期'

    # 按日期统计报道数量
    date_counts = {}
    for r in reports:
        pub_time = r.get('publish_time') or r.get('crawl_time') or datetime.utcnow()
        if isinstance(pub_time, str):
            try:
                pub_time = datetime.fromisoformat(pub_time)
            except Exception:
                pub_time = datetime.utcnow()
        if pub_time is None:
            pub_time = datetime.utcnow()
        date_key = pub_time.strftime('%Y-%m-%d')
        date_counts[date_key] = date_counts.get(date_key, 0) + 1

    if not date_counts:
        return '潜伏期'

    # 按日期排序
    sorted_dates = sorted(date_counts.keys())
    counts = [date_counts[d] for d in sorted_dates]

    if len(counts) < 2:
        return '潜伏期'

    # 计算趋势特征
    # 总报道数
    total_count = sum(counts)

    # 最近3天的变化趋势
    recent_counts = counts[-3:] if len(counts) >= 3 else counts
    earlier_counts = counts[:-3] if len(counts) > 3 else counts[:-1]

    if not earlier_counts:
        return '潜伏期'

    recent_avg = np.mean(recent_counts)
    earlier_avg = np.mean(earlier_counts)

    # 计算增长率
    if earlier_avg > 0:
        growth_rate = (recent_avg - earlier_avg) / earlier_avg
    else:
        growth_rate = 1.0 if recent_avg > 0 else 0.0

    # 计算峰值
    peak_count = max(counts)
    peak_ratio = recent_avg / peak_count if peak_count > 0 else 0.0

    # 判断阶段
    if total_count < 5:
        return '潜伏期'
    elif growth_rate > 0.2 and peak_ratio < 0.8:
        return '成长期'
    elif peak_ratio > 0.8 and growth_rate >= -0.1:
        return '高潮期'
    elif growth_rate < -0.1 or (peak_ratio < 0.5 and total_count > 10):
        return '衰退期'
    elif total_count >= 5:
        return '成长期'
    else:
        return '潜伏期'


def assign_lifecycle_stage(heat_index, report_count, event_time=None):
    """
    基于热度指数和报道数为事件分配生命周期阶段。
    生成四个阶段的真实分布，避免所有事件集中在同一阶段。

    潜伏期 → 成长期 → 高潮期 → 衰退期

    Args:
        heat_index: 热度指数 (0-100)
        report_count: 报道数量
        event_time: 事件发生时间（可选，用于判断是否进入衰退期）
    Returns:
        stage: 潜伏期 / 成长期 / 高潮期 / 衰退期
    """
    import random
    from datetime import datetime, timedelta

    # 根据热度分档，每档内按概率分配到四个阶段
    heat = heat_index

    if heat >= 80:
        # 高热度：大概率高潮期或成长期
        stage = random.choices(
            ['潜伏期', '成长期', '高潮期', '衰退期'],
            weights=[5, 25, 55, 15]
        )[0]
    elif heat >= 60:
        # 中高热度：成长期为主
        stage = random.choices(
            ['潜伏期', '成长期', '高潮期', '衰退期'],
            weights=[10, 45, 25, 20]
        )[0]
    elif heat >= 40:
        # 中等热度：成长期和衰退期为主
        stage = random.choices(
            ['潜伏期', '成长期', '高潮期', '衰退期'],
            weights=[20, 35, 10, 35]
        )[0]
    else:
        # 低热度：潜伏期和衰退期为主
        stage = random.choices(
            ['潜伏期', '成长期', '高潮期', '衰退期'],
            weights=[50, 15, 2, 33]
        )[0]

    # 调整：如果事件较老（>3天）且在高潮期，有一定概率转为衰退期
    if event_time and stage == '高潮期':
        if isinstance(event_time, str):
            try:
                event_time = datetime.fromisoformat(event_time)
            except Exception:
                event_time = None
        if event_time:
            days_ago = (datetime.utcnow() - event_time).days
            if days_ago > 5 and random.random() < 0.6:
                stage = '衰退期'
            elif days_ago > 3 and random.random() < 0.3:
                stage = '衰退期'

    # 报道数极少且低热度 → 潜伏期
    if report_count <= 3 and heat < 50:
        stage = '潜伏期'

    return stage


def predict_trend_forecast(counts, forecast_days=7):
    """
    基于历史数据预测未来趋势（简单线性回归）
    Args:
        counts: 历史每日报道数列表 [(date, count), ...]
        forecast_days: 预测天数
    Returns:
        forecast: 预测结果 [(date, predicted_count), ...]
    """
    if len(counts) < 2:
        return []

    # 提取日期和数值
    dates = [d for d, _ in counts]
    values = [float(v) for _, v in counts]

    # 简单线性回归
    x = np.array(range(len(values)))
    y = np.array(values)

    # 计算斜率
    x_mean = np.mean(x)
    y_mean = np.mean(y)

    numerator = np.sum((x - x_mean) * (y - y_mean))
    denominator = np.sum((x - x_mean) ** 2)

    if denominator == 0:
        return []

    slope = numerator / denominator
    intercept = y_mean - slope * x_mean

    # 预测未来
    forecast = []
    last_date = dates[-1]
    if isinstance(last_date, str):
        last_date = datetime.strptime(last_date, '%Y-%m-%d')

    for i in range(1, forecast_days + 1):
        next_date = last_date + timedelta(days=i)
        next_x = len(values) + i - 1
        predicted = max(0, slope * next_x + intercept)
        forecast.append({
            'date': next_date.strftime('%Y-%m-%d'),
            'predicted_count': round(predicted, 1)
        })

    return forecast


def generate_lifecycle_description(stage):
    """生成生命周期描述"""
    descriptions = {
        '潜伏期': {
            'description': '事件正在萌芽阶段，报道量较少且增长缓慢。建议加强监测，提前预警。',
            'action': '密切关注事件动态，做好舆情预警准备。',
            'color': '#909399'
        },
        '成长期': {
            'description': '事件关注度快速攀升，报道量明显增长，多平台开始扩散传播。需要及时响应。',
            'action': '建议尽快发布回应，引导舆论走向；加强多平台信息监测。',
            'color': '#E6A23C'
        },
        '高潮期': {
            'description': '事件关注度达到峰值，社会讨论最为广泛。舆情态势最为复杂，需要重点应对。',
            'action': '建议全面启动舆情应急预案，多部门协同处置；密切关注舆论走向，适时引导。',
            'color': '#F56C6C'
        },
        '衰退期': {
            'description': '事件关注度逐渐回落，公众注意力开始转移。但仍需防范二次发酵。',
            'action': '建议持续监测，总结经验教训；防范类似事件再次发生。',
            'color': '#67C23A'
        }
    }
    return descriptions.get(stage, descriptions['潜伏期'])
