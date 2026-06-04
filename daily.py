#!/usr/bin/env python3
"""
TheDailyMe — 个人化赛博日报

用法：
    python daily.py              # 使用默认 config.yaml
    python daily.py -c my.yaml   # 指定配置文件

作为库使用：
    from daily import generate_daily, load_config
    config = load_config()
    result = generate_daily(config, progress_callback=my_callback)
"""

import argparse
import json
import logging
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional, Dict, List, Any, Union

import yaml
from jinja2 import Environment, FileSystemLoader

# ── 项目根目录 ──────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent
TEMPLATES = ROOT / "templates"
OUTPUT = ROOT / "output"

sys.path.insert(0, str(ROOT))


# ── 配置加载 ────────────────────────────────────────────────

def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """加载 YAML 配置，返回 dict"""
    path = ROOT / config_path
    if not path.exists():
        raise FileNotFoundError(f"配置文件不存在: {path}")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_config(config: Dict[str, Any], config_path: str = "config.yaml") -> None:
    """保存配置到 YAML 文件"""
    path = ROOT / config_path
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


# ── 采集器工厂函数 ──────────────────────────────────────────

def create_sources(config: Dict[str, Any]) -> List["BaseSource"]:
    """根据 config.yaml 创建所有启用的采集器实例"""
    from sources.base import get_registry, BaseSource

    cfg_sources: Dict[str, Any] = config.get("sources", {})
    timeout: int = config.get("fetch", {}).get("request_timeout", 10)
    max_articles: int = config.get("fetch", {}).get("articles_per_source", 10)
    city: str = config.get("user", {}).get("city", "Beijing")

    sources: List[BaseSource] = []
    for entry in get_registry():
        category_cfg: Dict[str, Any] = cfg_sources.get(entry["category"], {})
        if not category_cfg.get(entry["config_key"], True):
            continue

        cls = entry["class"]
        kwargs: Dict[str, Union[int, str]] = {"timeout": timeout, "max_articles": max_articles}
        if entry.get("needs_city"):
            kwargs["city"] = city
        sources.append(cls(**kwargs))

    return sources


# ── 并发采集 ────────────────────────────────────────────────

def fetch_all(
    sources: List["BaseSource"],
    max_workers: int = 6,
    progress_callback: Optional[Callable[[str, str], None]] = None,
) -> Dict[str, List["Article"]]:
    """并发执行所有采集器，返回 {category: [articles]}"""
    from sources.base import Article, BaseSource

    results: Dict[str, List[Article]] = {}

    if progress_callback:
        progress_callback("fetching", f"正在从 {len(sources)} 个数据源采集...")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(source.fetch): source
            for source in sources
        }
        done = 0
        for future in as_completed(futures):
            source: BaseSource = futures[future]
            done += 1
            try:
                articles: List[Article] = future.result()
            except Exception as e:
                articles = []
                if progress_callback:
                    progress_callback("fetching", f"[{source.name}] 异常: {e}")

            cat = source.category
            if cat not in results:
                results[cat] = []
            results[cat].extend(articles)

            if progress_callback:
                progress_callback("fetching", f"{source.name} 完成 ({done}/{len(sources)})")

    total = sum(len(v) for v in results.values())
    if progress_callback:
        progress_callback("fetching", f"采集完成，共 {total} 条")
    return results


# ── 选头条 ──────────────────────────────────────────────────

def pick_headline(articles_by_cat: Dict[str, List["Article"]], config: Dict[str, Any]) -> Dict[str, Any]:
    """
    从所有文章中选一条头条 + 几条侧边重点。
    策略：按权重随机选一个类别，从该类别挑一条最长的（内容最丰富）。
    """
    from sources.base import Article

    if not articles_by_cat:
        return {"headline": None, "side_headlines": []}

    weights: Dict[str, float] = config.get("categories", {})
    cats: List[str] = list(articles_by_cat.keys())
    chosen_cat: Optional[str] = None

    if cats:
        cat_weights: List[float] = [weights.get(c, 0.33) for c in cats]
        total_w = sum(cat_weights)
        if total_w > 0:
            cat_weights = [w / total_w for w in cat_weights]
        else:
            cat_weights = [1.0 / len(cats)] * len(cats)
        chosen_cat = random.choices(cats, weights=cat_weights, k=1)[0]

    headline: Optional[Article] = None
    if chosen_cat and chosen_cat in articles_by_cat:
        cands: List[Article] = articles_by_cat[chosen_cat]
        if cands:
            headline = max(cands, key=lambda a: len(a.summary or a.title))

    side: List[Article] = []
    for cat, arts in articles_by_cat.items():
        if cat != chosen_cat and arts:
            side.append(arts[0])
    if chosen_cat and chosen_cat in articles_by_cat:
        remaining = [a for a in articles_by_cat[chosen_cat] if a is not headline]
        if remaining:
            side.append(remaining[0])
    side = side[:4]

    return {"headline": headline, "side_headlines": side}


