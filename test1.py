from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time

chrome_options = Options()
chrome_options.add_argument("--headless")
driver = webdriver.Chrome(options=chrome_options)
driver.get("https://opendata.sz.gov.cn/data/dataSet/toDataDetails/29200_00903509")
time.sleep(3)

buttons = driver.find_elements("xpath", "//button[contains(text(),'查看')]")
print("按钮数量:", len(buttons))
if buttons:
    buttons[0].click()
    time.sleep(3)
    html = driver.page_source
    print("包含 table 吗?", "<table" in html)
driver.quit()