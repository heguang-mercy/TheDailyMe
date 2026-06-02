"""
虎扑热帖采集器
解析 https://bbs.hupu.com/all-gambia 步行街热帖
"""

from sources.base import BaseSource, Article, register_source


@register_source("sports.hupu")
class HupuSource(BaseSource):
    name = "虎扑"
    category = "sports"

    URL = "https://bbs.hupu.com/all-gambia"

    def fetch(self) -> list[Article]:
        soup = self._get_soup(self.URL)
        if soup is None:
            return []

        articles = []
        # 虎扑帖子列表结构：a.truetit 或 .titlelink
        links = soup.select("a.truetit, a[href*='/thread/']")
        seen = set()

        for link in links:
            title = link.get_text(strip=True)
            href = link.get("href", "")
            if not title or not href or len(title) < 6:
                continue
            if title in seen:
                continue
            seen.add(title)

            if not href.startswith("http"):
                href = f"https://bbs.hupu.com{href}" if href.startswith("/") else href

            # 尝试获取回复数
            replies = ""
            parent = link.find_parent("li") or link.find_parent("tr")
            if parent:
                reply_el = parent.select_one(".ansnum, .replynum, span.num")
                if reply_el:
                    replies = reply_el.get_text(strip=True)

            articles.append(self._make_article(
                title=title, url=href, meta=f"回复 {replies}" if replies else "虎扑步行街",
            ))
            if len(articles) >= self.max_articles:
                break

        self._log_fetch(len(articles))
        return articles
