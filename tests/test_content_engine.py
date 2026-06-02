"""
TheDailyMe — 内容引擎单元测试
"""

import pytest
from datetime import datetime
from sources.base import Article, BaseSource
from content_engine import (
    score_article,
    deduplicate,
    tag_sub_topic,
    _similarity,
    _normalize,
)


class TestScoreArticle:
    """测试文章质量评分函数"""

    def test_score_article_high_reputation(self):
        """高信誉来源应获得高分"""
        article = Article(
            title="AI 技术突破",
            source="Hacker News",
            category="tech",
            url="https://example.com",
            summary="这是一篇关于 AI 技术突破的详细报道，内容非常丰富。" * 5,
            meta="1000 评论",
            sub_topic="AI",
        )
        score = score_article(article)
        assert score >= 9

    def test_score_article_low_reputation(self):
        """低信誉来源应获得较低分"""
        article = Article(
            title="普通新闻",
            source="Reddit r/gaming",
            category="gaming",
            url="https://example.com",
            summary="简短摘要",
            meta="10 评论",
        )
        score = score_article(article)
        assert score <= 6

    def test_score_article_long_content(self):
        """长内容应获得更高分"""
        article = Article(
            title="长文章标题",
            source="Hacker News",
            category="tech",
            url="https://example.com",
            summary="这是一篇非常长的文章内容，包含了很多详细信息。" * 10,
            meta="",
        )
        score = score_article(article)
        assert score >= 8

    def test_score_article_short_content(self):
        """短内容应获得较低分"""
        article = Article(
            title="短",
            source="Hacker News",
            category="tech",
            url="",
            summary="短",
            meta="",
        )
        score = score_article(article)
        assert score <= 5

    def test_score_article_with_url(self):
        """有 URL 的文章应加分"""
        article_with_url = Article(
            title="标题",
            source="Hacker News",
            category="tech",
            url="https://example.com",
            summary="内容",
            meta="",
        )
        article_without_url = Article(
            title="标题",
            source="Hacker News",
            category="tech",
            url="",
            summary="内容",
            meta="",
        )
        score_with = score_article(article_with_url)
        score_without = score_article(article_without_url)
        assert score_with > score_without

    def test_score_article_with_sub_topic(self):
        """有子主题标签的文章应加分"""
        article_with_topic = Article(
            title="AI 新闻",
            source="Hacker News",
            category="tech",
            url="https://example.com",
            summary="内容",
            meta="",
            sub_topic="AI",
        )
        article_without_topic = Article(
            title="AI 新闻",
            source="Hacker News",
            category="tech",
            url="https://example.com",
            summary="内容",
            meta="",
            sub_topic="",
        )
        score_with = score_article(article_with_topic)
        score_without = score_article(article_without_topic)
        assert score_with > score_without


class TestDeduplicate:
    """测试去重函数"""

    def test_deduplicate_removes_duplicates(self):
        """应移除相似标题的重复文章"""
        article1 = Article(
            title="AI 技术取得重大突破",
            source="Source A",
            category="tech",
            url="https://example.com/a",
            quality_score=8,
        )
        article2 = Article(
            title="AI 技术取得重大突破",
            source="Source B",
            category="tech",
            url="https://example.com/b",
            quality_score=6,
        )
        articles = [article1, article2]
        result = deduplicate(articles)
        assert len(result) == 1
        assert result[0] == article1

    def test_deduplicate_preserves_high_score(self):
        """去重时应保留质量评分更高的文章"""
        article_low = Article(
            title="相同标题",
            source="Source A",
            category="tech",
            url="https://example.com/a",
            quality_score=3,
        )
        article_high = Article(
            title="相同标题",
            source="Source B",
            category="tech",
            url="https://example.com/b",
            quality_score=9,
        )
        articles = [article_low, article_high]
        result = deduplicate(articles)
        assert len(result) == 1
        assert result[0] == article_high

    def test_deduplicate_different_categories(self):
        """不同分类的文章不应被视为重复"""
        article1 = Article(
            title="相同标题",
            source="Source A",
            category="tech",
            url="https://example.com/a",
            quality_score=8,
        )
        article2 = Article(
            title="相同标题",
            source="Source B",
            category="sports",
            url="https://example.com/b",
            quality_score=6,
        )
        articles = [article1, article2]
        result = deduplicate(articles)
        assert len(result) == 2

    def test_deduplicate_empty_list(self):
        """空列表应返回空列表"""
        result = deduplicate([])
        assert result == []

    def test_deduplicate_no_duplicates(self):
        """没有重复的列表应保持不变"""
        article1 = Article(
            title="标题1",
            source="Source A",
            category="tech",
            url="https://example.com/a",
            quality_score=8,
        )
        article2 = Article(
            title="完全不同的标题",
            source="Source B",
            category="tech",
            url="https://example.com/b",
            quality_score=6,
        )
        articles = [article1, article2]
        result = deduplicate(articles)
        assert len(result) == 2


class TestSimilarity:
    """测试相似度计算函数"""

    def test_similarity_identical(self):
        """相同文本相似度应为 1.0"""
        assert _similarity("相同文本", "相同文本") == 1.0

    def test_similarity_different(self):
        """不同文本相似度应较低"""
        sim = _similarity("人工智能", "足球比赛")
        assert sim < 0.3

    def test_similarity_partial(self):
        """部分相似文本应有中等相似度"""
        sim = _similarity("AI 技术突破", "AI 技术新进展")
        assert 0.4 < sim < 0.8


class TestTagSubTopic:
    """测试子主题标签匹配函数"""

    def test_tag_sub_topic_ai(self):
        """应正确识别 AI 主题"""
        article = Article(
            title="ChatGPT 发布新版本",
            source="Hacker News",
            category="tech",
            url="https://example.com",
            summary="GPT-5 大模型发布",
            meta="",
        )
        tag = tag_sub_topic(article)
        assert tag == "AI"

    def test_tag_sub_topic_security(self):
        """应正确识别安全主题"""
        article = Article(
            title="重大安全漏洞被发现",
            source="Hacker News",
            category="tech",
            url="https://example.com",
            summary="CVE-2024-0001 漏洞影响众多系统",
            meta="",
        )
        tag = tag_sub_topic(article)
        assert tag == "安全"

    def test_tag_sub_topic_no_match(self):
        """无匹配时应返回空字符串"""
        article = Article(
            title="普通文章",
            source="Source",
            category="tech",
            url="https://example.com",
            summary="没有关键词的内容",
            meta="",
        )
        tag = tag_sub_topic(article)
        assert tag == ""


class TestNormalize:
    """测试文本归一化函数"""

    def test_normalize_removes_punctuation(self):
        """应移除标点符号"""
        assert _normalize("Hello, World!") == "helloworld"

    def test_normalize_lowercase(self):
        """应转换为小写"""
        assert _normalize("AI Technology") == "aitechnology"

    def test_normalize_chinese(self):
        """应正确处理中文字符"""
        assert _normalize("人工智能！") == "人工智能"