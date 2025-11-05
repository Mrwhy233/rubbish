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

HISTORY_FILE = "history.json"


# ----------------------------------------------------
# 工具函数：加载与保存历史
# ----------------------------------------------------
def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_history(entry):
    data = load_history()
    for item in data:
        if item["url"] == entry["url"]:
            item.update(entry)
            break
    else:
        data.insert(0, entry)
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
# Selenium 模拟加载（支持多表格点击）
# ---------------------------------------------------
def fetch_with_selenium_multi(url, yield_log):
    """使用 Selenium 打开网页并点击所有数据表按钮，提取所有表格 HTML"""
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("window-size=1920,1080")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        )

        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(50)
        yield_log("🚀 启动浏览器加载网页中...")
        driver.get(url)
        time.sleep(4)

        # ↓ 模拟滚动，确保懒加载元素出现
        last_height = driver.execute_script("return document.body.scrollHeight")
        for _ in range(3):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

        # 查找所有按钮
        buttons = driver.find_elements(
            By.XPATH,
            "//a[contains(text(),'数据表')]"
            " | //button[contains(text(),'查看')]"
            " | //button[contains(text(),'表')]"
        )
        yield_log(f"🔍 找到 {len(buttons)} 个可能可点击的表格按钮。")

        # 如果一个按钮都没找到，只返回整个页面源代码
        if not buttons:
            html = driver.page_source
            driver.quit()
            yield_log("⚠️ 未检测到表格按钮，直接返回页面源。")
            return html

        full_html = ""
        for i, btn in enumerate(buttons):
            try:
                driver.execute_script("arguments[0].scrollIntoView();", btn)
                time.sleep(1)
                btn.click()
                yield_log(f"✅ 点击第 {i+1}/{len(buttons)} 个按钮，等待表格加载...")

                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "table"))
                )
                time.sleep(1)
                html_part = driver.page_source
                full_html += "\n<!-- 表格分隔符 -->\n" + html_part
                # 尝试关闭弹窗
                try:
                    driver.find_element(By.CSS_SELECTOR, "body").click()
                except Exception:
                    pass
                time.sleep(1)
            except Exception as e:
                yield_log(f"⚠️ 第 {i+1} 个按钮点击出错：{e}")

        driver.quit()
        yield_log("📊 所有弹窗采集完毕。")
        return full_html

    except Exception as e:
        yield_log(f"❌ Selenium 出错: {e}")
        return None


# ---------------------------------------------------
# Flask 主页面
# ---------------------------------------------------
@app.route('/')
def home():
    return render_template('index.html')


# ---------------------------------------------------
# 核心爬取接口
# ---------------------------------------------------
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

            # ---------------- 深圳开放数据 ----------------
            if "opendata.sz.gov.cn" in url:
                yield from send_log("🏙️ 检测到深圳开放数据平台，启用多表格采集模式。")
                html = fetch_with_selenium_multi(url, lambda m: (yield from send_log(m)))

            # ---------------- 常规网站 ----------------
            else:
                yield from send_log("🌍 尝试requests请求...")
                try:
                    resp = requests.get(url, headers=headers, timeout=10)
                    if resp.status_code >= 400:
                        yield from send_log(f"⚠️ 状态码 {resp.status_code}，切换 Selenium。")
                        html = fetch_with_selenium_multi(url, lambda m: (yield from send_log(m)))
                    else:
                        html = resp.text
                        yield from send_log("✅ requests 请求成功。")
                except Exception as e:
                    yield from send_log(f"⚠️ requests 失败：{e}")
                    html = fetch_with_selenium_multi(url, lambda m: (yield from send_log(m)))

            if not html:
                yield f"data: {json.dumps({'error': '❌ 未能获取网页'})}\n\n"
                return

            # ---------------- HTML解析 ----------------
            soup = BeautifulSoup(html, "html.parser")
            title = soup.title.string.strip() if soup.title else "无标题"
            paragraphs = [p.get_text(strip=True) for p in soup.find_all('p') if p.get_text(strip=True)]
            links = [a['href'] for a in soup.find_all('a', href=True)]

            # ---------------- 表格提取 ----------------
            tables_data = []
            for t in soup.find_all("table"):
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
                "tables": tables_data,
                "time": time.strftime("%Y-%m-%d %H:%M:%S")
            }

            save_history(result)
            yield from send_log(
                f"✅ 完成：提取 {len(paragraphs)} 段文字，{len(links)} 个链接，{len(tables_data)} 个表格"
            )

            yield f"data: {json.dumps({'result': result})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': f'任务出错：{str(e)}'})}\n\n"

    return Response(generate(), mimetype="text/event-stream")


# ---------------------------------------------------
# 历史与导出接口
# ---------------------------------------------------
@app.route("/history", methods=["GET"])
def history_list():
    return jsonify(load_history())


@app.route("/history/<int:index>", methods=["GET"])
def get_history_item(index):
    data = load_history()
    if 0 <= index < len(data):
        return jsonify(data[index])
    return jsonify({"error": "索引超出范围"}), 404


@app.route("/history/<int:index>", methods=["DELETE"])
def delete_history_item(index):
    ok = delete_history(index)
    return jsonify({"ok": ok})


@app.route("/history/export/<int:index>", methods=["GET"])
def export_history_item(index):
    data = load_history()
    if 0 <= index < len(data):
        filename = f"export_{index}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data[index], f, ensure_ascii=False, indent=2)
        return send_file(filename, as_attachment=True)
    return jsonify({"error": "未找到"}), 404


@app.route("/history/export_table/<int:index>/<int:table_idx>", methods=["GET"])
def export_table_csv(index, table_idx):
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


# ---------------------------------------------------
# 启动入口
# ---------------------------------------------------
if __name__ == '__main__':
    print("🚀 Flask + 深圳开放数据多表格增强版启动：http://127.0.0.1:5000")
    app.run(debug=True, threaded=True)