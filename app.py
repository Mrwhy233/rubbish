from flask import Flask, render_template, request, Response, jsonify, send_file
from bs4 import BeautifulSoup
import json
import requests
import time
import os
import csv
from io import StringIO

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

app = Flask(__name__)

# 本地历史记录文件
HISTORY_FILE = "history.json"


# ----------------------------------------------------
# 工具函数：加载与保存历史
# ----------------------------------------------------
def load_history():
    """读取历史记录"""
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_history(entry):
    """保存新的爬取记录"""
    data = load_history()
    # 若历史中已有相同URL，则覆盖
    for item in data:
        if item["url"] == entry["url"]:
            item.update(entry)
            break
    else:
        data.insert(0, entry)  # 最新在最前
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def delete_history(index):
    data = load_history()
    if 0 <= index < len(data):
        del data[index]
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    return False


# ---------------------------------------------------
# Selenium 模拟加载
# ---------------------------------------------------
def fetch_with_selenium(url, yield_log, retry_no_headless=False):
    """使用 Selenium 模拟打开网页"""
    try:
        chrome_options = Options()
        if not retry_no_headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("window-size=1920,1080")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/128.0.0.0 Safari/537.36"
        )

        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(40)

        mode = "🔒 取消无界面模式重新尝试加载" if retry_no_headless else "🚀 启动浏览器模式加载网页"
        yield_log(mode)
        driver.get(url)

        # 等待正文加载
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "article, .blog-content-box, #content_views, .article-content"))
            )
            yield_log("✅ 检测到内容加载。")
        except Exception:
            yield_log("⚠️ 未检测到特定内容区域，继续...")

        # 向下滚动以触发懒加载
        last_height = driver.execute_script("return document.body.scrollHeight")
        for i in range(5):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
            yield_log(f"↩️ 第 {i+1} 次滚动完成")

        html = driver.page_source
        driver.quit()
        yield_log("✅ 页面加载完毕。")
        return html

    except Exception as e:
        yield_log(f"❌ Selenium 出错: {e}")
        return None


# ---------------------------------------------------
# Flask 主路由
# ---------------------------------------------------
@app.route('/')
def home():
    return render_template('index.html')


