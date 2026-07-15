"""
事件传播路径分析模块 v2
- 识别关键传播节点：首发、首次大V转发、首次官媒介入
- 构建传播路径图和时间线
- 计算传播速度、影响力等指标
"""
import json
from datetime import datetime, timedelta


def classify_report_node(report, is_original=False, node_meta=None):
    """
    分类报道的传播节点类型

    Returns:
        {'node_type': 'origin'|'official'|'vip_repost'|'normal',
         'description': str, 'author_type': str, 'priority': int}
    """
    if is_original:
        return {
            'node_type': 'origin',
            'description': '信息首发',
            'author_type': 'origin',
            'priority': 0,
        }

    author_type = 'normal'
    media_name = None
    if node_meta:
        author_type = node_meta.get('author_type', 'normal')
        media_name = node_meta.get('media_name')

    if author_type == 'official_media':
        media_label = media_name or '官方媒体'
        return {
            'node_type': 'official',
            'description': f'{media_label}介入报道',
            'author_type': 'official_media',
            'priority': 1,
        }
    elif author_type == 'influencer':
        return {
            'node_type': 'vip_repost',
            'description': '大V/认证用户转发，推动话题扩散',
            'author_type': 'influencer',
            'priority': 2,
        }
    else:
        return {
            'node_type': 'normal',
            'description': '普通传播节点',
            'author_type': 'normal',
            'priority': 3,
        }


def build_propagation_timeline(reports, origin_time=None):
    """
    构建传播时间线 — 按时间排列所有关键事件

    Returns:
        timeline: 按时间排序的事件列表，每个事件包含绝对时间和相对时间差
    """
    if not origin_time:
        origin_time = reports[0].publish_time if reports else datetime.utcnow()

    timeline = []
    seen_type_keys = set()

    for r in reports:
        pub_time = getattr(r, 'publish_time', None)

        formatted_time = ''
        delta_str = ''
        if pub_time:
            formatted_time = pub_time.strftime('%Y-%m-%d %H:%M')
            delta = pub_time - origin_time
            total_min = delta.total_seconds() / 60
            if total_min < 0:
                delta_str = ''
            elif total_min < 60:
                delta_str = f'{int(total_min)}分钟后'
            elif total_min < 1440:
                h = int(total_min / 60)
                m = int(total_min % 60)
                delta_str = f'{h}小时{m}分钟后' if m > 0 else f'{h}小时后'
            else:
                d = int(total_min / 1440)
                h = int((total_min % 1440) / 60)
                delta_str = f'{d}天{h}小时后' if h > 0 else f'{d}天后'

        node_type = getattr(r, 'node_type', '') or 'normal'
        is_original = getattr(r, 'is_original', False)
        author = getattr(r, 'author', '') or ''
        platform = getattr(r, 'platform', '') or ''
        title = getattr(r, 'title', '') or ''
        url = getattr(r, 'source_url', '') or ''

        # 节点描述
        if is_original or node_type == 'origin':
            event_desc = f'📌 {platform}首发：{title[:40]}'
        elif node_type == 'official':
            event_desc = f'📰 {author}（{platform}）介入报道'
        elif node_type == 'vip_repost':
            event_desc = f'🔥 {author}（{platform}）转发，话题引爆'
        elif node_type == 'normal':
            event_desc = f'📡 {platform}平台跟进传播'
        else:
            event_desc = f'{platform}报道'

        # 避免重复同类型（但保留 origin + 每个平台的首次 official/vip）
        if node_type == 'origin':
            type_key = 'origin'
        elif node_type in ('official', 'vip_repost'):
            type_key = f'{node_type}_{platform}'
        else:
            type_key = f'normal_{platform}'

        if type_key not in seen_type_keys or node_type == 'origin':
            timeline.append({
                'time': pub_time.isoformat() if pub_time else '',
                'formatted_time': formatted_time,
                'delta': delta_str,
                'event': event_desc,
                'type': node_type,
                'platform': platform,
                'author': author,
                'url': url,
            })
            if node_type != 'normal':
                seen_type_keys.add(type_key)

    # 按时间排序
    timeline.sort(key=lambda t: t['time'])
    return timeline


