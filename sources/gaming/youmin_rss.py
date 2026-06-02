"""
游民星空采集器
RSS + HTML 页面解析双通道
"""

from sources.base import RSSBaseSource, Article, register_source


@register_source("gaming.youmin_rss")
class YouminRSSSource(RSSBaseSource):
    name = "游民星空"
    category = "gaming"
    FEEDS = [
        "https://www.gamersky.com/rss/news.xml",
        "http://www.gamersky.com/rss/news",
    ]
    HTML_FALLBACK = "https://www.gamersky.com/news/"

    def _try_html(self) -> list[Article]:
        soup = self._get_soup(self.HTML_FALLBACK)
        if soup is None:
            return []

        articles = []
        links = soup.select("a[href*='/news/']")
        seen = set()
        for link in links:
            title = link.get_text(strip=True)
            href = link.get("href", "")
            if not title or not href or len(title) < 8:
                continue
            if title in seen:
                continue
            seen.add(title)
            if not href.startswith("http"):
                href = f"https://www.gamersky.com{href}" if href.startswith("/") else href
            articles.append(self._make_article(title=title, url=href, meta="游民星空"))
            if len(articles) >= self.max_articles:
                break

        return articles

    def fetch(self) -> list[Article]:
        articles = super().fetch()
        if not articles:
            articles = self._try_html()
        self._log_fetch(len(articles))
        return articles
