"""
V2EX 采集器
解析 https://www.v2ex.com/ 首页热帖
"""

from sources.base import BaseSource, Article, register_source


@register_source("tech.v2ex")
class V2exSource(BaseSource):
    name = "V2EX"
    category = "tech"

    URL = "https://www.v2ex.com/"

    def fetch(self) -> list[Article]:
        soup = self._get_soup(self.URL)
        if soup is None:
            return []

        articles = []
        # V2EX 首页帖子在 span.item_title > a 中
        items = soup.select("span.item_title")
        for item in items[:self.max_articles]:
            link = item.select_one("a")
            if not link:
                continue
            title = link.get_text(strip=True)
            href = link.get("href", "")
            url = f"https://www.v2ex.com{href}" if href else ""

            # 尝试获取回复数（在相邻的 td 里）
            reply_count = ""
            parent_td = item.find_parent("td")
            if parent_td:
                row = parent_td.find_parent("tr")
                if row:
                    replies = row.select_one("a.count_orange, a.count_livid")
                    if replies:
                        reply_count = replies.get_text(strip=True) + " replies"

            articles.append(self._make_article(
                title=title,
                url=url,
                meta=reply_count,
            ))

        self._log_fetch(len(articles))
        return articles
