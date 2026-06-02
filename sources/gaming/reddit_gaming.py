"""
Reddit r/gaming 采集器
Reddit 提供 JSON API：URL 后加 .json 即可获取结构化数据
"""

from sources.base import BaseSource, Article, register_source


@register_source("gaming.reddit_gaming")
class RedditGamingSource(BaseSource):
    name = "Reddit r/gaming"
    category = "gaming"

    URL = "https://old.reddit.com/r/gaming/hot.json?limit=25"

    def fetch(self) -> list[Article]:
        # Reddit 要求浏览器级 User-Agent，用 old.reddit.com 的 JSON API
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "application/json",
        })
        data = self._get_json(self.URL)
        if data is None:
            # 回退到 www 域
            data = self._get_json("https://www.reddit.com/r/gaming/hot.json?limit=25")
        if data is None:
            return []

        articles = []
        posts = data.get("data", {}).get("children", [])
        for child in posts:
            post_data = child.get("data", {})
            title = post_data.get("title", "")
            permalink = post_data.get("permalink", "")
            score = post_data.get("score", 0)
            num_comments = post_data.get("num_comments", 0)
            selftext = post_data.get("selftext", "")

            if not title:
                continue

            url = f"https://www.reddit.com{permalink}" if permalink else ""
            summary = selftext[:200] if selftext else ""
            meta = f"{score} up · {num_comments} comments"

            articles.append(self._make_article(
                title=title,
                url=url,
                summary=summary,
                meta=meta,
            ))

            if len(articles) >= self.max_articles:
                break

        self._log_fetch(len(articles))
        return articles
