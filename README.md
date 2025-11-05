# 🕷️ 智能分页网页爬虫系统（Smart Web Crawler with Pagination）

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.x-orange)](https://flask.palletsprojects.com/)
[![Selenium](https://img.shields.io/badge/Selenium-Automation-green)](https://www.selenium.dev/)
[![Status](https://img.shields.io/badge/Release-v1.5-brightgreen)]()

---

> 🌐 一款可实时展示网页内容的 **智能爬虫系统**。支持分页显示正文与链接、防反爬机制、历史记录保存、快速回看与数据导出。（随便做着玩玩的，功能缺少，有空再改）

---
## ❓ 为什么（why）
> 为什么做这个玩意，主要是为了符合范小橦的需要爬取数据。因为公司数据不能够直接**ctrl+a**直接全选然后复制。高手说要换浏览器试试，但是范小橦觉得这样子太low了，所以我来试试做个爬虫数据显得高大上一点~~

## 📸 项目预览（Project Screenshot）

<p align="center">
  <img src="image/image.png" alt="Demo Screenshot" width="860">
</p>

---

## 📚 目录（Table of Contents）
- [✨ 功能特性](#-功能特性)
- [⚙️ 环境准备](#️-环境准备)
- [🚀 快速上手](#-快速上手)
- [📂 项目结构](#-项目结构)
- [🧩 系统模块说明](#-系统模块说明)
- [🧠 技术细节](#-技术细节)
- [📡 API 接口](#-api-接口)
- [💾 历史数据结构](#-历史数据结构)
- [📊 扩展建议](#-扩展建议)
- [👨‍💻 作者信息](#-作者信息)

---

## ✨ 功能特性
| 模块 | 描述 |
|------|------|
| ⚡ 实时爬取 | 自动适配防爬机制，实时输出日志 |
| 📑 分页展示 | 正文与链接多页浏览，支持翻页 |
| 📜 历史记录 | 每次爬取自动保存，可快速回看 |
| 🔁 一键重爬 | 历史记录直接重新抓取 |
| 💾 导出结果 | 单条历史可导出 JSON 文件 |
| ❌ 删除记录 | 历史记录列表可手动管理 |
| 🔍 搜索过滤 | 关键字快速筛选历史记录 |

---

## ⚙️ 环境准备

### 🧱 环境依赖
- Python ≥ 3.8  
- Google Chrome 浏览器  
- ChromeDriver（版本匹配 Chrome）

### 🧰 安装依赖包
```bash  
pip install flask requests beautifulsoup4 selenium  
```
### 🧩 验证 WebDriver
```bash  
chromedriver --version
```
## 🚀 快速上手
### 1️⃣ 启动后端
```bash  
python app.py
```
### 2️⃣ 打开浏览器
```python 
http://127.0.0.1:5000
```
### 3️⃣ 操作步骤
- 输入目标网址；
- 点击「开始爬取」；
- 实时查看控制台日志；
-分页浏览正文与链接；
- 历史记录自动保存，可再次查看。
## 📂 项目结构
```python
smart-crawler/
├── app.py                   # 后端主程序（Flask + Selenium + BS4）
├── chromedriver.exe         # 模拟浏览器驱动
├── history.json              # 历史记录存储文件（自动生成）
├──templates/
    └── index.html            # 前端界面模板（分页 + 历史系统）
└──static                    #样式和前端渲染
    ├── style.css
    └── script.js
```
### 文件说明：
| 文件     | 描述 |
| ----------- | ----------- |
| app.py      | 主程序，包含爬取、日志推送、历史接口等逻辑      |
| history.json  | 自动生成的本地历史缓存       |
| index.html  | 网页端（前端交互 + 分页展示）       |
## 🧩 系统模块说明
### 🌍 爬取模块（/stream）
后端核心接口，采用 **Server-Sent Events (SSE)** 推送日志流。
可在爬取时实时输出状态，用户可边看边等。
### 流程：
1. 尝试使用 requests 获取页面；
2. 若触发防爬（403/520等），自动切换至 Selenium 浏览器渲染；
3. 模拟滚动滚动触发懒加载；
4. 提取标题、段落、链接并返回；
5. 结果自动写入 history.json。
### 📜 历史记录模块
接口：
| 路径    | 方法 |功能|
| ----------- | ----------- | ----------- |
|/history     | GET |获取所有历史爬取记录|
| /history/<index>  | GET |获取单条记录|
| /history/<index>  |	DELETE |删除记录|
| /history/export/<index> |	GET|下载单条记录 JSON|
前端侧边栏会自动请求 **/history** 渲染历史数据。
### 🧩 前端模块 (index.html)
- 使用原生 HTML + JS + CSS
- 支持：
    - 🧾 正文分页；
    - 🔗 链接分页；
    - 🕓 实时日志；
    - 📜 历史加载与搜索；
    - 🔁、❌、💾 操作按钮。
## 🧠 技术细节
| 要点     | 实现 |
| ----------- | ----------- |
| 防反爬机制    | 根据状态码自动切换 **requests/Selenium**    |
| 懒加载滚动  | 模拟滚动触发动态内容加载       |
| 流式通信  | SSE (**text/event-stream**) 实现边爬边显示      |
| 内容去重  | 	**dict.fromkeys()** 去除重复段落与链接     |
| 持久化存储  | 结果保存于 JSON 文件 **history.json**    |
## 📡 API 接口示例
```json
{
  "log": "🔍 解析网页中...",
  "result": {
    "url": "https://example.com",
    "title": "示例网页",
    "paragraphs": ["这是第一段", "这是第二段"],
    "links": ["https://a.com", "https://b.com"],
    "time": "2025-11-05 22:45:33"
  }
}
```
## 💾 历史数据结构
```json
[
  {
    "url": "https://blog.example.com/post/123",
    "title": "示例文章",
    "paragraphs": ["段1", "段2", "段3"],
    "links": ["https://img.example.com/a.jpg"],
    "time": "2025-11-05 22:31:00"
  }
]
```
## 📊 扩展建议
| 模块     | 功能  |
| ----------- | ----------- |
| 🧩 分类标签系统    | 自动识别内容类型（技术/博客/论坛）   |
| 📈 统计面板  | 展示爬取数量、来源域名统计、时间趋势     |
| 📤 导出格式  | 支持 CSV、Excel 格式    |
| ⚙️ 数据库版本  | 	用 SQLite 存储历史，支持分页查询    |
| 🤖 异步任务 | 用 Celery 实现多任务并行爬取   |
## 👨‍💻 作者信息
- **Author：** 一坨屎
- **Tech Stack：** Python · Flask · Selenium · JS
- **Release Date：** 2025-11-05
- **GitHub：**[view my github ](https://github.com/Mrwhy233)