# -------------------- 核心爬取 ---------------------
@app.route('/stream', methods=['POST'])
def stream():
    data = request.get_json()
    url = data.get("url")

    def generate():
        def send_log(msg):
            yield f"data: {json.dumps({'log': msg})}\n\n"

        if not url:
            yield f"data: {json.dumps({'error': '❌ 未提供URL'})}\n\n"
            return

        try:
            yield from send_log(f"开始爬取 {url} ...")
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/128.0.0.0 Safari/537.36"
                )
            }

            html = None
            yield from send_log("🌍 使用requests获取中...")
            try:
                resp = requests.get(url, headers=headers, timeout=10)
                if resp.status_code in [403, 520, 521, 522, 523, 524]:
                    yield from send_log(f"⚠️ 状态码 {resp.status_code}，切换到浏览器方式。")
                    html = fetch_with_selenium(url, lambda m: (yield from send_log(m)))
                else:
                    html = resp.text
                    yield from send_log("✅ requests成功。")
            except Exception as e:
                yield from send_log(f"⚠️ requests 失败: {e}")
                html = fetch_with_selenium(url, lambda m: (yield from send_log(m)))

            if not html:
                yield f"data: {json.dumps({'error': '❌ 获取网页失败'})}\n\n"
                return

            # ---- 解析HTML ----
            soup = BeautifulSoup(html, "html.parser")
            title = soup.title.string.strip() if soup.title else "无标题"
            paragraphs = [p.get_text(strip=True) for p in soup.find_all('p') if p.get_text(strip=True)]
            links = [a['href'] for a in soup.find_all('a', href=True)]

            # ---- 新增：表格提取 ----
            tables_data = []
            tables = soup.find_all("table")
            for t in tables:
                headers = [th.get_text(strip=True) for th in t.find_all("th")]
                rows = []
                for tr in t.find_all("tr"):
                    cells = [td.get_text(strip=True) for td in tr.find_all("td")]
                    if cells:
                        rows.append(cells)
                if headers or rows:
                    tables_data.append({"headers": headers, "rows": rows})

            # ---- 若检测安全验证则重试 ----
            if "安全验证" in title or len(paragraphs) < 5:
                yield from send_log("⚠️ 检测安全验证页面，重新尝试(关闭无界面)")
                html_retry = fetch_with_selenium(url, lambda m: (yield from send_log(m)), retry_no_headless=True)
                if html_retry:
                    soup = BeautifulSoup(html_retry, "html.parser")
                    title = soup.title.string.strip() if soup.title else title
                    paragraphs = [p.get_text(strip=True) for p in soup.find_all('p') if p.get_text(strip=True)]
                    links = [a['href'] for a in soup.find_all('a', href=True)]
                    tables_data = []
                    tables = soup.find_all("table")
                    for t in tables:
                        headers = [th.get_text(strip=True) for th in t.find_all("th")]
                        rows = []
                        for tr in t.find_all("tr"):
                            cells = [td.get_text(strip=True) for td in tr.find_all("td")]
                            if cells:
                                rows.append(cells)
                        if headers or rows:
                            tables_data.append({"headers": headers, "rows": rows})

            paragraphs = list(dict.fromkeys(paragraphs))[:200]
            links = list(dict.fromkeys(links))[:200]

            result = {
                "url": url,
                "title": title,
                "paragraphs": paragraphs,
                "links": links,
                "tables": tables_data,  # ✅ 新增字段
                "time": time.strftime("%Y-%m-%d %H:%M:%S")
            }

            # 保存历史记录
            save_history(result)
            yield from send_log(f"✅ 获取成功，共 {len(paragraphs)} 段文字，{len(links)} 个链接，{len(tables_data)} 个表格，已保存到历史记录。")

            yield f"data: {json.dumps({'result': result})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': f'任务出错：{str(e)}'})}\n\n"

    return Response(generate(), mimetype="text/event-stream")


# -------------------- 历史接口 ---------------------
@app.route("/history", methods=["GET"])
def history_list():
    """获取所有历史记录"""
    data = load_history()
    return jsonify(data)


@app.route("/history/<int:index>", methods=["GET"])
def get_history_item(index):
    """获取单条历史"""
    data = load_history()
    if 0 <= index < len(data):
        return jsonify(data[index])
    return jsonify({"error": "索引超出范围"}), 404


@app.route("/history/<int:index>", methods=["DELETE"])
def delete_history_item(index):
    """删除指定历史"""
    ok = delete_history(index)
    return jsonify({"ok": ok})


@app.route("/history/export/<int:index>", methods=["GET"])
def export_history_item(index):
    """导出历史为单独JSON文件"""
    data = load_history()
    if 0 <= index < len(data):
        filename = f"export_{index}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data[index], f, ensure_ascii=False, indent=2)
        return send_file(filename, as_attachment=True)
    return jsonify({"error": "未找到"}), 404


# -------------------- 新增：导出表格为CSV ---------------------
@app.route("/history/export_table/<int:index>/<int:table_idx>", methods=["GET"])
def export_table_csv(index, table_idx):
    """导出某条历史中的某个表格为CSV"""
    data = load_history()
    if 0 <= index < len(data):
        item = data[index]
        tables = item.get("tables", [])
        if 0 <= table_idx < len(tables):
            table = tables[table_idx]
            csv_file = StringIO()
            writer = csv.writer(csv_file)
            if table["headers"]:
                writer.writerow(table["headers"])
            writer.writerows(table["rows"])
            csv_file.seek(0)

            filename = f"table_{index}_{table_idx}.csv"
            return Response(
                csv_file.getvalue(),
                mimetype="text/csv",
                headers={"Content-Disposition": f"attachment;filename={filename}"}
            )
    return jsonify({"error": "未找到表格"}), 404


# -------------------- 启动 ---------------------
if __name__ == '__main__':
    print("🚀 Flask + 表格增强版爬虫启动：http://127.0.0.1:5000")
    app.run(debug=True, threaded=True)