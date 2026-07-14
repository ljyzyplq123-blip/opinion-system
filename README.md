# 网络舆情事件智能分析系统

> 大型程序设计实践课程项目

实时抓取微博、百度、知乎、今日头条等平台热搜数据，自动进行情感分析、虚假检测、生命周期预测，提供舆情看板、事件溯源和智能问答功能。

---

## 功能特性

- 🔥 **实时热搜抓取** — 自动爬取多平台热搜数据，始终使用真实数据
- 📊 **舆情看板** — 事件总览、分类统计、生命周期分布、热度排行
- 📈 **事件详情** — 完整舆情画像：趋势图、情感扇形图、平台分布、关键词云
- 😊 **情感分析** — 基于 jieba 分词和情感词典的正/负/中性分析
- 🔍 **虚假检测** — 四维度检测：标题党、来源可信度、内容一致性、语言特征
- 🧬 **生命周期** — 潜伏期→成长期→高潮期→衰退期 四阶段判定
- 🔗 **事件溯源** — 跨平台传播路径图谱，首发→扩散→跟进
- 🤖 **智能问答** — 支持 DeepSeek R1/V3 等大模型，带本地 fallback
- 👤 **个人中心** — 监控平台配置、Cookie 管理、LLM 配置

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python · Flask · SQLAlchemy · SQLite |
| 前端 | Bootstrap 5 · ECharts · Axios · Jinja2 |
| NLP | jieba 分词 · scikit-learn (TF-IDF / KMeans / DBSCAN) |
| 爬虫 | requests · BeautifulSoup4 |
| LLM | DeepSeek API（兼容 OpenAI 格式） |

---

## 快速开始

### 1. 安装依赖

```bash
cd opinion_system
pip install -r requirements.txt
```

### 2. 配置 LLM（智能问答）

启动后在浏览器中进入**个人中心 → 大模型配置**，填入 DeepSeek API Key。

或直接在 `opinion_system/llm_config.json` 中配置：

```json
{
  "api_url": "https://api.deepseek.com/v1/chat/completions",
  "api_key": "sk-你的APIKey",
  "model": "deepseek-chat"
}
```

### 3. 启动

```bash
cd opinion_system
python app.py
```

### 4. 访问

打开浏览器访问 `http://localhost:5000`

**演示账号**：`admin` / `admin123`

---

## 项目结构

```
opinion_system/
├── app.py                 # Flask 应用入口，启动自动爬取 + 定时刷新
├── config.py              # 系统配置（数据库/NLP/LLM）
├── models.py              # 8 张数据表 ORM 模型
├── auth.py                # 登录/注册/页面路由
├── requirements.txt       # Python 依赖
│
├── api/                   # REST API
│   ├── dashboard_api.py   #   看板统计
│   ├── event_api.py       #   事件详情/趋势/溯源/虚假检测
│   ├── qa_api.py          #   智能问答
│   ├── user_api.py        #   监控源/关键词/LLM配置
│   └── crawler_api.py     #   爬虫控制
│
├── crawler/               # 多平台爬虫
│   ├── spider.py          #   微博/百度/知乎/头条/B站 真实爬虫
│   └── crawler_config.py  #   Cookie/认证配置
│
├── nlp/                   # 自然语言处理
│   ├── sentiment.py       #   情感分析（词典法）
│   ├── segmentation.py    #   分词 + TF-IDF 关键词提取
│   ├── fake_detect.py     #   虚假信息四维检测
│   ├── lifecycle.py       #   生命周期阶段预测
│   ├── hotspot.py         #   热点发现 + 分类 + 风险预测
│   └── clustering.py      #   DBSCAN 聚类 + 热度计算
│
├── llm/qa.py              # LLM 服务封装
├── data/demo_data.py      # 演示数据生成器
├── scripts/               # 工具脚本
├── templates/             # Jinja2 前端页面
└── static/                # CSS/JS/字体
```

---

## 数据库设计

| 表 | 说明 |
|---|------|
| `users` | 用户账号 |
| `monitored_sources` | 监控平台配置（决定爬取哪些平台） |
| `monitored_keywords` | 关注关键词 |
| `events` | 舆情事件（热度/风险/阶段/情感占比） |
| `event_reports` | 事件报道（情感得分/关键节点标记） |
| `event_keywords` | 事件关键词（TF-IDF 权重） |
| `event_trends` | 每日趋势数据 |
| `qa_history` | 智能问答历史 |

---

## 配置文件说明

以下文件首次启动后自动生成，不跟随 Git：

| 文件 | 说明 |
|------|------|
| `llm_config.json` | LLM API 配置 |
| `crawler/crawler_config.json` | 爬虫 Cookie 认证 |

在**个人中心**可在线配置，无需手动编辑。

---

## License

MIT
