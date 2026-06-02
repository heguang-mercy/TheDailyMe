"""
TheDailyMe — Web 客户端
Flask 本地服务，浏览器访问 http://localhost:5050

用法:
    python app.py
    python app.py -p 8080    # 指定端口
"""

import argparse
import threading
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, request, send_file, send_from_directory
from daily import generate_daily, load_config, save_config

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "output"
TEMPLATES_DIR = ROOT / "templates"
STATIC_DIR = ROOT / "static"

STATIC_DIR.mkdir(exist_ok=True)
OUTPUT.mkdir(exist_ok=True)

# ── Flask 应用 ──────────────────────────────────────────────

app = Flask(__name__, template_folder=str(TEMPLATES_DIR), static_folder=str(STATIC_DIR))


# ── 全局生成状态（单用户本地应用，全局变量足够）─────────────

_gen_lock = threading.Lock()
_gen_status = {
    "running": False,
    "stage": "idle",       # idle | init | fetching | rendering | done
    "detail": "",
    "result": None,        # generate_daily 返回值
    "error": None,
}


def _read_status() -> dict:
    with _gen_lock:
        return dict(_gen_status)


def _update_status(**kwargs):
    with _gen_lock:
        _gen_status.update(kwargs)


# ═══════════════════════════════════════════════════════════
#  页面路由
# ═══════════════════════════════════════════════════════════

@app.route("/")
def index():
    """客户端主页面"""
    return send_from_directory(str(TEMPLATES_DIR), "client.html")


@app.route("/report/<date>")
def view_report(date: str):
    """查看某天的日报 HTML"""
    path = OUTPUT / f"{date}.html"
    if not path.exists():
        return "日报不存在", 404
    return send_file(path)


# ═══════════════════════════════════════════════════════════
#  API 路由
# ═══════════════════════════════════════════════════════════

@app.route("/api/archives")
def api_archives():
    """列出所有已生成的日报（按日期倒序）"""
    if not OUTPUT.exists():
        return jsonify([])

    files = sorted(OUTPUT.glob("*.html"), reverse=True)
    archives = []
    for f in files:
        stat = f.stat()
        archives.append({
            "date": f.stem,
            "size_kb": round(stat.st_size / 1024, 1),
            "mtime": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        })
    return jsonify(archives)


@app.route("/api/status")
def api_status():
    """返回当前状态：今天是否已有日报、生成状态"""
    today = datetime.now().strftime("%Y-%m-%d")
    today_exists = (OUTPUT / f"{today}.html").exists()

    status = _read_status()
    return jsonify({
        "today": today,
        "today_exists": today_exists,
        "generating": status["running"],
        "gen_stage": status["stage"],
        "gen_detail": status["detail"],
        "gen_error": status["error"],
    })


@app.route("/api/generate", methods=["POST"])
def api_generate():
    """触发日报生成（后台线程）"""
    status = _read_status()
    if status["running"]:
        return jsonify({"ok": False, "error": "正在生成中，请稍候"}), 409

    def _progress_callback(stage: str, detail: str):
        _update_status(stage=stage, detail=detail)

    def _run():
        try:
            config = load_config()
            result = generate_daily(config, progress_callback=_progress_callback)
            _update_status(result=result, error=None)
        except Exception as e:
            _update_status(error=str(e), result=None)
        finally:
            error = _read_status()["error"]
            _update_status(running=False, stage="done" if not error else "error")

    _update_status(
        running=True,
        stage="init",
        detail="正在启动...",
        result=None,
        error=None,
    )

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    return jsonify({"ok": True})


@app.route("/api/config", methods=["GET"])
def api_get_config():
    """获取当前配置"""
    config = load_config()
    # 移除敏感/不需要的字段
    return jsonify(config)


@app.route("/api/config", methods=["POST"])
def api_save_config():
    """保存配置"""
    data = request.get_json(force=True)
    try:
        save_config(data)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@app.route("/api/topic-hierarchy", methods=["GET"])
def api_topic_hierarchy():
    from content_engine import get_topic_hierarchy
    return jsonify(get_topic_hierarchy())


@app.route("/api/report/<date>", methods=["DELETE"])
def api_delete_report(date: str):
    """删除某天的日报"""
    path = OUTPUT / f"{date}.html"
    if path.exists():
        path.unlink()
        return jsonify({"ok": True})
    return jsonify({"ok": False, "error": "文件不存在"}), 404


# ═══════════════════════════════════════════════════════════
#  启动入口
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TheDailyMe Web 客户端")
    parser.add_argument("-p", "--port", type=int, default=5050,
                        help="服务端口（默认: 5050）")
    parser.add_argument("--host", default="127.0.0.1",
                        help="绑定地址（默认: 127.0.0.1）")
    args = parser.parse_args()

    print("╔══════════════════════════════════════╗")
    print("║      THE DAILY ME — Web 客户端      ║")
    print("╚══════════════════════════════════════╝")
    print(f"\n>> 浏览器打开: http://{args.host}:{args.port}")
    print(f">> 日报存档: {OUTPUT}")
    print(f"\n按 Ctrl+C 停止服务\n")

    app.run(host=args.host, port=args.port, debug=False)