def analyze_propagation(event, all_reports):
    """
    分析事件的传播路径（v2）
    - 识别首发、首次大V转发、首次官媒介入
    - 构建按时间排序的关键节点链
    - 计算传播速度和影响力指标

    Returns:
        source_trace dict
    """
    if not all_reports:
        return _empty_trace()

    # 按时间排序
    sorted_reports = sorted(all_reports, key=lambda r: getattr(r, 'publish_time', datetime.utcnow()))

    # 分类提取
    origin_reports = [r for r in sorted_reports if getattr(r, 'is_original', False)]
    key_reports = [r for r in sorted_reports if getattr(r, 'is_key_node', False) and not getattr(r, 'is_original', False)]
    official_reports = [r for r in sorted_reports if getattr(r, 'node_type', '') == 'official']
    vip_reports = [r for r in sorted_reports if getattr(r, 'node_type', '') == 'vip_repost']
    normal_reports = [r for r in sorted_reports if getattr(r, 'node_type', '') == 'normal'
                      and not getattr(r, 'is_original', False) and not getattr(r, 'is_key_node', False)]

    # 首发
    origin = origin_reports[0] if origin_reports else sorted_reports[0]
    origin_time = getattr(origin, 'publish_time', None) or datetime.utcnow()
    origin_platform = getattr(origin, 'platform', '') or '未知'
    origin_url = getattr(origin, 'source_url', '') or ''
    origin_author = getattr(origin, 'author', '') or '未知'

    origin_time_str = origin_time.isoformat() if hasattr(origin_time, 'isoformat') else str(origin_time)
    origin_formatted = origin_time.strftime('%Y-%m-%d %H:%M') if hasattr(origin_time, 'strftime') else origin_time_str

    # ---- 构建关键节点（按时间排序） ----
    key_nodes = []

    # 1. 首发节点
    key_nodes.append({
        'type': 'origin',
        'platform': origin_platform,
        'time': origin_time_str,
        'formatted_time': origin_formatted,
        'url': origin_url,
        'author': origin_author,
        'description': f'📌 事件首发：{origin_platform}平台最先出现该热搜话题',
        'icon': 'origin',
    })

    # 2. 首次大V转发节点
    first_vip = None
    if vip_reports:
        first_vip = vip_reports[0]
        r = first_vip
        r_time = getattr(r, 'publish_time', None)
        time_str = r_time.isoformat() if hasattr(r_time, 'isoformat') else origin_time_str
        formatted = r_time.strftime('%Y-%m-%d %H:%M') if hasattr(r_time, 'strftime') else origin_formatted
        delta = _calc_delta(r_time, origin_time)
        key_nodes.append({
            'type': 'vip_repost',
            'platform': getattr(r, 'platform', '') or '',
            'time': time_str,
            'formatted_time': formatted,
            'delta': delta,
            'url': getattr(r, 'source_url', '') or '',
            'author': getattr(r, 'author', '') or '',
            'description': f'🔥 首次大V转发：{getattr(r, "author", "意见领袖")} 在 {getattr(r, "platform", "")} 转发，话题开始扩散',
            'icon': 'vip',
        })

    # 3. 首次官媒介入节点
    first_official = None
    if official_reports:
        first_official = official_reports[0]
        r = first_official
        r_time = getattr(r, 'publish_time', None)
        time_str = r_time.isoformat() if hasattr(r_time, 'isoformat') else origin_time_str
        formatted = r_time.strftime('%Y-%m-%d %H:%M') if hasattr(r_time, 'strftime') else origin_formatted
        delta = _calc_delta(r_time, origin_time)
        key_nodes.append({
            'type': 'official',
            'platform': getattr(r, 'platform', '') or '',
            'time': time_str,
            'formatted_time': formatted,
            'delta': delta,
            'url': getattr(r, 'source_url', '') or '',
            'author': getattr(r, 'author', '') or '',
            'description': f'📰 首次官媒介入：{getattr(r, "author", "权威媒体")} 正式报道，事件进入公众视野',
            'icon': 'official',
        })

    # 4. 其他关键节点（不同平台的首次大V/官媒）
    seen_authors = {getattr(origin, 'author', '')}
    if first_vip:
        seen_authors.add(getattr(first_vip, 'author', ''))
    if first_official:
        seen_authors.add(getattr(first_official, 'author', ''))

    for r in vip_reports[1:3] + official_reports[1:3]:
        author = getattr(r, 'author', '')
        if author not in seen_authors:
            seen_authors.add(author)
            node_type = 'vip_repost' if getattr(r, 'node_type', '') == 'vip_repost' else 'official'
            r_time = getattr(r, 'publish_time', None)
            time_str = r_time.isoformat() if r_time else origin_time_str
            formatted = r_time.strftime('%Y-%m-%d %H:%M') if r_time else origin_formatted
            delta = _calc_delta(r_time, origin_time)
            key_nodes.append({
                'type': node_type,
                'platform': getattr(r, 'platform', '') or '',
                'time': time_str,
                'formatted_time': formatted,
                'delta': delta,
                'url': getattr(r, 'source_url', '') or '',
                'author': author,
                'description': f'{getattr(r, "author", "")}（{getattr(r, "platform", "")}）加入传播',
                'icon': 'key',
            })

    # 按时间排序
    key_nodes.sort(key=lambda n: n['time'])

    # ---- 构建传播阶段 ----
    propagation_stages = _build_stages(origin_time, key_nodes, official_reports, vip_reports, all_reports)

    # ---- 构建时间线 ----
    timeline = build_propagation_timeline(sorted_reports, origin_time)

    # ---- 传播指标 ----
    metrics = _calc_metrics(origin_time, key_nodes, all_reports)

    # ---- 平台统计 ----
    platform_set = set()
    platform_detail = {}
    for r in all_reports:
        p = getattr(r, 'platform', '')
        if p:
            platform_set.add(p)
            if p not in platform_detail:
                platform_detail[p] = {'total': 0, 'key': 0, 'official': 0, 'vip': 0, 'normal': 0}
            platform_detail[p]['total'] += 1
            nt = getattr(r, 'node_type', '') or 'normal'
            if getattr(r, 'is_original', False):
                platform_detail[p]['key'] += 1
            elif nt == 'official':
                platform_detail[p]['official'] += 1
            elif nt == 'vip_repost':
                platform_detail[p]['vip'] += 1
            else:
                platform_detail[p]['normal'] += 1

    return {
        'initial_source': {
            'platform': origin_platform,
            'url': origin_url,
            'time': origin_time_str,
            'formatted_time': origin_formatted,
            'author': origin_author,
            'author_type': 'origin',
            'description': f'事件最早由{origin_platform}热搜话题引爆',
        },
        'key_nodes': key_nodes,
        'propagation_timeline': timeline,
        'propagation_stages': propagation_stages,
        'propagation_metrics': metrics,
        'platform_summary': {
            'total_platforms': len(platform_set),
            'platforms': list(platform_set),
            'platform_detail': platform_detail,
            'total_reports': len(all_reports),
            'key_report_count': len(key_reports),
            'official_report_count': len(official_reports),
            'vip_report_count': len(vip_reports),
            'normal_report_count': len(normal_reports),
        },
    }


