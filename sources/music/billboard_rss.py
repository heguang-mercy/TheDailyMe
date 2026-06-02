"""
Billboard 音乐榜单/新闻 RSS
"""

from sources.base import RSSBaseSource, register_source


@register_source("music.billboard_rss")
class BillboardSource(RSSBaseSource):
    name = "Billboard"
    category = "music"
    FEEDS = [
        "https://www.billboard.com/feed/",
        "https://www.billboard.com/articles/rss.xml",
    ]
