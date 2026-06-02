"""
TheDailyMe — 内容引擎

提供：
  - 子主题自动标签匹配
  - 文章质量评分
  - 标题相似度去重
"""

import re
from typing import Callable, Optional, Dict, List, Any, Set

# ═══════════════════════════════════════════════════════════
#  子主题体系：关键词 → 子标签
# ═══════════════════════════════════════════════════════════

SUB_TOPICS = {
    "tech": {
        "ai": {"keywords": ["AI", "GPT", "LLM", "大模型", "机器学习", "深度学习", "神经网络",
                            "ChatGPT", "Copilot", "Claude", "Gemini", "人工智能", "智能"],
               "label": "AI"},
        "opensource": {"keywords": ["开源", "GitHub", "open source", "repo", "Star", "仓库"],
                       "label": "开源"},
        "security": {"keywords": ["漏洞", "安全", "攻击", "黑客", "CVE", "exploit", "bug",
                                  "隐私", "封禁", "风控"],
                     "label": "安全"},
        "programming": {"keywords": ["Python", "Rust", "Go", "TypeScript", "JavaScript",
                                     "编程", "语言", "框架", "编译器", "代码"],
                        "label": "编程"},
        "internet": {"keywords": ["互联网", "社交", "Meta", "Instagram", "Twitter", "X",
                                  "Google", "微软", "Apple", "字节", "腾讯", "阿里"],
                     "label": "互联网"},
    },
    "climate": {
        "extreme_weather": {"keywords": ["高温", "热浪", "暴雨", "洪水", "台风", "飓风",
                                          "干旱", "极端", "山火", "冰雹", "寒潮"],
                            "label": "极端天气"},
        "policy": {"keywords": ["政策", "减排", "碳", "COP", "协定", "协议", "气候峰会",
                                "碳中和", "碳达峰", "排放", "法规"],
                   "label": "气候政策"},
        "energy": {"keywords": ["能源", "太阳能", "风能", "光伏", "核", "化石", "煤炭",
                                "石油", "天然气", "可再生", "电网", "储能"],
                   "label": "能源转型"},
        "ecology": {"keywords": ["生态", "生物", "森林", "海洋", "冰川", "物种", "污染",
                                 "环保", "自然", "保护"],
                    "label": "生态"},
    },
    "gaming": {
        "pc": {"keywords": ["PC", "Steam", "Epic", "Windows", "显卡", "主机配置", "mod"],
               "label": "PC游戏"},
        "console": {"keywords": ["PS5", "PS4", "Xbox", "Switch", "任天堂", "索尼", "主机"],
                    "label": "主机"},
        "mobile": {"keywords": ["手游", "手机", "iOS", "Android", "iPhone", "原神", "王者"],
                   "label": "手游"},
        "esports": {"keywords": ["电竞", "比赛", "LOL", "DOTA2", "CS2", "Valorant",
                                 "赛事", "战队", "选手", "冠军"],
                    "label": "电竞"},
        "industry": {"keywords": ["厂商", "收购", "销量", "发布", "预告", "新作", "DLC",
                                  "更新", "测试", "封测"],
                     "label": "行业"},
    },
    "sports": {
        "basketball": {"keywords": ["篮球", "NBA", "CBA", "湖人", "勇士", "篮网", "凯尔特人"],
                       "label": "篮球"},
        "football": {"keywords": ["足球", "英超", "西甲", "欧冠", "世界杯", "中超", "曼联",
                                  "皇马", "巴萨", "soccer"],
                     "label": "足球"},
        "tennis": {"keywords": ["网球", "温网", "法网", "美网", "澳网", "ATP", "WTA"],
                   "label": "网球"},
        "combat": {"keywords": ["UFC", "拳击", "MMA", "格斗", "摔角", "WWE"],
                   "label": "格斗"},
    },
    "movies": {
        "new_release": {"keywords": ["上映", "定档", "预告", "首映", "发布", "确认", "档期"],
                        "label": "新片"},
        "box_office": {"keywords": ["票房", "纪录", "破亿", "冠军", "排名", "收入"],
                       "label": "票房"},
        "review": {"keywords": ["评价", "评分", "口碑", "烂番茄", "豆瓣", "IMDb", "影评"],
                   "label": "评价"},
        "streaming": {"keywords": ["Netflix", "Disney", "流媒体", "HBO", "上线", "平台"],
                      "label": "流媒体"},
    },
    "music": {
        "charts": {"keywords": ["Billboard", "榜单", "排名", "榜首", "空降", "周榜"],
                   "label": "榜单"},
        "pop": {"keywords": ["流行", "pop", "歌手", "专辑", "单曲", "Taylor", "Ed Sheeran"],
                "label": "流行"},
        "electronic": {"keywords": ["电子", "DJ", "EDM", "house", "techno", "remix"],
                       "label": "电子"},
        "indie": {"keywords": ["独立", "indie", "alternative", "摇滚", "乐队", "Pitchfork"],
                  "label": "独立/摇滚"},
    },
}


