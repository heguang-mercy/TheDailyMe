"""
GitHub Trending 采集器
解析 https://github.com/trending?since=daily 页面
"""

from sources.base import BaseSource, Article, register_source


@register_source("tech.github_trending")
class GitHubTrendingSource(BaseSource):
    name = "GitHub Trending"
    category = "tech"

    URL = "https://github.com/trending?since=daily"

    def fetch(self) -> list[Article]:
        soup = self._get_soup(self.URL)
        if soup is None:
            return []

        articles = []
        # Trending 仓库在 article.Box-row 中
        repos = soup.select("article.Box-row")
        for repo in repos[:self.max_articles]:
            # 仓库名
            h2 = repo.select_one("h2")
            if not h2:
                continue
            name_parts = h2.get_text(strip=True).replace("\n", "").strip()
            # 清理多余空格
            while "  " in name_parts:
                name_parts = name_parts.replace("  ", " ")
            name_parts = name_parts.replace(" ", "").replace("/", " / ")

            # 描述
            desc_el = repo.select_one("p")
            summary = desc_el.get_text(strip=True) if desc_el else ""

            # 语言 + stars
            lang_el = repo.select_one("[itemprop='programmingLanguage']")
            lang = lang_el.get_text(strip=True) if lang_el else ""

            stars_el = repo.select_one(".d-inline-block.float-sm-right")
            stars = stars_el.get_text(strip=True) if stars_el else ""

            # 今日 stars
            today_stars = ""
            for span in repo.select(".float-sm-right"):
                text = span.get_text(strip=True)
                if "stars today" in text:
                    today_stars = text
                    break

            meta_parts = [p for p in [lang, stars, today_stars] if p]
            meta = " · ".join(meta_parts)

            # URL
            link_el = h2.select_one("a")
            url = ""
            if link_el:
                href = link_el.get("href", "")
                url = f"https://github.com{href}" if href else ""

            articles.append(self._make_article(
                title=name_parts,
                url=url,
                summary=summary,
                meta=meta,
            ))

        self._log_fetch(len(articles))
        return articles
