"""
TheDailyMe — 采集器基类和统一数据格式

每个采集器继承 BaseSource，实现 fetch() 方法，返回 list[Article]。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import logging
import requests
from bs4 import BeautifulSoup
import feedparser

logger = logging.getLogger("thedailyme")


_source_registry = []


def register_source(config_key: str, needs_city: bool = False):
    def decorator(cls):
        category, key = config_key.split(".", 1)
        _source_registry.append({
            "class": cls,
            "category": category,
            "config_key": key,
            "needs_city": needs_city,
        })
        return cls
    return decorator


def get_registry() -> list:
    return list(_source_registry)


# ── 统一数据格式 ────────────────────────────────────────────

@dataclass
class Article:
    """所有采集器统一返回的新闻条目"""

    title: str
    source: str           # 数据源名称，如 "GitHub Trending"
    category: str         # "tech" / "climate" / "gaming"
    url: str
    summary: str = ""
    meta: str = ""        # 副信息：star 数 / 评论数 / 温度 / 时间
    article_type: str = ""  # 条目类型：""(普通) / "weather"(天气)
    timestamp: datetime = field(default_factory=datetime.now)
    sub_topic: str = ""     # 子主题标签
    quality_score: int = 0  # 质量评分 0-10

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "source": self.source,
            "category": self.category,
            "url": self.url,
            "summary": self.summary,
            "meta": self.meta,
            "article_type": self.article_type,
            "timestamp": self.timestamp.isoformat(),
            "sub_topic": self.sub_topic,
            "quality_score": self.quality_score,
        }


# ── 采集器基类 ──────────────────────────────────────────────

class BaseSource:
    """采集器基类。子类只需实现 fetch() → list[Article]"""

    name: str = "BaseSource"
    category: str = ""

    def __init__(self, timeout: int = 10, max_articles: int = 10):
        self.timeout = timeout
        self.max_articles = max_articles
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        })

    def fetch(self) -> list[Article]:
        """子类重写此方法，返回 Article 列表"""
        raise NotImplementedError

    def _log_fetch(self, count: int):
        logger.info("[%s] 获取 %s 条", self.name, count)

    def _get(self, url: str) -> Optional[requests.Response]:
        """带超时和异常处理的 GET 请求"""
        try:
            resp = self.session.get(url, timeout=self.timeout)
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            logger.warning("[%s] 请求失败: %s", self.name, e)
            return None

    def _get_json(self, url: str) -> Optional[dict]:
        """GET 并解析 JSON"""
        resp = self._get(url)
        if resp is None:
            return None
        try:
            return resp.json()
        except ValueError as e:
            logger.warning("[%s] JSON 解析失败: %s", self.name, e)
            return None

    def _get_soup(self, url: str) -> Optional[BeautifulSoup]:
        """GET 并解析 HTML（用 resp.content 让 BS4 从 <meta> 推测编码）"""
        resp = self._get(url)
        if resp is None:
            return None
        # 优先用 apparent_encoding（chardet 推测），回退到 resp.content 让 BS4 自行判断
        encoding = resp.apparent_encoding or None
        return BeautifulSoup(resp.content, "html.parser", from_encoding=encoding)

    def _make_article(
        self, title: str, url: str = "", summary: str = "", meta: str = "",
        article_type: str = "",
    ) -> Article:
        """快捷构造 Article，自动填入 source 和 category"""
        return Article(
            title=title,
            source=self.name,
            category=self.category,
            url=url,
            summary=summary,
            meta=meta,
            article_type=article_type,
        )


class RSSBaseSource(BaseSource):
    """RSS 采集器基类。子类只需定义 FEEDS 或 FEED_URL"""

    FEED_URL = None
    FEEDS = []

    def _entry_meta(self, entry) -> str:
        return self.name

    def _parse_entry(self, entry) -> Optional[Article]:
        title = entry.get("title", "").strip()
        link = entry.get("link", "")
        summary = entry.get("summary", "")
        if summary:
            summary = BeautifulSoup(summary, "html.parser").get_text(strip=True)[:200]
        if title:
            return self._make_article(
                title=title, url=link, summary=summary,
                meta=self._entry_meta(entry),
            )
        return None

    def _try_feed(self, feed_url: str) -> list:
        try:
            feed = feedparser.parse(feed_url)
        except Exception:
            return []
        if not feed.entries:
            return []
        items = []
        for entry in feed.entries[:self.max_articles]:
            article = self._parse_entry(entry)
            if article:
                items.append(article)
        return items

    def fetch(self) -> list[Article]:
        feed_urls = self.FEEDS if self.FEEDS else ([self.FEED_URL] if self.FEED_URL else [])
        articles = []
        for feed_url in feed_urls:
            articles = self._try_feed(feed_url)
            if articles:
                break
        self._log_fetch(len(articles))
        return articles