CAT_LABELS = {
    "tech":  "科技", "climate": "气候", "gaming": "游戏",
    "sports": "体育", "movies": "影视", "music": "音乐",
}


def get_topic_hierarchy() -> Dict[str, Dict[str, Any]]:
    """导出主题层级结构供前端使用"""
    result: Dict[str, Dict[str, Any]] = {}
    for cat_key, sub_dict in SUB_TOPICS.items():
        result[cat_key] = {
            "label": CAT_LABELS.get(cat_key, cat_key),
            "sub_topics": [
                {"key": sk, "label": sv["label"]}
                for sk, sv in sub_dict.items()
            ],
        }
    return result


def tag_sub_topic(article: "Article") -> str:
    """根据文章标题和摘要匹配子主题标签，返回匹配度最高的标签名"""
    from sources.base import Article

    text: str = f"{article.title} {article.summary} {article.meta}".lower()
    category_topics: Dict[str, Dict[str, Any]] = SUB_TOPICS.get(article.category, {})
    best_score: int = 0
    best_tag: str = ""

    for topic_key, topic_info in category_topics.items():
        score: int = 0
        for kw in topic_info["keywords"]:
            if kw.lower() in text:
                score += len(kw)
        if score > best_score:
            best_score = score
            best_tag = topic_info["label"]

    return best_tag


# ═══════════════════════════════════════════════════════════
#  质量评分
# ═══════════════════════════════════════════════════════════

SOURCE_REPUTATION = {
    "GitHub Trending": 8, "Hacker News": 9, "V2EX": 6,
    "Open-Meteo 天气": 10, "Carbon Brief": 9, "天气资讯": 7,
    "Steam 新闻": 7, "Reddit r/gaming": 5, "游民星空": 6,
    "ESPN": 8, "虎扑": 6, "Reddit r/sports": 5,
    "豆瓣电影": 7, "Reddit r/movies": 5, "烂番茄": 8,
    "Reddit r/music": 5, "Pitchfork": 8, "Billboard": 8,
}


def score_article(article: "Article") -> int:
    """对文章进行 0-10 质量评分，综合多个维度"""
    from sources.base import Article

    score: int = 5

    rep: int = SOURCE_REPUTATION.get(article.source, 5)
    if rep >= 9:
        score += 3
    elif rep >= 7:
        score += 2
    elif rep >= 5:
        score += 1

    text_len: int = len(article.summary or article.title)
    if text_len > 150:
        score += 3
    elif text_len > 80:
        score += 2
    elif text_len > 20:
        score += 1

    meta: str = article.meta.lower()
    nums = re.findall(r'(\d+)', meta)
    if nums:
        max_num: int = max(int(n) for n in nums)
        if max_num >= 1000:
            score += 3
        elif max_num >= 100:
            score += 2
        elif max_num >= 10:
            score += 1

    if article.url and article.url.startswith("http"):
        score += 1

    if article.sub_topic:
        score += 1

    return min(score, 10)


# ═══════════════════════════════════════════════════════════
#  去重
# ═══════════════════════════════════════════════════════════

