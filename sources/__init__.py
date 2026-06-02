"""
TheDailyMe — 数据采集器包
导入时自动注册所有采集器到 SourceRegistry
"""

from sources.tech.github_trending import GitHubTrendingSource
from sources.tech.hackernews import HackerNewsSource
from sources.tech.v2ex import V2exSource
from sources.climate.open_meteo import OpenMeteoSource
from sources.climate.weather_rss import WeatherRSSSource
from sources.climate.carbon_brief import CarbonBriefSource
from sources.gaming.steam_rss import SteamRSSSource
from sources.gaming.reddit_gaming import RedditGamingSource
from sources.gaming.youmin_rss import YouminRSSSource
from sources.sports.espn_rss import EspnRSSSource
from sources.sports.hupu import HupuSource
from sources.sports.reddit_sports import RedditSportsSource
from sources.movies.douban_rss import DoubanRSSSource
from sources.movies.reddit_movies import RedditMoviesSource
from sources.movies.rottentomatoes_rss import RottenTomatoesSource
from sources.music.reddit_music import RedditMusicSource
from sources.music.pitchfork_rss import PitchforkSource
from sources.music.billboard_rss import BillboardSource

__all__ = [
    "GitHubTrendingSource", "HackerNewsSource", "V2exSource",
    "OpenMeteoSource", "WeatherRSSSource", "CarbonBriefSource",
    "SteamRSSSource", "RedditGamingSource", "YouminRSSSource",
    "EspnRSSSource", "HupuSource", "RedditSportsSource",
    "DoubanRSSSource", "RedditMoviesSource", "RottenTomatoesSource",
    "RedditMusicSource", "PitchforkSource", "BillboardSource",
]
