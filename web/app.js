const state = {
  result: null,
  sessionId: "",
  view: "preview",
  zoom: 1,
  status: null,
  busy: false,
};

const $ = (id) => document.getElementById(id);
const promptEl = $("prompt");
const kindEl = $("kind");
const themeEl = $("theme");
const generateButton = $("generateButton");

document.addEventListener("DOMContentLoaded", () => {
  bindEvents();
  loadStatus();
  loadSessions();
  const requestedSession = new URLSearchParams(window.location.search).get("session");
  if (requestedSession) loadSession(requestedSession);
});

function bindEvents() {
  generateButton.addEventListener("click", generate);
  promptEl.addEventListener("keydown", (event) => {
    if (event.ctrlKey && event.key === "Enter") generate();
  });
  document.querySelectorAll(".example-card").forEach((card) => {
    card.addEventListener("click", () => {
      promptEl.value = card.dataset.prompt;
      kindEl.value = card.dataset.kind;
      promptEl.focus();
    });
  });
  $("newSession").addEventListener("click", resetSession);
  $("refreshStatus").addEventListener("click", loadStatus);
  $("historyJump").addEventListener("click", () => $("historySection").scrollIntoView({ behavior: "smooth" }));
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => switchTab(tab.dataset.tab));
  });
  $("zoomIn").addEventListener("click", () => setZoom(state.zoom + 0.1));
  $("zoomOut").addEventListener("click", () => setZoom(state.zoom - 0.1));
  $("downloadButton").addEventListener("click", (event) => {
    event.stopPropagation();
    $("downloadMenu").classList.toggle("open");
  });
  document.addEventListener("click", () => $("downloadMenu").classList.remove("open"));
  $("downloadMenu").addEventListener("click", (event) => {
    const format = event.target.dataset.format;
    if (format) download(format);
  });
  $("copyButton").addEventListener("click", copyCurrent);
  $("copyCode").addEventListener("click", copyCode);
}

async function loadStatus() {
  try {
    const response = await fetch("/api/status");
    if (!response.ok) throw new Error("状态接口失败");
    state.status = await response.json();
    $("statusDot").classList.toggle("online", Boolean(state.status.llm_ready));
    $("modelStatus").textContent = state.status.llm_ready
      ? `${state.status.provider} · ${state.status.model}`
      : "离线模板模式";
    $("skillCount").textContent = state.status.skills?.length || 0;
    $("mcpCount").textContent = state.status.mcp?.servers?.filter((item) => item.enabled).length || 0;
    $("skillChips").innerHTML = "";
    (state.status.skills || []).forEach((skill) => {
      const chip = document.createElement("span");
      chip.textContent = skill.name;
      chip.title = skill.description;
      $("skillChips").appendChild(chip);
    });
    renderHistory(state.status.sessions || []);
    if (!state.status.llm_ready) {
      $("modeHintText").textContent = "离线模板已启用；配置模型后可处理任意题目";
    }
  } catch (error) {
    $("statusDot").classList.remove("online");
    $("modelStatus").textContent = "服务未连接";
    toast(error.message, true);
  }
}

async function loadSessions() {
  try {
    const response = await fetch("/api/sessions");
    if (!response.ok) return;
    const data = await response.json();
    renderHistory(data.sessions || []);
  } catch (_) {
    // Status request will surface the connection problem.
  }
}

function renderHistory(sessions) {
  const list = $("historyList");
  list.innerHTML = "";
  $("historyCount").textContent = sessions.length;
  if (!sessions.length) {
    list.innerHTML = '<p class="empty-small">还没有生成记录</p>';
    return;
  }
  sessions.forEach((session) => {
    const button = document.createElement("button");
    button.className = "history-item";
    button.dataset.id = session.id;
    const icon = kindGlyph(session.kind);
    const date = formatDate(session.updated_at);
    button.innerHTML = `
      <span class="h-icon">${icon}</span>
      <span><span class="h-title"></span><span class="h-meta">${escapeHtml(date)}</span></span>
      <span class="h-kind">${escapeHtml(session.kind || "")}</span>`;
    button.querySelector(".h-title").textContent = session.title || "未命名图表";
    button.addEventListener("click", () => loadSession(session.id));
    list.appendChild(button);
  });
}

async function loadSession(id) {
  if (state.busy) return;
  try {
    const response = await fetch(`/api/session?id=${encodeURIComponent(id)}`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "会话加载失败");
    state.sessionId = data.id;
    state.result = {
      session_id: data.id,
      title: data.title,
      prompt: data.prompt,
      diagram: data.diagram,
      svg: data.svg,
      mermaid: data.mermaid,
      summary: data.summary,
      trace: data.trace || [],
      todos: data.todos || [],
      warnings: data.warnings || [],
    };
    promptEl.value = data.prompt || "";
    kindEl.value = data.kind || data.diagram?.kind || "auto";
    themeEl.value = data.theme || data.diagram?.theme || "ocean";
    displayResult(state.result);
    updateSessionHint();
    document.querySelectorAll(".history-item").forEach((item) => item.classList.toggle("active", item.dataset.id === id));
    toast("已载入历史会话");
  } catch (error) {
    toast(error.message, true);
  }
}

