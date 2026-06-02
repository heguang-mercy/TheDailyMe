"""
Hacker News 采集器
使用官方 Firebase API：https://github.com/HackerNews/API
"""

from sources.base import BaseSource, Article, register_source


@register_source("tech.hackernews")
class HackerNewsSource(BaseSource):
    name = "Hacker News"
    category = "tech"

    TOP_STORIES = "https://hacker-news.firebaseio.com/v0/topstories.json"
    ITEM = "https://hacker-news.firebaseio.com/v0/item/{}.json"

    def fetch(self) -> list[Article]:
        # 获取 top story IDs
        ids = self._get_json(self.TOP_STORIES)
        if ids is None:
            return []

        # 取前 30 个 ID，逐个获取详情
        articles = []
        for item_id in ids[:30]:
            item = self._get_json(self.ITEM.format(item_id))
            if item is None:
                continue

            title = item.get("title", "")
            if not title:
                continue

            url = item.get("url", "")
            if not url:
                url = f"https://news.ycombinator.com/item?id={item_id}"

            score = item.get("score", 0)
            descendants = item.get("descendants", 0)  # 评论数
            meta = f"{score} points · {descendants} comments"

            articles.append(self._make_article(
                title=title,
                url=url,
                meta=meta,
            ))

            if len(articles) >= self.max_articles:
                break

        self._log_fetch(len(articles))
        return articles