# ── AI 服务初始化 ───────────────────────────────────────────

def _init_ai_service(config: dict):
    """根据配置初始化 AI 服务，若未启用或无 API key 返回 None"""
    ai_cfg = config.get("ai", {})
    if not ai_cfg.get("enabled"):
        return None
    api_key = ai_cfg.get("api_key", "")
    if not api_key:
        return None
    try:
        from ai_service import AIService
        return AIService(
            api_key=api_key,
            base_url=ai_cfg.get("base_url", "https://api.openai.com/v1"),
            model=ai_cfg.get("model", "gpt-4o-mini"),
            max_articles=ai_cfg.get("max_input_articles", 60),
        )
    except ImportError:
        return None


def pick_headline_ai(articles_by_cat: dict, config: dict,
                     progress_callback=None) -> dict:
    """
    AI 驱动的头条选择：让大模型从所有文章中挑 3-5 条最重要内容，
    重写标题、生成摘要和深度解读。
    返回用于模板的数据，也包含传统格式的兼容数据。
    """
    from sources.base import Article

    ai_service = _init_ai_service(config)
    if ai_service is None:
        return pick_headline(articles_by_cat, config)

    all_articles = []
    for cat_arts in articles_by_cat.values():
        all_articles.extend(cat_arts)

    if not all_articles:
        return {"headline": None, "side_headlines": [], "ai_headlines": [],
                "daily_briefing": ""}

    if progress_callback:
        progress_callback("ai", f"AI 正在分析 {len(all_articles)} 条新闻，挑选头条...")

    ai_headlines = ai_service.select_and_rewrite_headlines(all_articles)

    if not ai_headlines:
        if progress_callback:
            progress_callback("ai", "AI 头条分析未返回结果，回退到传统模式")
        return pick_headline(articles_by_cat, config)

    if progress_callback:
        progress_callback("ai", f"AI 已选出 {len(ai_headlines)} 条头条，正在生成今日必读...")

    daily_briefing = ai_service.generate_daily_briefing(ai_headlines)

    main_headline = ai_headlines[0] if ai_headlines else None
    side_headlines = ai_headlines[1:5] if len(ai_headlines) > 1 else []

    headline_article = None
    if main_headline:
        headline_article = Article(
            title=main_headline.ai_title,
            source=main_headline.source,
            category=main_headline.category,
            url=main_headline.url,
            summary=main_headline.ai_summary,
            meta=f"AI 精选 · 重要性: {main_headline.importance_score}/10",
        )

    side_articles = []
    for sh in side_headlines:
        side_articles.append(Article(
            title=sh.ai_title,
            source=sh.source,
            category=sh.category,
            url=sh.url,
            summary=sh.ai_summary,
            meta=f"AI 精选 · 重要性: {sh.importance_score}/10",
        ))

    result = {
        "headline": headline_article,
        "side_headlines": side_articles,
        "ai_headlines": [
            {
                "ai_title": h.ai_title,
                "ai_summary": h.ai_summary,
                "ai_detail": h.ai_detail,
                "importance_score": h.importance_score,
                "importance_reason": h.importance_reason,
                "source": h.source,
                "category": h.category,
                "url": h.url,
                "original_title": h.original_title,
                "original_summary": h.original_summary,
            }
            for h in ai_headlines
        ],
        "daily_briefing": daily_briefing,
    }

    return result


# ── 可用排版主题 ──

LAYOUTS = ["broadsheet", "swiss", "cyberpunk", "magazine"]

# 模板引擎单例，每次渲染复用
_jinja_env = Environment(loader=FileSystemLoader(str(TEMPLATES)))