async function generate() {
  if (state.busy) return;
  const prompt = promptEl.value.trim();
  if (!prompt) {
    promptEl.focus();
    toast("请先输入题目信息", true);
    return;
  }
  setBusy(true);
  $("emptyCanvas").classList.add("hidden");
  $("diagramViewport").classList.add("hidden");
  $("codeView").classList.add("hidden");
  $("loadingState").classList.remove("hidden");
  $("loadingTitle").textContent = "正在理解题目...";
  $("loadingDetail").textContent = "代理会先规划，再加载技能并调用绘图工具";
  $("liveBadge").textContent = "RUNNING";
  $("liveBadge").className = "live-badge running";
  $("traceList").innerHTML = loadingTrace();

  const stages = [
    ["正在选择图种与建模角色...", "抽取参与者、对象、状态和关系"],
    ["正在组织图表规格...", "建立节点、关系、边界与说明"],
    ["正在渲染 SVG...", "生成自包含矢量图和 Mermaid 源码"],
    ["正在执行结构自检...", "检查孤立节点、悬空关系与语义"],
  ];
  let stage = 0;
  const timer = setInterval(() => {
    stage = Math.min(stage + 1, stages.length - 1);
    $("loadingTitle").textContent = stages[stage][0];
    $("loadingDetail").textContent = stages[stage][1];
  }, 1600);

  try {
    const response = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        prompt,
        kind: kindEl.value,
        theme: themeEl.value,
        session_id: state.sessionId || "",
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "生成失败");
    state.result = data;
    state.sessionId = data.session_id;
    displayResult(data);
    updateSessionHint();
    await loadSessions();
    document.querySelectorAll(".history-item").forEach((item) => item.classList.toggle("active", item.dataset.id === state.sessionId));
    toast("图表已生成并保存");
  } catch (error) {
    $("loadingState").classList.add("hidden");
    if (!state.result) $("emptyCanvas").classList.remove("hidden");
    else $("diagramViewport").classList.remove("hidden");
    toast(error.message, true);
  } finally {
    clearInterval(timer);
    setBusy(false);
  }
}

function displayResult(data) {
  $("loadingState").classList.add("hidden");
  $("emptyCanvas").classList.add("hidden");
  $("diagramTitle").textContent = data.title || data.diagram?.title || "未命名图表";
  $("diagramPaper").innerHTML = data.svg || "";
  $("diagramViewport").classList.remove("hidden");
  $("downloadButton").disabled = false;
  $("copyButton").disabled = false;
  $("summaryBox").classList.remove("hidden");
  $("summaryText").textContent = data.summary || "图表已生成。";
  $("liveBadge").textContent = "DONE";
  $("liveBadge").className = "live-badge done";
  $("footerInfo").textContent = `${kindLabel(data.diagram?.kind)} · ${data.diagram?.nodes?.length || 0} 个节点 · ${data.diagram?.edges?.length || 0} 条关系`;
  const warnings = data.warnings || [];
  $("warningInfo").textContent = warnings.length ? `${warnings.length} 条建模提示` : "";
  renderTrace(data.trace || []);
  renderPlan(data.todos || []);
  switchTab("preview");
  requestAnimationFrame(fitDiagram);
}

function switchTab(view) {
  state.view = view;
  document.querySelectorAll(".tab").forEach((tab) => tab.classList.toggle("active", tab.dataset.tab === view));
  $("diagramViewport").classList.toggle("hidden", view !== "preview" || !state.result);
  $("emptyCanvas").classList.toggle("hidden", Boolean(state.result));
  $("codeView").classList.toggle("hidden", view === "preview" || !state.result);
  if (view === "mermaid") {
    $("codeLabel").textContent = "MERMAID";
    $("codeContent").textContent = state.result?.mermaid || "";
  }
  if (view === "spec") {
    $("codeLabel").textContent = "DIAGRAM SPEC · JSON";
    $("codeContent").textContent = JSON.stringify(state.result?.diagram || {}, null, 2);
  }
}

function setZoom(value) {
  state.zoom = Math.max(0.45, Math.min(1.8, Number(value.toFixed(2))));
  $("zoomValue").textContent = `${Math.round(state.zoom * 100)}%`;
  const svg = $("diagramPaper").querySelector("svg");
  if (!svg) return;
  const baseWidth = Number(svg.dataset.baseWidth || svg.getAttribute("width")) || 1200;
  const baseHeight = Number(svg.dataset.baseHeight || svg.getAttribute("height")) || 800;
  svg.dataset.baseWidth = String(baseWidth);
  svg.dataset.baseHeight = String(baseHeight);
  svg.style.width = `${baseWidth * state.zoom}px`;
  svg.style.height = `${baseHeight * state.zoom}px`;
}

