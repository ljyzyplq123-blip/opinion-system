/**
 * Dashboard JS - 舆情看板
 */
let currentSort = 'heat';
let currentPage = 1;
let currentCategory = '';

document.addEventListener('DOMContentLoaded', () => {
    loadStats();
    loadEvents();
    loadCategoryChart();
    loadLifecycleChart();
    checkDataSource();
});

// 检查数据来源
async function checkDataSource() {
    try {
        const resp = await axios.get('/api/crawler/status');
        if (resp.data.success) {
            const usingReal = resp.data.global.use_real_crawler;
            const btn = document.getElementById('refreshRealBtn');
            if (btn) {
                btn.className = usingReal
                    ? 'btn btn-success btn-sm'
                    : 'btn btn-warning btn-sm';
            }
        }
    } catch (err) { /* ignore */ }
}

// 一键刷新真实数据
async function refreshRealData() {
    const btn = document.getElementById('refreshRealBtn');
    if (!confirm('将用真实热搜数据替换当前所有事件，确定继续？\n\n需要爬虫已配置Cookie（个人中心→爬虫配置）')) return;

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> 爬取中...';

    try {
        const resp = await axios.post('/api/crawler/refresh-events', {}, { timeout: 120000 });
        if (resp.data.success) {
            showToast(`✅ 已用真实热搜数据刷新！共 ${resp.data.count} 个事件`, 'success');
            // 重新加载数据
            loadStats();
            loadEvents(1);
            loadCategoryChart();
            loadLifecycleChart();
        } else {
            showToast('❌ ' + (resp.data.message || '刷新失败'), 'error');
            console.log(resp.data.log);
        }
    } catch (err) {
        showToast('❌ 刷新失败: ' + (err.response?.data?.message || err.message), 'error');
    }

    btn.disabled = false;
    btn.innerHTML = '<i class="bi bi-cloud-download"></i> 刷新真实热搜数据';
}

// 加载统计数据
async function loadStats() {
    try {
        const resp = await axios.get('/api/dashboard/stats');
        if (resp.data.success) {
            const s = resp.data.stats;
            document.getElementById('statTotalEvents').textContent = s.total_events;
            document.getElementById('statHighRisk').textContent = s.high_risk_count;
            document.getElementById('statTodayEvents').textContent = s.today_events;
            document.getElementById('statTotalReports').textContent = formatNumber(s.total_reports);
        }
    } catch (err) {
        console.error('加载统计数据失败:', err);
    }
}

// 加载事件列表
async function loadEvents(page = 1) {
    const list = document.getElementById('eventList');
    list.innerHTML = `<div class="text-center py-5"><div class="spinner-border text-primary"></div><p class="mt-2 text-muted">加载中...</p></div>`;

    try {
        const resp = await axios.get('/api/dashboard', {
            params: { sort: currentSort, category: currentCategory, page: page, per_page: 20 }
        });
        if (resp.data.success) {
            renderEventList(resp.data.events);
            renderPagination(resp.data);
            currentPage = page;
        }
    } catch (err) {
        list.innerHTML = `<div class="text-center py-5 text-danger">加载失败: ${err.message}</div>`;
    }
}

// 渲染事件列表
function renderEventList(events) {
    const list = document.getElementById('eventList');
    if (!events.length) {
        list.innerHTML = '<div class="text-center py-5 text-muted">暂无事件数据</div>';
        return;
    }

    let html = '<div class="list-group list-group-flush">';
    events.forEach((e, i) => {
        const riskBadge = e.risk_level === '高' ? 'bg-danger' : (e.risk_level === '中' ? 'bg-warning' : 'bg-success');
        const lifecycleColor = {
            '潜伏期': '#909399', '成长期': '#E6A23C', '高潮期': '#F56C6C', '衰退期': '#67C23A'
        }[e.lifecycle_stage] || '#909399';

        // 情感颜色条
        const posW = (e.positive_ratio * 100).toFixed(0);
        const negW = (e.negative_ratio * 100).toFixed(0);
        const neuW = (e.neutral_ratio * 100).toFixed(0);

        html += `
        <a href="/event/${e.id}" class="list-group-item list-group-item-action event-item">
            <div class="d-flex justify-content-between align-items-start">
                <div class="flex-grow-1 me-3">
                    <div class="d-flex align-items-center gap-2 mb-1">
                        <span class="badge ${riskBadge}">${e.risk_level}风险</span>
                        <span class="badge" style="background:${lifecycleColor};color:#fff;">${e.lifecycle_stage}</span>
                        <span class="badge bg-secondary">${e.category}</span>
                        <small class="text-muted">${formatDate(e.event_time)}</small>
                    </div>
                    <h6 class="mb-1 fw-bold">${e.title}</h6>
                    <p class="mb-1 text-muted small event-summary">${e.summary ? e.summary.substring(0, 80) + '...' : ''}</p>
                    <!-- 情感分布条 -->
                    <div class="d-flex align-items-center gap-2 mt-2" style="max-width:300px;">
                        <small class="text-success" style="width:40px;">正面${posW}%</small>
                        <div class="progress flex-grow-1" style="height:6px;">
                            <div class="progress-bar bg-success" style="width:${posW}%"></div>
                            <div class="progress-bar bg-secondary" style="width:${neuW}%"></div>
                            <div class="progress-bar bg-danger" style="width:${negW}%"></div>
                        </div>
                        <small class="text-danger" style="width:40px;text-align:right;">负面${negW}%</small>
                    </div>
                </div>
                <div class="text-end">
                    <div class="fs-4 fw-bold text-danger">${e.heat_index}</div>
                    <small class="text-muted">热度指数</small>
                    <div class="mt-1">
                        <small class="text-muted">
                            <i class="bi bi-chat-dots"></i> ${e.report_count}篇报道
                        </small>
                    </div>
                </div>
            </div>
        </a>`;
    });
    html += '</div>';
    list.innerHTML = html;
}

