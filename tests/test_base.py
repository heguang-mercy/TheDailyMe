"""
TheDailyMe — 采集器基类单元测试
"""

import pytest
from sources.base import Article, BaseSource, register_source


class TestArticle:
    """测试 Article 数据类"""

    def test_article_creation(self):
        """应能正确创建 Article 对象"""
        article = Article(
            title="测试标题",
            source="测试来源",
            category="tech",
            url="https://example.com",
            summary="测试摘要",
            meta="测试元信息",
            article_type="",
        )
        assert article.title == "测试标题"
        assert article.source == "测试来源"
        assert article.category == "tech"
        assert article.url == "https://example.com"
        assert article.summary == "测试摘要"
        assert article.meta == "测试元信息"

    def test_article_default_values(self):
        """应使用默认值"""
        article = Article(
            title="标题",
            source="来源",
            category="tech",
            url="",
        )
        assert article.summary == ""
        assert article.meta == ""
        assert article.article_type == ""
        assert article.sub_topic == ""
        assert article.quality_score == 0

    def test_article_to_dict(self):
        """应正确转换为字典"""
        article = Article(
            title="标题",
            source="来源",
            category="tech",
            url="https://example.com",
            summary="摘要",
            meta="元信息",
        )
        result = article.to_dict()
        assert result["title"] == "标题"
        assert result["source"] == "来源"
        assert result["category"] == "tech"
        assert result["url"] == "https://example.com"
        assert "timestamp" in result


class TestBaseSource:
    """测试 BaseSource 基类"""

    def test_make_article(self):
        """_make_article 应正确创建 Article 对象"""
        class TestSource(BaseSource):
            name = "TestSource"
            category = "tech"

        source = TestSource()
        article = source._make_article(
            title="测试文章",
            url="https://example.com",
            summary="测试摘要",
            meta="100 评论",
            article_type="",
        )
        
        assert article.title == "测试文章"
        assert article.source == "TestSource"
        assert article.category == "tech"
        assert article.url == "https://example.com"
        assert article.summary == "测试摘要"
        assert article.meta == "100 评论"

    def test_make_article_defaults(self):
        """_make_article 应使用默认值"""
        class TestSource(BaseSource):
            name = "TestSource"
            category = "sports"

        source = TestSource()
        article = source._make_article(title="标题")
        
        assert article.title == "标题"
        assert article.source == "TestSource"
        assert article.category == "sports"
        assert article.url == ""
        assert article.summary == ""
        assert article.meta == ""

    def test_register_source_decorator(self):
        """register_source 装饰器应正确注册采集器"""
        @register_source("tech.test_source")
        class TestSource(BaseSource):
            name = "TestSource"
            category = "tech"

        from sources.base import get_registry
        registry = get_registry()
        entries = [e for e in registry if e["class"] == TestSource]
        assert len(entries) == 1
        assert entries[0]["category"] == "tech"
        assert entries[0]["config_key"] == "test_source"

    def test_register_source_with_city(self):
        """register_source 装饰器应正确处理 needs_city 参数"""
        @register_source("climate.weather", needs_city=True)
        class WeatherSource(BaseSource):
            name = "WeatherSource"
            category = "climate"

        from sources.base import get_registry
        registry = get_registry()
        entries = [e for e in registry if e["class"] == WeatherSource]
        assert len(entries) == 1
        assert entries[0]["needs_city"] is True