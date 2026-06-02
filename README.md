# TheDailyMe

> 📰 你的个人化赛博日报 — 每日精选新闻，AI 智能解读

TheDailyMe 是一个基于 Python 的自动化日报生成系统，能够从多个数据源采集新闻，通过 AI 智能分析生成个性化日报，支持多种排版主题和 Web 预览。

---

## 功能特性

### 🎯 核心功能

| 功能 | 描述 |
|------|------|
| **多源数据采集** | 支持科技、气候、游戏、体育、影视、音乐六大分类，18+ 数据源 |
| **AI 智能分析** | 自动挑选头条、重写标题、生成深度摘要和今日必读 |
| **内容智能处理** | 子主题自动标注、质量评分、标题去重 |
| **多种排版主题** | 提供 Broadsheet、Swiss、Cyberpunk、Magazine 四种精美主题 |
| **Web 客户端** | 内置 Flask 服务，支持浏览器预览和配置管理 |

### 📦 数据源覆盖

| 分类 | 数据源 |
|------|--------|
| 科技 | GitHub Trending、Hacker News、V2EX |
| 气候 | Open-Meteo 天气、Carbon Brief、天气资讯 |
| 游戏 | Steam 新闻、Reddit Gaming、游民星空 |
| 体育 | ESPN、虎扑、Reddit Sports |
| 影视 | 豆瓣电影、Reddit Movies、烂番茄 |
| 音乐 | Billboard、Pitchfork、Reddit Music |

---

## 技术栈

| 分类 | 技术 | 版本要求 |
|------|------|----------|
| 语言 | Python | >= 3.10 |
| Web 框架 | Flask | >= 3.0 |
| 模板引擎 | Jinja2 | >= 3.1 |
| 配置解析 | PyYAML | >= 6.0 |
| 网络请求 | requests | >= 2.31 |
| RSS 解析 | feedparser | >= 6.0 |
| HTML 解析 | beautifulsoup4 | >= 4.12 |
| AI 服务 | OpenAI API | >= 1.0 |

---

## 环境要求

- **操作系统**: Windows 10/11、macOS 10.15+、Linux (Ubuntu 20.04+)
- **Python 版本**: 3.10 及以上
- **AI 服务**: 可选，需配置 API Key（DeepSeek 或 OpenAI）

---

## 安装与配置

### 1. 克隆项目

```bash
git clone https://github.com/yourusername/the-daily-me.git
cd the-daily-me
```

### 2. 创建虚拟环境（推荐）

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置文件

复制示例配置并修改：

```bash
cp config.example.yaml config.yaml
```

编辑 `config.yaml`：

```yaml
layout: broadsheet              # 排版主题：broadsheet/swiss/cyberpunk/magazine
user:
  name: 同学                     # 用户名（日报中显示）
  city: Beijing                  # 城市（影响天气信息）
  language: zh                   # 语言
categories:                     # 各分类权重（0-1，决定头条选择概率）
  tech: 0.25
  climate: 0.15
  gaming: 0.15
  sports: 0.15
  movies: 0.15
  music: 0.15
topic_selection:                # 主题订阅（selected=false 关闭整个分类）
  tech:
    selected: true
    sub_topics: []              # 空列表表示全部子主题，如 ["ai", "opensource"]
  climate:
    selected: true
    sub_topics: []
  gaming:
    selected: true
    sub_topics: []
  sports:
    selected: true
    sub_topics: []
  movies:
    selected: true
    sub_topics: []
  music:
    selected: true
    sub_topics: []
sources:                        # 数据源开关
  tech:
    github_trending: true
    hackernews: true
    v2ex: true
  climate:
    open_meteo: true
    weather_rss: true
    carbon_brief: true
  gaming:
    steam_rss: true
    reddit_gaming: true
    youmin_rss: true
  sports:
    espn_rss: true
    hupu: true
    reddit_sports: true
  movies:
    douban_rss: true
    reddit_movies: true
    rottentomatoes_rss: true
  music:
    reddit_music: true
    pitchfork_rss: true
    billboard_rss: true
ai:                             # AI 配置（可选，不配置则使用传统算法）
  enabled: true
  api_key: your-api-key-here    # 替换为你的 API Key
  base_url: https://api.deepseek.com/v1  # DeepSeek 或 OpenAI 地址
  model: deepseek-chat          # 模型名称
  max_input_articles: 60        # 最大输入文章数
fetch:
  articles_per_source: 3        # 每个数据源获取文章数
  headline_pool_size: 3         # 头条候选池大小
  request_timeout: 10           # 请求超时时间（秒）
```

> **注意**: AI 功能为可选配置，若不启用，头条选择将使用传统加权随机算法。

---

## 使用指南

### 方式一：Web 客户端（推荐）

```bash
# 启动 Web 服务
python app.py

# 指定端口
python app.py -p 8080

# 绑定到外部地址（允许局域网访问）
python app.py --host 0.0.0.0 --port 8080
```

启动后访问：`http://localhost:5050`

### 方式二：命令行模式

```bash
# 使用默认配置
python daily.py

# 指定配置文件
python daily.py -c my_config.yaml
```