def render_html(articles_by_cat: dict, headline: dict, config: dict) -> str:
    """Jinja2 渲染，CSS 内联（按 layout 加载对应模板和主题 CSS）"""
    layout = config.get("layout", "broadsheet")
    if layout not in LAYOUTS:
        layout = "broadsheet"

    env = _jinja_env
    template = env.get_template(f"{layout}.html.j2")

    # 从 themes/<layout>.css 加载主题
    css_path = TEMPLATES / "themes" / f"{layout}.css"
    if css_path.exists():
        css = css_path.read_text(encoding="utf-8")
    else:
        css = (TEMPLATES / "themes" / "broadsheet.css").read_text(encoding="utf-8")

    # 加载通用组件 CSS
    components_css = ""
    components_css_path = TEMPLATES / "themes" / "components.css"
    if components_css_path.exists():
        components_css = components_css_path.read_text(encoding="utf-8")

    now = datetime.now()
    user_name = config.get("user", {}).get("name", "同学")

    CAT_LABELS = {
        "tech": "科技",
        "climate": "气候",
        "gaming": "游戏",
        "sports": "体育",
        "movies": "影视",
        "music": "音乐",
    }

    categories = []
    weather_items = []
    cat_weights = config.get("categories", {})
    ordered_cats = sorted(articles_by_cat.keys(), key=lambda c: -cat_weights.get(c, 0))
    for cat_key in ordered_cats:
        cat_label = CAT_LABELS.get(cat_key, cat_key)
        arts = articles_by_cat.get(cat_key, [])
        categories.append((cat_key, cat_label, arts))
        if cat_key == "climate":
            for a in arts:
                if a.article_type == "weather":
                    weather_items.append(a)

    total = sum(len(v) for v in articles_by_cat.values())

    ai_headlines = headline.get("ai_headlines", [])
    daily_briefing = headline.get("daily_briefing", "")
    ai_headlines_json = json.dumps(ai_headlines, ensure_ascii=False)

    return template.render(
        css=css,
        components_css=components_css,
        date=now.strftime("%Y年%m月%d日"),
        vol=now.strftime("%j"),
        year=now.year,
        user_name=user_name,
        total_articles=total,
        headline=headline.get("headline"),
        side_headlines=headline.get("side_headlines", []),
        categories=categories,
        weather_items=weather_items,
        ai_headlines=ai_headlines,
        ai_headlines_json=ai_headlines_json,
        daily_briefing=daily_briefing,
        has_ai=(len(ai_headlines) > 0),
    )


# ── 核心生成流程（CLI 和 Web 共用）─────────────────────────

def generate_daily(
    config: Dict[str, Any],
    progress_callback: Optional[Callable[[str, str], None]] = None,
) -> Dict[str, Any]:
    """
    执行完整日报生成流程。

    progress_callback(stage, detail):
        stage: "init" | "fetching" | "rendering" | "done"

    返回:
        {
            "html": str,          # 完整 HTML
            "path": str,          # 输出文件绝对路径
            "date": str,          # YYYY-MM-DD
            "stats": {
                "total_articles": int,
                "by_category": {"tech": N, "climate": N, "gaming": N},
                "elapsed_seconds": float,
                "sources_used": int,
                "sources_failed": int,
            }
        }
    """
    start: float = time.time()
    date_str: str = datetime.now().strftime("%Y-%m-%d")

    if progress_callback:
        progress_callback("init", "正在初始化采集器...")

    sources: List["BaseSource"] = create_sources(config)
    if not sources:
        raise ValueError("没有启用任何数据源，请检查配置")

    source_names: List[str] = [s.name for s in sources]
    if progress_callback:
        progress_callback("init", f"已加载 {len(sources)} 个数据源: {', '.join(source_names)}")

    # 1. 并发采集
    articles_by_cat: Dict[str, List["Article"]] = fetch_all(sources, progress_callback=progress_callback)

    # 1.5 内容处理：子主题标注 + 质量评分 + 去重
    try:
        from content_engine import process_articles
        topic_sel: Optional[Dict[str, Any]] = config.get("topic_selection", None)
        articles_by_cat = process_articles(
            articles_by_cat, progress_callback=progress_callback,
            topic_selection=topic_sel,
        )
    except ImportError:
        pass

    # 1.8 翻译英文文章（如果开启了 AI 和翻译）
    translate_cfg = config.get("translate", {})
    if translate_cfg.get("enabled", False):
        ai_service = _init_ai_service(config)
        if ai_service is not None:
            all_articles = []
            for cat_arts in articles_by_cat.values():
                all_articles.extend(cat_arts)
            if progress_callback:
                progress_callback("translating", f"正在翻译英文内容...")
            n = ai_service.translate_batch(all_articles, target_lang="zh")
            if progress_callback and n > 0:
                progress_callback("translating", f"已翻译 {n} 篇英文文章")
        else:
            logger.warning("翻译已启用但 AI 未配置，跳过翻译")

    # 2. 选头条（优先 AI，降级传统）
    ai_enabled: bool = config.get("ai", {}).get("enabled", False) and config.get("ai", {}).get("api_key", "")
    hl: Dict[str, Any]
    if ai_enabled:
        hl = pick_headline_ai(articles_by_cat, config, progress_callback=progress_callback)
    else:
        if progress_callback:
            progress_callback("rendering", "正在排版...")
        hl = pick_headline(articles_by_cat, config)

    # 3. 渲染 HTML
    if progress_callback:
        progress_callback("rendering", "正在渲染 HTML...")
    html: str = render_html(articles_by_cat, hl, config)

    # 4. 写入文件
    OUTPUT.mkdir(exist_ok=True)
    out_path: Path = OUTPUT / f"{date_str}.html"
    out_path.write_text(html, encoding="utf-8")

    elapsed: float = time.time() - start

    by_cat: Dict[str, int] = {cat: len(arts) for cat, arts in articles_by_cat.items()}
    total: int = sum(by_cat.values())

    result: Dict[str, Any] = {
        "html": html,
        "path": str(out_path.resolve()),
        "date": date_str,
        "stats": {
            "total_articles": total,
            "by_category": by_cat,
            "elapsed_seconds": round(elapsed, 1),
            "sources_used": len(sources),
            "sources_failed": 0,  # 在 fetch_all 中不精确统计，此处保守填 0
        },
    }

    if progress_callback:
        progress_callback("done", f"日报生成完成：{total} 条，耗时 {elapsed:.1f}s")

    return result


