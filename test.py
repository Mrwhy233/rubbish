from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import csv
import time

# ====== 1️⃣ 配置 Selenium ======
chrome_options = Options()
chrome_options.add_argument("--headless")  # 无界面模式，取消这一行可看可视化浏览器
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
service = Service()  # 自动找驱动
driver = webdriver.Chrome(service=service, options=chrome_options)

# ====== 2️⃣ 打开主页面 ======
url = "https://opendata.sz.gov.cn/data/catalog/toDataCatalog"
driver.get(url)
driver.maximize_window()
time.sleep(3)

# ====== 3️⃣ 定位目标数据集卡片并点击 ======
target_text = "自动站实况格点数据表"
# 精确匹配按钮文字
target_button = WebDriverWait(driver, 10).until(
    EC.element_to_be_clickable((By.XPATH, f"//a[contains(text(),'{target_text}')]"))
)
target_button.click()

# ====== 4️⃣ 等待弹窗加载完成 ======
WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.CSS_SELECTOR, ".modal-dialog table"))
)
time.sleep(1)

# ====== 5️⃣ 抓取弹窗 HTML 并解析表格 ======
popup_html = driver.find_element(By.CSS_SELECTOR, ".modal-dialog").get_attribute("outerHTML")
soup = BeautifulSoup(popup_html, "html.parser")

rows = []
for tr in soup.select("table tr"):
    cells = [td.get_text(strip=True) for td in tr.find_all(["th", "td"])]
    rows.append(cells)

driver.quit()

# ====== 6️⃣ 打印表格内容 ======
for row in rows:
    print("\t".join(row))

# ====== 7️⃣ 可选：保存为 CSV ======
with open("深圳自动站实况格点表.csv", "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f)
    writer.writerows(rows)

print("✅ 数据已保存到 深圳自动站实况格点表.csv")