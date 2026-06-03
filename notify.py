"""
TheDailyMe — 通知推送模块

支持两种推送渠道：
  1. 企业微信机器人 Webhook（推荐，免费即配即用）
  2. SMTP 邮件（支持 163/QQ/Gmail 等）

用法：
    from notify import send_daily_brief

    send_daily_brief(config, result, date_str)
"""

import json
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import requests

logger = logging.getLogger("thedailyme.notify")


# ═══════════════════════════════════════════════════════════
#  企业微信机器人 Webhook
# ═══════════════════════════════════════════════════════════

def send_wechat(webhook_url: str, date_str: str,
                result: Optional[dict] = None,
                pages_url: str = "") -> bool:
    """
    通过企业微信机器人 Webhook 发送日报摘要。

    如何获取 Webhook URL：
      1. 打开企业微信 → 群聊 → 群设置 → 群机器人 → 添加机器人
      2. 复制 Webhook 地址
      3. 填入 config.yaml 的 notify.wechat_webhook
    """
    stats = result.get("stats", {}) if result else {}
    total = stats.get("total_articles", 0)
    by_cat = stats.get("by_category", {})

    # 构建分类统计
    cat_names = {"tech": "科技", "climate": "气候", "gaming": "游戏",
                 "sports": "体育", "movies": "影视", "music": "音乐"}
    cat_str = "  |  ".join(
        f"{cat_names.get(c, c)} {n}条"
        for c, n in (by_cat or {}).items() if n > 0
    )

    # 日报链接
    link_line = ""
    if pages_url:
        link_line = f"\n[查看完整日报]({pages_url.rstrip('/')}/{date_str}.html)"

    content = (
        f"## TheDailyMe · {date_str}\n"
        f"> 今日采集 **{total}** 条内容\n\n"
        f"{cat_str}"
        f"{link_line}"
    )

    try:
        resp = requests.post(webhook_url, json={
            "msgtype": "markdown",
            "markdown": {"content": content},
        }, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data.get("errcode") == 0:
            logger.info("企业微信通知发送成功")
            return True
        else:
            logger.warning("企业微信通知失败: %s", data)
            return False
    except Exception as e:
        logger.warning("企业微信通知异常: %s", e)
        return False


# ═══════════════════════════════════════════════════════════
#  SMTP 邮件
# ═══════════════════════════════════════════════════════════

def send_email(smtp_host: str, smtp_port: int,
               user: str, password: str,
               to_addr: str, date_str: str,
               html_content: str = "",
               pages_url: str = "") -> bool:
    """
    通过 SMTP 发送日报邮件。

    常用邮箱 SMTP 配置：
      163:  smtp.163.com, port 465 (SSL)
      QQ:   smtp.qq.com,   port 465 (SSL), 需要授权码
      Gmail: smtp.gmail.com, port 587 (TLS), 需要应用专用密码

    html_content: 空则发送纯文本摘要，传了就发 HTML 邮件
    """
    pages_link = f"{pages_url.rstrip('/')}/{date_str}.html" if pages_url else ""

    # 构建邮件
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"TheDailyMe · {date_str} 日报"
    msg["From"] = user
    msg["To"] = to_addr

    if html_content:
        # HTML 邮件（直接发送日报全文）
        full_html = f"""\
<!DOCTYPE html><html><head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#faf7f2;">
{html_content}
</body></html>"""
        msg.attach(MIMEText(full_html, "html", "utf-8"))
    else:
        # 纯文本摘要
        text = (
            f"TheDailyMe · {date_str}\n"
            f"{'─' * 40}\n"
            f"今日日报已生成。\n"
            f"完整阅读: {pages_link}\n"
        )
        msg.attach(MIMEText(text, "plain", "utf-8"))

    try:
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=15)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=15)
            server.starttls()
        server.login(user, password)
        server.sendmail(user, [to_addr], msg.as_string())
        server.quit()
        logger.info("邮件发送成功 → %s", to_addr)
        return True
    except Exception as e:
        logger.warning("邮件发送失败: %s", e)
        return False


# ═══════════════════════════════════════════════════════════
#  统一入口
# ═══════════════════════════════════════════════════════════

def send_daily_brief(config: dict, result: dict, date_str: str,
                     pages_url: str = "") -> dict[str, bool]:
    """
    根据配置发送日报通知。

    config["notify"]:
        wechat_webhook: ""      # 企业微信机器人 URL
        email_smtp_host: ""     # SMTP 服务器
        email_smtp_port: 465
        email_user: ""          # 发件邮箱
        email_pass: ""          # 密码/授权码
        email_to: ""            # 收件邮箱（多个用逗号隔开，或 YAML 列表）

    pages_url: GitHub Pages 或部署 URL，生成日报链接

    返回 {"wechat": bool, "email": {"addr": bool, "_all": bool}}
    """
    notify_cfg = config.get("notify", {})
    if not notify_cfg:
        logger.info("未配置通知渠道")
        return {}

    status = {}

    # 企业微信
    webhook = notify_cfg.get("wechat_webhook", "")
    if webhook:
        logger.info("发送企业微信通知...")
        status["wechat"] = send_wechat(webhook, date_str, result, pages_url)

    # 邮件
    smtp_host = notify_cfg.get("email_smtp_host", "")
    if smtp_host:
        # 支持多个收件箱：逗号分隔 or YAML 列表
        raw_to = notify_cfg.get("email_to", "")
        if isinstance(raw_to, list):
            to_addrs = raw_to
        elif isinstance(raw_to, str):
            to_addrs = [a.strip() for a in raw_to.split(",") if a.strip()]
        else:
            to_addrs = []

        if not to_addrs:
            logger.warning("邮件配置了 SMTP 但未指定收件人 (email_to)")
        else:
            status["email"] = {}
            html = result.get("html", "")
            for addr in to_addrs:
                ok = send_email(
                    smtp_host=smtp_host,
                    smtp_port=notify_cfg.get("email_smtp_port", 465),
                    user=notify_cfg.get("email_user", ""),
                    password=notify_cfg.get("email_pass", ""),
                    to_addr=addr,
                    date_str=date_str,
                    html_content=html,
                    pages_url=pages_url,
                )
                status["email"][addr] = ok
                if ok:
                    logger.info("  邮件 -> %s [OK]", addr)
                else:
                    logger.warning("  邮件 -> %s [FAIL]", addr)
            status["email"]["_all"] = all(status["email"].values())

    return status
