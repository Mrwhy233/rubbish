document.getElementById("scrapeBtn").addEventListener("click", () => {
  const url = document.getElementById("urlInput").value.trim();
  const logs = document.getElementById("logs");
  const resultDiv = document.getElementById("result");
  logs.innerHTML = "";
  resultDiv.innerHTML = "";

  if (!url) {
    alert("请输入网址！");
    return;
  }

  logs.innerHTML += `> 已启动爬取任务...\n`;

  const eventSource = new EventSourcePolyfill("/stream", {
    headers: { "Content-Type": "application/json" },
    payload: JSON.stringify({ url }),
  });

  eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.log) {
      logs.innerHTML += data.log + "\n";
      logs.scrollTop = logs.scrollHeight;
    }
    if (data.result) {
      const { title, paragraphs, links } = data.result;
      let html = `<h3>网页标题：${title}</h3>`;
      html += `<h4>主要段落：</h4><ul>`;
      paragraphs.forEach((p) => (html += `<li>${p}</li>`));
      html += `</ul><h4>所有链接：</h4><ul>`;
      links.forEach(
        (link) => (html += `<li><a href="${link}" target="_blank">${link}</a></li>`)
      );
      html += `</ul>`;
      resultDiv.innerHTML = html;
    }
    if (data.error) {
      logs.innerHTML += "❌ 出错：" + data.error + "\n";
      eventSource.close();
    }
  };

  eventSource.onerror = (err) => {
    logs.innerHTML += "⚠️ 流式连接已断开。\n";
    eventSource.close();
  };
});


// Polyfill for EventSource with POST support
class EventSourcePolyfill {
  constructor(url, options) {
    const { headers, payload } = options;
    this.controller = new AbortController();

    this._init(url, headers, payload);
  }

  async _init(url, headers, payload) {
    try {
      const response = await fetch(url, {
        method: "POST",
        headers,
        body: payload,
        signal: this.controller.signal,
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n\n");
        buffer = parts.pop();

        for (const part of parts) {
          if (part.startsWith("data:")) {
            const event = { data: part.replace(/^data:\s*/, "") };
            this.onmessage && this.onmessage(event);
          }
        }
      }
    } catch (err) {
      this.onerror && this.onerror(err);
    }
  }

  close() {
    this.controller.abort();
  }
}