def _calc_delta(r_time, origin_time):
    """计算与首发的时间差（人类可读）"""
    if not r_time or not origin_time:
        return ''
    delta = r_time - origin_time
    total_min = delta.total_seconds() / 60
    if total_min < 0:
        return ''
    elif total_min < 60:
        return f'{int(total_min)}分钟'
    elif total_min < 1440:
        return f'{int(total_min / 60)}小时'
    else:
        return f'{int(total_min / 1440)}天'


def _build_stages(origin_time, key_nodes, official_reports, vip_reports, all_reports):
    """构建传播阶段描述"""
    stages = []

    # 潜伏期
    stages.append({
        'stage': '潜伏期',
        'icon': '🌱',
        'description': f'话题在首发平台出现，尚未引起广泛关注',
        'time_range': 'T+0',
    })

    # 扩散期（首次大V转发后）
    vip_times = [n.get('formatted_time', '') for n in key_nodes if n['type'] == 'vip_repost']
    if vip_times:
        stages.append({
            'stage': '扩散期',
            'icon': '🔥',
            'description': f'大V/意见领袖转发扩散，话题开始跨平台传播',
            'time_range': vip_times[0],
        })

    # 爆发期（官媒介入后）
    official_times = [n.get('formatted_time', '') for n in key_nodes if n['type'] == 'official']
    if official_times:
        stages.append({
            'stage': '爆发期',
            'icon': '💥',
            'description': f'官方媒体正式介入报道，事件进入公众视野，讨论量激增',
            'time_range': official_times[0],
        })

    # 持续期
    if len(all_reports) >= 4:
        last_time = all_reports[-1].publish_time
        last_formatted = last_time.strftime('%Y-%m-%d %H:%M') if last_time else ''
        stages.append({
            'stage': '持续期',
            'icon': '📊',
            'description': f'多平台持续跟进报道，事件深度发酵',
            'time_range': last_formatted,
        })

    return stages


