/* ==========================================================
   人工智能心理咨询陪练系统 - 前端逻辑
   仅与本地后端通信，不包含任何第三方 API 信息
   ========================================================== */

// 后端地址：同源托管时留空字符串；直接以 file:// 打开时改为 "http://127.0.0.1:5000"
const API_BASE = "";

// ---------------------------------------------------------------------------
// 工具函数
// ---------------------------------------------------------------------------
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));

function showToast(msg, isError = false) {
  const toast = $("#toast");
  toast.textContent = msg;
  toast.classList.toggle("error", isError);
  toast.classList.add("show");
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => toast.classList.remove("show"), 2600);
}

/** 初始化一个分段选择器组：单选 + 读取当前值 */
function initSegmentGroup(groupId) {
  const group = document.getElementById(groupId);
  group.addEventListener("click", (e) => {
    const btn = e.target.closest(".segment");
    if (!btn || group.dataset.disabled === "1") return;
    group.querySelectorAll(".segment").forEach((s) => s.classList.remove("active"));
    btn.classList.add("active");
  });
  return {
    get value() {
      const active = group.querySelector(".segment.active");
      return active ? active.dataset.value : "";
    },
    disable() {
      group.dataset.disabled = "1";
      group.style.opacity = "0.6";
      group.style.pointerEvents = "none";
    },
    enable() {
      group.dataset.disabled = "";
      group.style.opacity = "";
      group.style.pointerEvents = "";
    },
  };
}

/** 生成一个防抖后的 markdown 渲染器（流式期间避免每帧重排） */
function createMarkdownRenderer(el) {
  let pending = "";
  let timer = null;
  const render = () => {
    el.innerHTML = marked.parse(pending);
    el.scrollTop = el.scrollHeight; // 滚动到底部跟随输出
  };
  return {
    append(chunk) {
      pending += chunk;
      if (!timer) {
        timer = setTimeout(() => {
          timer = null;
          render();
        }, 80);
      }
    },
    get text() {
      return pending;
    },
    finish() {
      if (timer) {
        clearTimeout(timer);
        timer = null;
      }
      render();
    },
    clear() {
      pending = "";
      if (timer) {
        clearTimeout(timer);
        timer = null;
      }
      el.innerHTML = "";
    },
  };
}

/** 流式请求本地后端，逐段回调 content */
async function streamGenerate(url, body, onChunk) {
  const resp = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!resp.ok || !resp.body) {
    throw new Error(`后端响应异常（HTTP ${resp.status}）`);
  }

  const reader = resp.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // 按 SSE 规范以 \n\n 分隔事件
    const events = buffer.split("\n\n");
    buffer = events.pop(); // 末段可能不完整，留在缓冲区

    for (const evt of events) {
      for (const line of evt.split("\n")) {
        if (!line.startsWith("data:")) continue;
        const payload = line.slice(5).trim();
        if (!payload || payload === "[DONE]") continue;
        try {
          const obj = JSON.parse(payload);
          if (obj.error) throw new Error(obj.error);
          if (obj.content) onChunk(obj.content);
        } catch (err) {
          if (err instanceof SyntaxError) continue; // 忽略不完整 JSON
          throw err; // 后端明确返回的业务错误
        }
      }
    }
  }
}

/** 导出文本为 .txt 文件 */
function exportTxt(filename, text) {
  const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// ---------------------------------------------------------------------------
// 星光背景
// ---------------------------------------------------------------------------
(function initStars() {
  const wrap = $("#stars");
  const COUNT = 70;
  const frag = document.createDocumentFragment();
  for (let i = 0; i < COUNT; i++) {
    const star = document.createElement("div");
    star.className = "star";
    const size = Math.random() * 2.2 + 0.6;
    star.style.width = `${size}px`;
    star.style.height = `${size}px`;
    star.style.left = `${Math.random() * 100}%`;
    star.style.top = `${Math.random() * 100}%`;
    star.style.animationDelay = `${Math.random() * 4}s`;
    star.style.animationDuration = `${3 + Math.random() * 4}s`;
    frag.appendChild(star);
  }
  wrap.appendChild(frag);
})();

// ---------------------------------------------------------------------------
// Tab 切换
// ---------------------------------------------------------------------------
$$(".tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    $$(".tab-btn").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    $$(".panel").forEach((p) => p.classList.remove("active"));
    $(`#panel-${btn.dataset.tab}`).classList.add("active");
  });
});