# ── CLI 入口 ────────────────────────────────────────────────

def _setup_logging() -> logging.Logger:
    """配置日志：同时输出到控制台和文件"""
    logger = logging.getLogger("thedailyme")
    logger.setLevel(logging.DEBUG)

    if logger.handlers:
        logger.handlers.clear()

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter("  %(message)s")
    console_handler.setFormatter(console_formatter)

    log_dir = ROOT / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f"{datetime.now().strftime('%Y-%m-%d')}.log"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    return logger


def main():
    logger = _setup_logging()

    parser = argparse.ArgumentParser(description="TheDailyMe — 个人化赛博日报")
    parser.add_argument("-c", "--config", default="config.yaml",
                        help="配置文件路径（默认: config.yaml）")
    args = parser.parse_args()

    logger.info("╔══════════════════════════════════╗")
    logger.info("║      THE DAILY ME               ║")
    logger.info("║      你的个人日报                ║")
    logger.info("╚══════════════════════════════════╝")

    try:
        config = load_config(args.config)
    except FileNotFoundError as e:
        logger.error(f"配置文件不存在: {e}")
        sys.exit(1)

    def cli_progress(stage: str, detail: str):
        if stage == "init":
            logger.info(f"\n--> {detail}")
        elif stage == "fetching":
            logger.info(f"  {detail}")
        elif stage == "processing":
            logger.info(f"  {detail}")
        elif stage == "ai":
            logger.info(f"  {detail}")
        elif stage == "rendering":
            logger.info(f"\n    {detail}")
        elif stage == "done":
            logger.info(f"\n[OK] {detail}")

    try:
        result = generate_daily(config, progress_callback=cli_progress)
        logger.info(f"\n>> 日报已生成: {result['path']}")
        logger.info(f"    总耗时: {result['stats']['elapsed_seconds']}s")
        logger.info(f"\n用浏览器打开上面的 HTML 文件即可阅读。")

        # ── 通知推送 ──
        pages_url = config.get("pages_url", "")
        notify_cfg = config.get("notify", {})
        if notify_cfg.get("wechat_webhook") or notify_cfg.get("email_smtp_host"):
            logger.info(f"\n-- 发送通知...")
            try:
                from notify import send_daily_brief
                status = send_daily_brief(config, result, result["date"], pages_url)
                for channel, ok in status.items():
                    logger.info(f"  {channel}: {'[OK]' if ok else '[FAIL]'}")
            except ImportError:
                logger.warning("  通知模块未安装（需 requests）")
            except Exception as e:
                logger.warning(f"  通知发送异常: {e}")

        logger.debug(f"生成统计: {result['stats']}")
    except Exception as e:
        logger.error(f"日报生成失败: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
