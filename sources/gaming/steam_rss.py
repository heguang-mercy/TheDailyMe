"""
Steam 新闻 RSS 采集器
"""

from sources.base import RSSBaseSource, register_source


@register_source("gaming.steam_rss")
class SteamRSSSource(RSSBaseSource):
    name = "Steam 新闻"
    category = "gaming"
    FEED_URL = "https://store.steampowered.com/feeds/news.xml"
