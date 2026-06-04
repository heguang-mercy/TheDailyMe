"""
TheDailyMe — 朴素翻译引擎

零外部依赖，直接用 requests 调 Google 免费翻译接口。
回退策略：Google Free API → 百度免费 API → 返回原文
"""

import logging
import re
import time
from typing import Optional

import requests

logger = logging.getLogger("thedailyme.translate")


# ═══════════════════════════════════════════════════════════
#  Google Translate (免费，无需 API key)
# ═══════════════════════════════════════════════════════════

def _google_translate(text: str, target: str = "zh",
                      source: str = "en") -> Optional[str]:
    """
    调用 Google Translate 免费接口。

    接口地址：translate.googleapis.com
    这是 Chrome 浏览器翻译功能同款接口，无官方 SLA 但有速率限制。
    """
    url = "https://translate.googleapis.com/translate_a/single"
    params = {
        "client": "gtx",
        "sl": source,
        "tl": target,
        "dt": "t",
        "q": text,
    }
    try:
        resp = requests.get(url, params=params, timeout=8)
        resp.raise_for_status()
        data = resp.json()
        # 返回格式：[[["翻译", "原文", ...]], ...]
        sentences = data[0]
        result = "".join(s[0] for s in sentences if isinstance(s, list))
        return result if result else None
    except Exception as e:
        logger.debug("Google Translate 请求失败: %s", e)
        return None


# ═══════════════════════════════════════════════════════════
#  百度免费翻译（基于 signature 简化版）
# ═══════════════════════════════════════════════════════════

def _baidu_translate(text: str, target: str = "zh",
                     source: str = "en") -> Optional[str]:
    """
    百度翻译免费接口（不需要 API key 的版本）。

    有速率限制，但比 Google Translate 在中国大陆更稳定。
    """
    url = "https://fanyi.baidu.com/transapi"
    data = {
        "query": text,
        "from": source,
        "to": target,
    }
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36"
        ),
        "Referer": "https://fanyi.baidu.com/",
    }
    try:
        resp = requests.post(url, data=data, headers=headers, timeout=8)
        resp.raise_for_status()
        result = resp.json()
        data_list = result.get("data", [])
        if data_list:
            return data_list[0].get("dst", "")
        return None
    except Exception as e:
        logger.debug("百度翻译请求失败: %s", e)
        return None


# ═══════════════════════════════════════════════════════════
#  统一入口
# ═══════════════════════════════════════════════════════════

def translate(text: str, target: str = "zh") -> str:
    """
    翻译一段文字，自动回退。

    策略：
      1. Google Translate（快，全球可用）
      2. 百度翻译（中国大陆稳定）
      3. 返回原文

    参数：
      text: 待翻译文本
      target: 目标语言代码，默认 zh

    返回：翻译后的文本，失败则返回原文
    """
    if not text or not text.strip():
        return text

    # 跳过纯英文标点/数字/无意义文本
    cleaned = text.strip()
    if len(cleaned) < 3:
        return text

    # Google 优先
    result = _google_translate(text, target)
    if result:
        return result

    # 百度回退
    result = _baidu_translate(text, target)
    if result:
        return result

    # 都失败，返回原文
    logger.warning("翻译失败，返回原文: %s...", text[:40])
    return text


def is_chinese(text: str, threshold: float = 0.35) -> bool:
    """
    判断一段文字是否已经是中文。

    统计 CJK 统一表意文字（\u4e00-\u9fff）占比，
    超过 threshold 判定为中文，跳过翻译。
    """
    if not text:
        return True
    cjk = sum(1 for ch in text if '\u4e00' <= ch <= '\u9fff')
    return (cjk / len(text)) > threshold


def batch_translate(articles: list, target: str = "zh",
                    fields: tuple = ("title", "summary"),
                    max_batch: int = 30) -> int:
    """
    批量翻译文章列表，支持多个字段。

    articles: 支持任何有 title/summary 属性的对象
    fields: 要翻译的字段名
    max_batch: 单次最多翻译篇数（避免 API 限速）

    返回：成功翻译的文章数
    """
    need = []
    for a in articles:
        text = " ".join(getattr(a, f, "") or "" for f in fields)
        if text.strip() and not is_chinese(text):
            need.append(a)

    if not need:
        logger.info("翻译: 0 篇需要翻译")
        return 0

    n = min(len(need), max_batch)
    batch = need[:n]
    logger.info("翻译: %d 篇 → 中文...", len(batch))

    translated = 0
    for a in batch:
        for field in fields:
            original = getattr(a, field, "") or ""
            if not original.strip():
                continue
            # 标题单独判断是否已是中文
            if field == "title" and is_chinese(original):
                continue
            result = translate(original, target)
            if result and result != original:
                setattr(a, field, result)
        translated += 1
        # 礼貌性延迟：避免触发 Google 限速
        if translated % 5 == 0:
            time.sleep(0.3)

    logger.info("翻译: 完成 %d 篇", translated)
    return translated
