"""
天气相关新闻 RSS 采集器
聚合多个中文天气/环境新闻 RSS 源
"""

from sources.base import RSSBaseSource, Article, register_source, logger


@register_source("climate.weather_rss")
class WeatherRSSSource(RSSBaseSource):
    name = "天气资讯"
    category = "climate"
    FEEDS = [
        ("http://www.weather.com.cn/rss/news.xml", "中国天气网"),
        ("https://www.cenews.com.cn/rss.xml", "环境新闻"),
    ]

    def fetch(self) -> list[Article]:
        articles = []
        for feed_url, source_label in self.FEEDS:
            items = self._try_feed(feed_url)
            if items:
                for a in items:
                    a.meta = source_label
            articles.extend(items)
            if len(articles) >= self.max_articles:
                break

        if not articles:
            logger.warning("[%s] 所有 RSS 源均不可达，将依赖 Open-Meteo 和 Carbon Brief", self.name)

        self._log_fetch(len(articles))
        return articles