function fitDiagram() {
  const viewport = $("diagramViewport");
  const svg = $("diagramPaper").querySelector("svg");
  if (!viewport || !svg || viewport.classList.contains("hidden")) return;
  const width = Number(svg.getAttribute("width")) || 1200;
  const height = Number(svg.getAttribute("height")) || 800;
  const widthFit = (viewport.clientWidth - 72) / width;
  const heightFit = (viewport.clientHeight - 72) / height;
  const fit = Math.min(1, widthFit, Math.max(0.55, heightFit));
  setZoom(Math.max(0.45, fit));
}

function renderTrace(trace) {
  const list = $("traceList");
  list.innerHTML = "";
  if (!trace.length) {
    list.innerHTML = '<div class="trace-empty"><span class="trace-glyph">⌁</span><p>本次运行没有轨迹记录。</p></div>';
    return;
  }
  trace.forEach((item) => {
    const el = document.createElement("div");
    el.className = `trace-item ${item.type || "tool"}`;
    el.innerHTML = `
      <span class="trace-icon">${traceGlyph(item.type)}</span>
      <div><div class="trace-title"><span></span><time>${escapeHtml(item.time || "")}</time></div>
      <div class="trace-detail"></div></div>`;
    el.querySelector(".trace-title span").textContent = item.title || "";
    el.querySelector(".trace-detail").textContent = compactText(item.detail || "");
    list.appendChild(el);
  });
}

function renderPlan(todos) {
  const list = $("planList");
  list.innerHTML = "";
  const done = todos.filter((item) => item.status === "completed").length;
  $("planProgress").textContent = `${done} / ${todos.length}`;
  if (!todos.length) {
    list.innerHTML = '<p class="empty-small">暂无步骤</p>';
    return;
  }
  todos.forEach((item) => {
    const el = document.createElement("div");
    el.className = `plan-item ${item.status}`;
    const check = item.status === "completed" ? "✓" : item.status === "in_progress" ? "•" : "";
    el.innerHTML = `<span class="plan-check">${check}</span><span></span>`;
    el.querySelector("span:last-child").textContent = item.text;
    list.appendChild(el);
  });
}

function setBusy(value) {
  state.busy = value;
  generateButton.disabled = value;
  generateButton.querySelector(".button-label").textContent = value ? "代理正在工作…" : (state.sessionId ? "继续修改并生成" : "生成图表");
}

function updateSessionHint() {
  if (state.sessionId) {
    $("modeHintText").textContent = "正在当前会话中迭代；修改描述后会生成新版本";
    generateButton.querySelector(".button-label").textContent = "继续修改并生成";
  } else {
    $("modeHintText").textContent = state.status?.llm_ready ? "首次生成会创建新会话" : "离线模板已启用；配置模型后可处理任意题目";
    generateButton.querySelector(".button-label").textContent = "生成图表";
  }
}

function resetSession() {
  if (state.busy) return;
  state.sessionId = "";
  state.result = null;
  promptEl.value = "";
  kindEl.value = "auto";
  themeEl.value = "ocean";
  $("diagramTitle").textContent = "等待创建图表";
  $("diagramPaper").innerHTML = "";
  $("emptyCanvas").classList.remove("hidden");
  $("diagramViewport").classList.add("hidden");
  $("codeView").classList.add("hidden");
  $("loadingState").classList.add("hidden");
  $("summaryBox").classList.add("hidden");
  $("zoomValue").textContent = "100%";
  state.zoom = 1;
  $("traceList").innerHTML = '<div class="trace-empty"><span class="trace-glyph">⌁</span><p>生成后，这里会展示计划、工具调用与校验结果。</p></div>';
  $("planList").innerHTML = '<p class="empty-small">暂无步骤</p>';
  $("planProgress").textContent = "0 / 0";
  $("downloadButton").disabled = true;
  $("copyButton").disabled = true;
  $("liveBadge").textContent = "IDLE";
  $("liveBadge").className = "live-badge";
  $("footerInfo").textContent = "SVG 本地渲染 · 不依赖外部 CDN";
  $("warningInfo").textContent = "";
  document.querySelectorAll(".history-item").forEach((item) => item.classList.remove("active"));
  switchTab("preview");
  updateSessionHint();
  promptEl.focus();
}

