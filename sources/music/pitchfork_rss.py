"""
Pitchfork 音乐评论/新闻 RSS
"""

from sources.base import RSSBaseSource, register_source


@register_source("music.pitchfork_rss")
class PitchforkSource(RSSBaseSource):
    name = "Pitchfork"
    category = "music"
    FEEDS = [
        "https://pitchfork.com/rss/news/",
        "https://pitchfork.com/feed/",
    ]
