"""
豆瓣电影 RSS 采集器
"""

from sources.base import RSSBaseSource, register_source


@register_source("movies.douban_rss")
class DoubanRSSSource(RSSBaseSource):
    name = "豆瓣电影"
    category = "movies"
    FEEDS = [
        "https://movie.douban.com/feed/",
        "https://www.douban.com/feed/",
    ]