def _calc_metrics(origin_time, key_nodes, all_reports):
    """计算传播指标"""
    now = datetime.utcnow()

    # 首次响应时间（origin → first vip/official）
    first_response_node = None
    for node in key_nodes:
        if node['type'] in ('vip_repost', 'official'):
            first_response_node = node
            break

    first_response_delta = ''
    first_response_time = ''
    if first_response_node:
        first_response_time = first_response_node.get('formatted_time', '')
        first_response_delta = first_response_node.get('delta', '')

    # 传播速度（关键节点时间跨度）
    key_times = [n.get('time', '') for n in key_nodes if n.get('time')]
    propagation_span = ''
    if len(key_times) >= 2:
        try:
            t0 = datetime.fromisoformat(key_times[0])
            t1 = datetime.fromisoformat(key_times[-1])
            span_min = (t1 - t0).total_seconds() / 60
            if span_min < 60:
                propagation_span = f'{int(span_min)}分钟'
            elif span_min < 1440:
                propagation_span = f'{span_min / 60:.1f}小时'
            else:
                propagation_span = f'{span_min / 1440:.1f}天'
        except Exception:
            pass

    # 平台覆盖
    platforms = set()
    for r in all_reports:
        p = getattr(r, 'platform', '')
        if p:
            platforms.add(p)

    # 传播层级（origin → vip → official → normal 的最大深度）
    has_vip = any(n['type'] == 'vip_repost' for n in key_nodes)
    has_official = any(n['type'] == 'official' for n in key_nodes)
    depth = 1 + int(has_vip) + int(has_official)

    return {
        'first_response_time': first_response_time,
        'first_response_delta': first_response_delta,
        'propagation_span': propagation_span,
        'platform_count': len(platforms),
        'propagation_depth': depth,
        'total_reports': len(all_reports),
        'key_node_count': len(key_nodes),
    }


def _empty_trace():
    return {
        'initial_source': {
            'platform': '未知', 'url': '', 'time': '', 'formatted_time': '',
            'author': '', 'author_type': 'normal',
            'description': ''
        },
        'key_nodes': [],
        'propagation_timeline': [],
        'propagation_stages': [],
        'propagation_metrics': {
            'first_response_time': '', 'first_response_delta': '',
            'propagation_span': '', 'platform_count': 0,
            'propagation_depth': 0, 'total_reports': 0, 'key_node_count': 0,
        },
        'platform_summary': {
            'total_platforms': 0, 'platforms': [], 'platform_detail': {},
            'total_reports': 0, 'key_report_count': 0,
            'official_report_count': 0, 'vip_report_count': 0, 'normal_report_count': 0,
        },
    }