// 渲染分页
function renderPagination(data) {
    const footer = document.getElementById('paginationFooter');
    if (data.pages <= 1) {
        footer.innerHTML = '';
        return;
    }

    let html = '<nav><ul class="pagination pagination-sm justify-content-center mb-0">';
    html += `<li class="page-item ${data.page <= 1 ? 'disabled' : ''}">
        <a class="page-link" href="#" onclick="loadEvents(${data.page-1});return false;">上一页</a></li>`;

    for (let i = 1; i <= data.pages; i++) {
        if (Math.abs(i - data.page) <= 2 || i === 1 || i === data.pages) {
            html += `<li class="page-item ${i === data.page ? 'active' : ''}">
                <a class="page-link" href="#" onclick="loadEvents(${i});return false;">${i}</a></li>`;
        } else if (Math.abs(i - data.page) === 3) {
            html += '<li class="page-item disabled"><span class="page-link">...</span></li>';
        }
    }

    html += `<li class="page-item ${!data.has_next ? 'disabled' : ''}">
        <a class="page-link" href="#" onclick="loadEvents(${data.page+1});return false;">下一页</a></li>`;
    html += '</ul></nav>';
    footer.innerHTML = html;
}

// 排序切换
function sortEvents(sort, btn) {
    currentSort = sort;
    // 更新按钮状态
    document.querySelectorAll('.btn-group .btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    loadEvents(1);
}

// 分类分布图
async function loadCategoryChart() {
    try {
        const resp = await axios.get('/api/dashboard/stats');
        if (!resp.data.success) return;

        const categories = resp.data.stats.categories || [];
        const chart = echarts.init(document.getElementById('categoryChart'));
        chart.setOption({
            tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
            legend: { bottom: 0, textStyle: { fontSize: 11 } },
            series: [{
                type: 'pie',
                radius: ['40%', '70%'],
                center: ['50%', '45%'],
                avoidLabelOverlap: false,
                itemStyle: { borderRadius: 4, borderColor: '#fff', borderWidth: 2 },
                label: { show: true, formatter: '{b}\n{d}%', fontSize: 10 },
                data: categories.map(c => ({ name: c.name, value: c.count }))
            }]
        });
        window.addEventListener('resize', () => chart.resize());
    } catch (err) {
        console.error('加载分类图失败:', err);
    }
}

// 生命周期分布图
async function loadLifecycleChart() {
    try {
        const resp = await axios.get('/api/dashboard/stats');
        if (!resp.data.success) return;

        const lifecycle = resp.data.stats.lifecycle || [];
        const stages = ['潜伏期', '成长期', '高潮期', '衰退期'];
        const colors = ['#909399', '#E6A23C', '#F56C6C', '#67C23A'];
        const data = stages.map(s => {
            const found = lifecycle.find(l => l.stage === s);
            return found ? found.count : 0;
        });

        const chart = echarts.init(document.getElementById('lifecycleChart'));
        chart.setOption({
            tooltip: { trigger: 'axis' },
            grid: { left: '15%', right: '10%', top: 10, bottom: 20 },
            xAxis: {
                type: 'category',
                data: stages,
                axisLabel: { fontSize: 10 }
            },
            yAxis: { type: 'value', show: false },
            series: [{
                type: 'bar',
                data: data.map((d, i) => ({
                    value: d,
                    itemStyle: { color: colors[i], borderRadius: [4, 4, 0, 0] }
                })),
                barWidth: '50%',
                label: { show: true, position: 'top', fontSize: 12, fontWeight: 'bold' }
            }]
        });
        window.addEventListener('resize', () => chart.resize());
    } catch (err) {
        console.error('加载生命周期图失败:', err);
    }
}