def _normalize(text: str) -> str:
    """归一化文本：去标点、空格、转小写"""
    text = re.sub(r'[^\w\u4e00-\u9fff]', '', text)
    return text.lower()


def _char_bigrams(text: str) -> Set[str]:
    """生成字符二元组集合用于 Jaccard 相似度"""
    return set(text[i:i+2] for i in range(len(text) - 1))


def _similarity(a: str, b: str) -> float:
    """Jaccard 相似度 (0-1)"""
    sa: Set[str] = _char_bigrams(_normalize(a))
    sb: Set[str] = _char_bigrams(_normalize(b))
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def deduplicate(articles: List["Article"], threshold: float = 0.65) -> List["Article"]:
    """
    基于标题相似度去重。
    相似度 > threshold 的两篇文章视为重复，保留质量评分高的那篇。
    """
    from sources.base import Article

    if not articles:
        return []

    deduped: List[Article] = []
    for article in articles:
        dup_found: bool = False
        for existing in deduped:
            if (article.category == existing.category
                    and _similarity(article.title, existing.title) > threshold):
                dup_found = True
                if article.quality_score > existing.quality_score:
                    deduped.remove(existing)
                    deduped.append(article)
                break
        if not dup_found:
            deduped.append(article)

    return deduped


# ═══════════════════════════════════════════════════════════
#  一键处理
# ═══════════════════════════════════════════════════════════

def filter_by_topic_selection(articles_by_cat: Dict[str, List["Article"]], 
                              topic_selection: Dict[str, Any]) -> Dict[str, List["Article"]]:
    """
    根据主题选择配置过滤文章。
    - 大主题未选中：移除整个分类
    - 大主题选中但指定了子主题：只保留匹配子主题的文章
    - 大主题选中但 sub_topics 为空：保留该分类全部文章
    """
    from sources.base import Article

    if not topic_selection:
        return articles_by_cat

    result: Dict[str, List[Article]] = {}
    for cat_key, cat_articles in articles_by_cat.items():
        sel: Dict[str, Any] = topic_selection.get(cat_key, {})
        if not sel.get("selected", True):
            continue
        sub_filter: List[str] = sel.get("sub_topics", [])
        if not sub_filter:
            result[cat_key] = cat_articles
            continue
        selected_labels: Set[str] = set()
        cat_subs: Dict[str, Any] = SUB_TOPICS.get(cat_key, {})
        for sk in sub_filter:
            if sk in cat_subs:
                selected_labels.add(cat_subs[sk]["label"])
        filtered: List[Article] = [a for a in cat_articles
                    if a.article_type == "weather" or a.sub_topic in selected_labels]
        if filtered:
            result[cat_key] = filtered

    return result


def process_articles(articles_by_cat: Dict[str, List["Article"]], 
                     progress_callback: Optional[Callable[[str, str], None]] = None,
                     topic_selection: Optional[Dict[str, Any]] = None) -> Dict[str, List["Article"]]:
    """
    对采集到的文章执行完整处理流程：
    1. 子主题标签匹配
    2. 质量评分
    3. 标题相似度去重
    4. 按主题选择过滤
    """
    from typing import Callable
    from sources.base import Article

    if progress_callback:
        progress_callback("processing", "正在标注子主题...")

    for cat_arts in articles_by_cat.values():
        for a in cat_arts:
            if a.article_type == "weather":
                continue
            a.sub_topic = tag_sub_topic(a)
            a.quality_score = score_article(a)

    if progress_callback:
        progress_callback("processing", "正在去重...")

    total_before: int = sum(len(v) for v in articles_by_cat.values())
    for cat in list(articles_by_cat.keys()):
        articles_by_cat[cat] = deduplicate(articles_by_cat[cat])
    total_after: int = sum(len(v) for v in articles_by_cat.values())

    if progress_callback:
        removed = total_before - total_after
        if removed > 0:
            progress_callback("processing",
                              f"去重完成：{total_before} → {total_after} 条（移除 {removed} 条重复）")

    if topic_selection:
        articles_by_cat = filter_by_topic_selection(articles_by_cat, topic_selection)

    return articles_by_cat
