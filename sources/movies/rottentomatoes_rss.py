"""
烂番茄 (Rotten Tomatoes) 电影新闻 RSS
"""

from sources.base import RSSBaseSource, register_source


@register_source("movies.rottentomatoes_rss")
class RottenTomatoesSource(RSSBaseSource):
    name = "烂番茄"
    category = "movies"
    FEEDS = [
        "https://www.rottentomatoes.com/syndication/rss/movies_opening.xml",
        "https://editorial.rottentomatoes.com/feed/",
    ]
