"""
Reddit r/sports 采集器
JSON API
"""

from sources.base import BaseSource, Article, register_source


@register_source("sports.reddit_sports")
class RedditSportsSource(BaseSource):
    name = "Reddit r/sports"
    category = "sports"

    URL = "https://www.reddit.com/r/sports/hot.json?limit=25"

    def fetch(self) -> list[Article]:
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        data = self._get_json(self.URL)
        if data is None:
            # 回退到 old.reddit.com
            data = self._get_json("https://old.reddit.com/r/sports/hot.json?limit=25")
        if data is None:
            return []

        articles = []
        posts = data.get("data", {}).get("children", [])
        for child in posts:
            post = child.get("data", {})
            title = post.get("title", "")
            permalink = post.get("permalink", "")
            score = post.get("score", 0)
            num_comments = post.get("num_comments", 0)
            selftext = post.get("selftext", "")

            if not title:
                continue

            url = f"https://www.reddit.com{permalink}" if permalink else ""
            summary = selftext[:200] if selftext else ""
            meta = f"{score} up · {num_comments} comments"

            articles.append(self._make_article(title=title, url=url, summary=summary, meta=meta))
            if len(articles) >= self.max_articles:
                break

        self._log_fetch(len(articles))
        return articles
