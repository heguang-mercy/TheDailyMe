"""
Carbon Brief 气候深度报道 RSS
"""

from sources.base import RSSBaseSource, register_source


@register_source("climate.carbon_brief")
class CarbonBriefSource(RSSBaseSource):
    name = "Carbon Brief"
    category = "climate"
    FEED_URL = "https://www.carbonbrief.org/feed/"

    def _entry_meta(self, entry) -> str:
        return "气候变化 · 深度报道"