生成的日报保存在 `output/YYYY-MM-DD.html`，用浏览器打开即可阅读。

### 方式三：作为库使用

```python
from daily import generate_daily, load_config

# 加载配置
config = load_config("config.yaml")

# 定义进度回调
def progress_callback(stage, detail):
    print(f"[{stage}] {detail}")

# 生成日报
result = generate_daily(config, progress_callback=progress_callback)

# 输出结果
print(f"日报已生成: {result['path']}")
print(f"统计: {result['stats']}")
```

---

## 项目结构

```
the-daily-me/
├── app.py                 # Web 服务入口
├── daily.py               # 核心日报生成逻辑
├── content_engine.py      # 内容处理引擎（标签、评分、去重）
├── ai_service.py          # AI 服务封装
├── config.example.yaml    # 配置文件模板
├── requirements.txt       # 依赖清单
├── sources/               # 数据源采集器
│   ├── __init__.py
│   ├── base.py            # 采集器基类
│   ├── tech/              # 科技类数据源
│   ├── climate/           # 气候类数据源
│   ├── gaming/            # 游戏类数据源
│   ├── sports/            # 体育类数据源
│   ├── movies/            # 影视类数据源
│   └── music/             # 音乐类数据源
├── templates/             # HTML 模板
│   ├── themes/            # 主题 CSS
│   │   ├── broadsheet.css
│   │   ├── swiss.css
│   │   ├── cyberpunk.css
│   │   ├── magazine.css
│   │   └── components.css
│   ├── broadsheet.html.j2
│   ├── swiss.html.j2
│   ├── cyberpunk.html.j2
│   ├── magazine.html.j2
│   ├── client.html        # Web 客户端页面
│   └── style.css
├── static/                # 静态资源
│   └── client.js          # 客户端脚本
└── output/                # 日报输出目录（自动创建）
    └── YYYY-MM-DD.html
```

---

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    TheDailyMe 系统架构                      │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐                                          │
│  │   Web UI     │  Flask 服务 (app.py)                      │
│  └──────┬───────┘                                          │
│         │                                                  │
│         ▼                                                  │
│  ┌──────────────┐     ┌──────────────┐                     │
│  │  generate    │────▶│  fetch_all   │                     │
│  │   daily()    │     │  (并发采集)   │                     │
│  └──────┬───────┘     └──────┬───────┘                     │
│         │                     │                            │
│         │              ┌──────▼──────┐                      │
│         │              │  Sources    │                      │
│         │              │ (18+数据源) │                      │
│         │              └──────┬───────┘                      │
│         │                     │                            │
│         │                     ▼                            │
│         │              ┌──────────────┐                     │
│         │              │ content_     │                     │
│         │              │  engine      │                     │
│         │              │ (标签/评分/去重)│                    │
│         │              └──────┬───────┘                     │
│         │                     │                            │
│         │                     ▼                            │
│         │              ┌──────────────┐     ┌───────────┐   │
│         │              │ pick_headline│────▶│  AI 服务   │   │
│         │              │  (_ai)       │     │ (可选)    │   │
│         │              └──────┬───────┘     └───────────┘   │
│         │                     │                            │
│         │                     ▼                            │
│         │              ┌──────────────┐                     │
│         │              │  render_html │                     │
│         │              │  (Jinja2)    │                     │
│         │              └──────┬───────┘                     │
│         │                     │                            │
│         ▼                     ▼                            │
│  ┌──────────────┐    ┌──────────────┐                      │
│  │  output/     │    │  templates/  │                      │
│  │ YYYY-MM-DD.  │    │ (主题模板)   │                      │
│  │    html      │    └──────────────┘                      │
│  └──────────────┘                                          │
└─────────────────────────────────────────────────────────────┘
```

---

## API 接口

| 端点 | 方法 | 描述 |
|------|------|------|
| `/` | GET | Web 客户端首页 |
| `/api/status` | GET | 获取当前状态 |
| `/api/generate` | POST | 触发日报生成 |
| `/api/config` | GET | 获取当前配置 |
| `/api/config` | POST | 保存配置 |
| `/api/archives` | GET | 获取日报存档列表 |
| `/api/report/<date>` | GET | 查看指定日期日报 |
| `/api/report/<date>` | DELETE | 删除指定日期日报 |
| `/api/topic-hierarchy` | GET | 获取主题层级结构 |

---

## 贡献指南

欢迎提交 Issue 和 Pull Request！

### 开发流程

1. Fork 本仓库
2. 创建特性分支：`git checkout -b feature/xxx`
3. 提交修改：`git commit -m "feat: xxx"`
4. 推送到远程：`git push origin feature/xxx`
5. 创建 Pull Request

### 代码规范

- 遵循 PEP 8 规范
- 使用类型注解
- 保持代码简洁清晰
- 添加必要的注释（仅对复杂逻辑）

---

## 许可证

MIT License

---

## 联系方式

- 项目地址：[https://github.com/yourusername/the-daily-me](https://github.com/yourusername/the-daily-me)
- 问题反馈：[Issues](https://github.com/yourusername/the-daily-me/issues)

---

*Made with ❤️ for your daily reading*