async function download(format) {
  if (!state.result) return;
  const base = slugify(state.result.title || "plant-agent-diagram");
  if (format === "svg") {
    downloadBlob(state.result.svg, `${base}.svg`, "image/svg+xml");
  } else if (format === "mmd") {
    downloadBlob(state.result.mermaid, `${base}.mmd`, "text/plain");
  } else if (format === "json") {
    downloadBlob(JSON.stringify(state.result.diagram, null, 2), `${base}.json`, "application/json");
  } else if (format === "png") {
    try {
      await downloadPng(state.result.svg, `${base}.png`);
    } catch (error) {
      toast(`PNG 导出失败：${error.message}`, true);
    }
  }
  $("downloadMenu").classList.remove("open");
}

function downloadBlob(content, filename, type) {
  const blob = new Blob([content], { type: `${type};charset=utf-8` });
  triggerDownload(URL.createObjectURL(blob), filename);
  setTimeout(() => URL.revokeObjectURL(blob), 3000);
  toast(`已导出 ${filename}`);
}

async function downloadPng(svgText, filename) {
  const parser = new DOMParser();
  const svgDoc = parser.parseFromString(svgText, "image/svg+xml");
  const svg = svgDoc.documentElement;
  const width = Number(svg.getAttribute("width")) || 1200;
  const height = Number(svg.getAttribute("height")) || 800;
  const scale = 2;
  const blob = new Blob([svgText], { type: "image/svg+xml;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const image = new Image();
  await new Promise((resolve, reject) => {
    image.onload = resolve;
    image.onerror = () => reject(new Error("SVG 渲染失败"));
    image.src = url;
  });
  const canvas = document.createElement("canvas");
  canvas.width = width * scale;
  canvas.height = height * scale;
  const context = canvas.getContext("2d");
  context.fillStyle = "#ffffff";
  context.fillRect(0, 0, canvas.width, canvas.height);
  context.drawImage(image, 0, 0, canvas.width, canvas.height);
  URL.revokeObjectURL(url);
  const pngBlob = await new Promise((resolve) => canvas.toBlob(resolve, "image/png"));
  const pngUrl = URL.createObjectURL(pngBlob);
  triggerDownload(pngUrl, filename);
  setTimeout(() => URL.revokeObjectURL(pngUrl), 3000);
  toast(`已导出 ${filename}`);
}

function triggerDownload(url, filename) {
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
}

async function copyCurrent() {
  if (!state.result) return;
  const text = state.view === "mermaid" ? state.result.mermaid : JSON.stringify(state.result.diagram, null, 2);
  await copyText(text, state.view === "mermaid" ? "已复制 Mermaid" : "已复制规格 JSON");
}

async function copyCode() {
  const text = $("codeContent").textContent;
  await copyText(text, "代码已复制");
}

async function copyText(text, message) {
  try {
    await navigator.clipboard.writeText(text);
    toast(message);
  } catch (_) {
    toast("浏览器未授予剪贴板权限", true);
  }
}

function loadingTrace() {
  return `
    <div class="trace-item plan"><span class="trace-icon">1</span><div><div class="trace-title"><span>建立建模计划</span><time>now</time></div><div class="trace-detail">解析题目、选择图表与知识技能</div></div></div>
    <div class="trace-item tool"><span class="trace-icon">2</span><div><div class="trace-title"><span>构建 DiagramSpec</span><time>now</time></div><div class="trace-detail">组织节点、关系、分组和假设说明</div></div></div>
    <div class="trace-item diagram"><span class="trace-icon">3</span><div><div class="trace-title"><span>渲染与自检</span><time>now</time></div><div class="trace-detail">生成 SVG、Mermaid，并检查结构风险</div></div></div>`;
}

function traceGlyph(type = "") {
  return { plan: "P", skill: "S", tool: "T", mcp: "M", model: "AI", diagram: "D", done: "✓", warning: "!" }[type] || "·";
}

function kindGlyph(kind = "") {
  return { class: "◈", sequence: "⇢", usecase: "◎", er: "▤", state: "◉", activity: "◇", component: "⬡", deployment: "▦", dfd: "⇄", flow: "→" }[kind] || "◇";
}

function kindLabel(kind = "") {
  return { class: "类图", sequence: "时序图", usecase: "用例图", er: "ER 图", state: "状态图", activity: "活动图", component: "组件图", deployment: "部署图", dfd: "数据流图", flow: "流程图" }[kind] || "图表";
}

function compactText(text) {
  return String(text || "").replace(/\s+/g, " ").trim().slice(0, 500);
}

function formatDate(value) {
  if (!value) return "刚刚";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value.slice(0, 16).replace("T", " ");
  return date.toLocaleString("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });
}

function slugify(text) {
  return String(text).trim().replace(/[\\/:*?"<>|]/g, "-").replace(/\s+/g, "-").slice(0, 60) || "diagram";
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = String(text || "");
  return div.innerHTML;
}

function toast(message, error = false) {
  const el = $("toast");
  el.textContent = message;
  el.className = `toast show${error ? " error" : ""}`;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => { el.className = "toast"; }, 3000);
}
