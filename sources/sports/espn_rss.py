"""
ESPN 体育新闻 RSS
"""

from sources.base import RSSBaseSource, register_source


@register_source("sports.espn_rss")
class EspnRSSSource(RSSBaseSource):

    name = "ESPN"
    category = "sports"
    FEED_URL = "https://www.espn.com/espn/rss/news"