// ---------------------------------------------------------------------------
// 表单状态
// ---------------------------------------------------------------------------
const lessonStage = initSegmentGroup("lesson-stage");
const lessonDuration = initSegmentGroup("lesson-duration");
const lessonStyle = initSegmentGroup("lesson-style");
const scriptDuration = initSegmentGroup("script-duration");
const scriptMultiEnding = initSegmentGroup("script-multi-ending");

// ---------------------------------------------------------------------------
// 面板配置
// ---------------------------------------------------------------------------
const panels = {
  lesson: {
    endpoint: `${API_BASE}/api/generate/lesson`,
    button: $("#btn-lesson"),
    inputs: () => [
      $("#lesson-topic"),
    ],
    segments: [lessonStage, lessonDuration, lessonStyle],
    buildBody: () => ({
      topic: $("#lesson-topic").value.trim(),
      stage: lessonStage.value,
      duration: lessonDuration.value,
      style: lessonStyle.value,
    }),
    resultBox: $("#result-lesson"),
    copyBtn: $("#copy-lesson"),
    exportBtn: $("#export-lesson"),
    filename: "教案.txt",
  },

  script: {
    endpoint: `${API_BASE}/api/generate/script`,
    button: $("#btn-script"),
    inputs: () => [
      $("#script-topic"),
    ],
    segments: [scriptDuration, scriptMultiEnding],
    buildBody: () => ({
      topic: $("#script-topic").value.trim(),
      characters: $("#script-characters").value,
      duration: scriptDuration.value,
      setting: $("#script-setting").value.trim(),
      multiEnding: scriptMultiEnding.value,
    }),
    resultBox: $("#result-script"),
    copyBtn: $("#copy-script"),
    exportBtn: $("#export-script"),
    filename: "情景剧脚本.txt",
  },
};

// ---------------------------------------------------------------------------
// 生成流程
// ---------------------------------------------------------------------------
async function runGenerate(panel) {
  const { endpoint, button, buildBody, resultBox, inputs, segments } = panel;
  const body = buildBody();

  if (!body.topic) {
    showToast("请先填写主题", true);
    inputs()[0].focus();
    return;
  }

  const originalLabel = button.querySelector("span").textContent;

  // 进入生成中状态
  button.disabled = true;
  button.querySelector("span").textContent = "生成中...";
  inputs().forEach((i) => (i.disabled = true));
  segments.forEach((s) => s.disable());
  resultBox.innerHTML =
    '<div class="markdown-body"><p><strong>正在生成，请稍候…</strong><span class="stream-cursor"></span></p></div>';

  try {
    resultBox.innerHTML = '<div class="markdown-body"></div>';
    const renderer = createMarkdownRenderer(resultBox.querySelector(".markdown-body"));

    await streamGenerate(endpoint, body, (chunk) => renderer.append(chunk));
    renderer.finish();

    if (!renderer.text.trim()) {
      resultBox.innerHTML = '<div class="result-error">生成结果为空，请重试。</div>';
    } else {
      panel._lastText = renderer.text;
      showToast("生成完成");
    }
  } catch (err) {
    console.error(err);
    resultBox.innerHTML = `<div class="result-error">生成失败：${err.message}</div>`;
    showToast("生成失败，请检查后端服务", true);
  } finally {
    // 恢复状态
    button.disabled = false;
    button.querySelector("span").textContent = originalLabel;
    inputs().forEach((i) => (i.disabled = false));
    segments.forEach((s) => s.enable());
  }
}

// ---------------------------------------------------------------------------
// 绑定事件
// ---------------------------------------------------------------------------
for (const panel of Object.values(panels)) {
  panel.button.addEventListener("click", () => runGenerate(panel));

  panel.copyBtn.addEventListener("click", async () => {
    const text = panel._lastText;
    if (!text) {
      showToast("暂无可复制的内容", true);
      return;
    }
    try {
      await navigator.clipboard.writeText(text);
      showToast("已复制到剪贴板");
    } catch {
      // 兼容非 https 环境
      const ta = document.createElement("textarea");
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
      showToast("已复制到剪贴板");
    }
  });

  panel.exportBtn.addEventListener("click", () => {
    const text = panel._lastText;
    if (!text) {
      showToast("暂无可导出的内容", true);
      return;
    }
    // 以主题命名文件
    const topic = panel.buildBody().topic || "AI生成内容";
    exportTxt(`${topic}_${panel.filename}`, text);
    showToast("已导出 txt 文件");
  });
}

// marked 配置
if (window.marked) {
  marked.setOptions({
    breaks: true,
    gfm: true,
  });
}
