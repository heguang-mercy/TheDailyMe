"""
TheDailyMe — AI 服务模块

提供基于大模型的：
  - 头条智能筛选 + 标题重写
  - 文章 AI 摘要生成
  - 二级详情页内容生成
  - 今日必读总览

依赖 OpenAI 兼容 API，支持配置任意兼容提供商。
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Optional

import requests

from sources.base import Article

logger = logging.getLogger("thedailyme.ai")


@dataclass
class AIHeadlineResult:
    original_title: str
    ai_title: str
    ai_summary: str
    ai_detail: str
    importance_score: int
    importance_reason: str
    source: str
    category: str
    url: str
    original_summary: str


@dataclass
class AIReportResult:
    headlines: list[AIHeadlineResult] = field(default_factory=list)
    daily_briefing: str = ""
    categories_highlight: dict[str, str] = field(default_factory=dict)


class AIService:
    """OpenAI 兼容 API 的统一封装"""

    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1",
                 model: str = "gpt-4o-mini", max_articles: int = 60):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.max_input_articles = max_articles

    def _api_url(self) -> str:
        if self.base_url.endswith("/chat/completions"):
            return self.base_url
        return f"{self.base_url}/chat/completions"

    def _call(self, system_prompt: str, user_prompt: str,
              temperature: float = 0.7, max_tokens: int = 4096) -> Optional[str]:
        """通用 API 调用"""
        url = self._api_url()
        logger.info("AI API 请求: %s (model=%s)", url, self.model)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=120)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            return content
        except requests.RequestException as e:
            logger.warning("AI API 请求失败: %s", e)
            if hasattr(e, 'response') and e.response is not None:
                logger.warning("AI API 响应: %s", e.response.text[:500])
            return None
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            logger.warning("AI API 响应解析失败: %s", e)
            return None

    def select_and_rewrite_headlines(self, articles: list[Article]) -> list[AIHeadlineResult]:
        """让 AI 从所有文章中选出 3-5 条最重要的，并重写标题、生成摘要"""
        if not articles:
            return []

        article_list = []
        for i, a in enumerate(articles[:self.max_input_articles]):
            article_list.append({
                "id": i,
                "title": a.title,
                "source": a.source,
                "category": a.category,
                "summary": (a.summary or "")[:150],
                "meta": a.meta,
            })

        system = (
            "你是一位资深新闻主编，负责为一份个人日报挑选最重要的头条新闻。"
            "你需要从今天的新闻列表中，选出 3-5 条最重要、最有价值的新闻作为头条。"
            "选择标准：新闻价值、时效性、对读者的实用性和知识性、话题热度。"
            "每条选中的新闻，你需要：\n"
            "1. 重写一个更吸引人的中文标题（15-25字），保留关键信息但更有可读性\n"
            "2. 写一段 80-150 字的中文 AI 摘要，让读者快速把握要点\n"
            "3. 写一段 300-500 字的中文深度解读（供二级详情页使用），包含背景、影响分析和看点\n"
            "4. 给出重要性评分 1-10 和简短理由\n\n"
            "只返回 JSON 数组，不要有其他文字。格式：\n"
            '[{"id": 原文id, "ai_title": "重写标题", "ai_summary": "摘要", '
            '"ai_detail": "深度解读内容", "importance_score": 9, '
            '"importance_reason": "理由"}]'
        )

        articles_json = json.dumps(article_list, ensure_ascii=False, indent=2)
        user = f"以下是今天聚合到的新闻列表，请挑选最重要的 3-5 条作为头条：\n\n{articles_json}"

        response = self._call(system, user, temperature=0.7, max_tokens=4096)
        if not response:
            return []

        try:
            response = response.strip()
            if response.startswith("```"):
                lines = response.split("\n")
                response = "\n".join(lines[1:-1])
            ai_picks = json.loads(response)
        except json.JSONDecodeError:
            logger.warning("AI 头条选择结果 JSON 解析失败")
            return []

        results = []
        for pick in ai_picks:
            idx = pick.get("id", -1)
            if 0 <= idx < len(articles):
                a = articles[idx]
                results.append(AIHeadlineResult(
                    original_title=a.title,
                    ai_title=pick.get("ai_title", a.title),
                    ai_summary=pick.get("ai_summary", ""),
                    ai_detail=pick.get("ai_detail", ""),
                    importance_score=pick.get("importance_score", 5),
                    importance_reason=pick.get("importance_reason", ""),
                    source=a.source,
                    category=a.category,
                    url=a.url,
                    original_summary=a.summary or "",
                ))

        results.sort(key=lambda x: x.importance_score, reverse=True)
        return results

    def generate_daily_briefing(self, headlines: list[AIHeadlineResult]) -> str:
        """基于头条生成今日必读简报"""
        if not headlines:
            return ""

        brief = []
        for i, h in enumerate(headlines[:5]):
            brief.append(f"{i+1}. [{h.category}] {h.ai_title}")

        system = (
            '你是日报主编，请根据今日头条列表，写一段 100-200 字的\u201c今日必读\u201d总览。'
            '用流畅的中文总结今天最重要的看点，让读者一眼了解今日大事。'
            '语气亲切但不失专业。不要使用任何 emoji 表情符号。'
        )
        user = f"今日头条列表：\n\n" + "\n".join(brief)

        return self._call(system, user, temperature=0.7, max_tokens=500) or ""

    # ═══════════════════════════════════════════════════════════
    #  批量翻译
    # ═══════════════════════════════════════════════════════════

    def translate_batch(self, articles: list[Article],
                        target_lang: str = "zh") -> int:
        """
        批量翻译英文文章标题和摘要为中文，原地修改 Article 对象。

        跳过已为中文的文章（CJK 字符占比 > 50%）。

        返回成功翻译的文章数量。
        """
        # 筛出需要翻译的英文文章
        need_translate = []
        for a in articles:
            text = a.title + " " + (a.summary or "")
            if not text.strip():
                continue
            cjk = sum(1 for ch in text if '\u4e00' <= ch <= '\u9fff' or
                      '\u3400' <= ch <= '\u4dbf')
            ratio = cjk / len(text) if text else 0
            if ratio < 0.3:  # 中文占比 < 30%，视为英文
                need_translate.append(a)

        if not need_translate:
            logger.info("翻译: 0 篇需要翻译（全部已是中文）")
            return 0

        logger.info("翻译: %d 篇英文文章 → 中文...", len(need_translate))

        # 每批最多 40 篇
        batch_size = 40
        translated = 0

        for batch_start in range(0, len(need_translate), batch_size):
            batch = need_translate[batch_start:batch_start + batch_size]

            # 构建输入
            items = {}
            for a in batch:
                key = str(id(a))
                items[key] = {
                    "title": a.title,
                    "summary": (a.summary or "")[:150],
                }

            system = (
                "你是一个专业的中英翻译引擎。请将以下英文新闻标题和摘要翻译成"
                "流畅自然的中文。注意：\n"
                "1. 标题翻译保留新闻感和吸引力，15-30 字最佳\n"
                "2. 摘要翻译保持信息完整，简洁明了\n"
                "3. 专业名词保留英文原文（如 GitHub、OpenAI、NBA）\n"
                "4. 只返回 JSON 对象，key 与输入一致，不要有任何其他文字"
            )

            user = json.dumps(items, ensure_ascii=False, indent=2)

            response = self._call(system, user, temperature=0.3, max_tokens=2048)
            if not response:
                logger.warning("翻译 API 返回空，跳过剩余 %d 篇", len(batch))
                break

            try:
                response = response.strip()
                if response.startswith("```"):
                    lines = response.split("\n")
                    response = "\n".join(lines[1:-1])
                result = json.loads(response)
            except json.JSONDecodeError:
                logger.warning("翻译结果 JSON 解析失败")
                continue

            for a in batch:
                key = str(id(a))
                if key in result and isinstance(result[key], dict):
                    t = result[key]
                    if isinstance(t.get("title"), str) and t["title"].strip():
                        a.title = t["title"].strip()
                        a._translated = True
                    if isinstance(t.get("summary"), str) and t["summary"].strip():
                        a.summary = t["summary"].strip()
                    translated += 1

        logger.info("翻译: 完成 %d 篇", translated)
        return translated

    def generate_detail_content(self, article_title: str, article_summary: str,
                                 article_source: str, article_category: str) -> str:
        """为单篇文章生成二级详情页的深度内容"""
        system = (
            "你是一个新闻深度解读助手。请根据给定的文章信息，生成一篇 300-500 字的深度解读。"
            "内容包括：\n"
            "1. 事件背景与来龙去脉\n"
            "2. 关键细节与数据分析\n"
            "3. 对相关领域的影响\n"
            "4. 值得关注的后续发展\n"
            "语言流畅专业，使用中文。"
        )
        user = (
            f"文章标题：{article_title}\n"
            f"来源：{article_source}\n"
            f"分类：{article_category}\n"
            f"原文摘要：{article_summary}\n\n"
            f"请生成深度解读内容。"
        )

        return self._call(system, user, temperature=0.7, max_tokens=1000) or ""
