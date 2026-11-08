const ui = Object.fromEntries(Array.from(document.querySelectorAll("[id]"), (element) => [element.id, element]));
const encoder = new TextEncoder();
const turns = [];
const models = {
  "Qwen2.5-0.5B-Instruct-q4f32_1-MLC": { name: "Qwen 2.5 · 0.5B", description: "適合先試繁體中文問答。" },
  "SmolLM2-360M-Instruct-q4f32_1-MLC": { name: "SmolLM2 · 360M", description: "較輕量，適合英文短問答。" },
};

let engine;
let worker;
let activeModel;
let gpuReady = false;
let loading = false;
let generating = false;
let stopping = false;

function status(message, error = false) {
  ui.status.textContent = message;
  ui.status.dataset.error = String(error);
}

function refresh() {
  const busy = loading || generating;
  const modelReady = engine && activeModel === ui.model.value;
  ui.model.disabled = busy;
  ui.load.disabled = busy || !gpuReady || Boolean(modelReady);
  ui.load.textContent = loading ? "載入中…" : modelReady ? "模型已就緒" : "載入模型";
  ui.prompt.disabled = busy || !modelReady;
  ui.prompt.placeholder = modelReady ? "輸入你的訊息…" : "載入模型後輸入訊息…";
  ui.send.disabled = ui.prompt.disabled || !ui.prompt.value.trim();
  ui.stop.hidden = !generating;
  ui.stop.disabled = stopping;
  ui.clear.disabled = busy || turns.length === 0;
  ui.export.disabled = busy || turns.length === 0;
}

function loadingProgress(report) {
  ui.progress.value = Math.min(100, Math.max(0, (report.progress || 0) * 100));
  const message = String(report.text || "");
  const percentage = Math.round(ui.progress.value);
  const phase = /fetch|download/i.test(message) ? "正在下載或讀取快取模型" : "正在準備本機模型";
  const label = `${phase}… ${percentage}%`;
  if (ui.status.textContent !== label) status(label);
}

async function loadModel() {
  if (ui.load.disabled) return;
  const selection = ui.model.value;
  loading = true;
  refresh();
  ui.progress.hidden = false;
  ui.progress.value = 0;
  status("正在載入瀏覽器推論引擎…");
  worker?.terminate();
  engine = worker = activeModel = undefined;

  try {
    const { CreateWebWorkerMLCEngine } = await import("./engine.mjs");
    const currentWorker = new Worker(new URL("./engine.mjs", import.meta.url), { type: "module" });
    worker = currentWorker;
    const workerError = new Promise((_, reject) => {
      currentWorker.addEventListener("error", () => reject(new Error("無法啟動本機推論引擎。")), { once: true });
    });
    engine = await Promise.race([
      CreateWebWorkerMLCEngine(currentWorker, selection, { initProgressCallback: loadingProgress }),
      workerError,
    ]);
    activeModel = selection;
    status(`${models[selection].name} 已就緒`);
  } catch (error) {
    worker?.terminate();
    engine = worker = activeModel = undefined;
    console.error("Model load failed", error);
    status("模型載入失敗。請確認可連線到模型來源，或換較小的模型再試。", true);
  } finally {
    loading = false;
    ui.progress.hidden = true;
    refresh();
    if (engine) ui.prompt.focus();
  }
}

function message(role, label, content) {
  const article = document.createElement("article");
  article.className = "message";
  article.dataset.role = role;
  const author = document.createElement("span");
  author.className = "message-label";
  author.textContent = label;
  const body = document.createElement("p");
  body.textContent = content;
  article.append(author, body);
  ui.thread.append(article);
  return { article, body };
}

function recentMessages(current) {
  const messages = [{ role: "user", content: current }];
  let budget = 5200 - encoder.encode(current).length;
  for (const turn of turns.slice(0, -1).reverse()) {
    if (!turn.completed) continue;
    budget -= encoder.encode(turn.prompt + turn.answer).length;
    if (budget < 0) break;
    messages.unshift({ role: "user", content: turn.prompt }, { role: "assistant", content: turn.answer });
  }
  return messages;
}

async function send(event) {
  event.preventDefault();
  if (ui.send.disabled) return;
  const prompt = ui.prompt.value.trim();
  if (!prompt) return;
  generating = true;
  const turn = { prompt, answer: "", model: models[activeModel].name, completed: false };
  turns.push(turn);
  ui.prompt.value = "";
  ui.empty.hidden = true;
  message("user", "你", prompt);
  const reply = message("assistant", turn.model, "正在產生回答…");
  ui.thread.scrollTop = ui.thread.scrollHeight;
  refresh();

  try {
    const stream = await engine.chat.completions.create({
      messages: recentMessages(prompt),
      stream: true,
      max_tokens: 384,
    });
    for await (const chunk of stream) {
      const token = chunk.choices[0]?.delta?.content;
      if (typeof token !== "string" || !token) continue;
      const atBottom = ui.thread.scrollHeight - ui.thread.clientHeight - ui.thread.scrollTop < 48;
      turn.answer += token;
      reply.body.textContent = turn.answer;
      if (atBottom) ui.thread.scrollTop = ui.thread.scrollHeight;
    }
    turn.completed = Boolean(turn.answer.trim()) && !stopping;
    if (stopping || !turn.completed) {
      const note = document.createElement("small");
      note.textContent = stopping ? "已停止產生" : "模型沒有回傳文字";
      if (!turn.answer) reply.body.textContent = note.textContent;
      else reply.article.append(note);
    }
    ui.announcer.textContent = stopping ? "已停止產生回答。" : "模型已完成回應。";
  } catch (error) {
    console.error("Generation failed", error);
    const note = document.createElement("small");
    note.textContent = stopping ? "已停止產生" : "回答失敗，請縮短訊息或重新載入頁面再試。";
    if (turn.answer) reply.article.append(note);
    else reply.body.textContent = note.textContent;
    ui.announcer.textContent = note.textContent;
  } finally {
    generating = stopping = false;
    refresh();
    ui.prompt.focus();
  }
}

ui.model.addEventListener("change", () => {
  ui["model-description"].textContent = models[ui.model.value].description;
  if (gpuReady) status(ui.model.value === activeModel ? `${models[activeModel].name} 已就緒` : "按「載入模型」開始。");
  refresh();
});
ui.load.addEventListener("click", loadModel);
ui.composer.addEventListener("submit", send);
ui.prompt.addEventListener("input", refresh);
ui.prompt.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey && !event.isComposing && event.keyCode !== 229) {
    event.preventDefault();
    ui.composer.requestSubmit();
  }
});
ui.stop.addEventListener("click", () => {
  if (!generating || stopping) return;
  stopping = true;
  engine.interruptGenerate();
  refresh();
});
ui.clear.addEventListener("click", () => {
  turns.length = 0;
  ui.thread.replaceChildren(ui.empty);
  ui.empty.hidden = false;
  refresh();
  if (!ui.prompt.disabled) ui.prompt.focus();
});
ui.export.addEventListener("click", () => {
  const contents = turns.map((turn) => `你\n${turn.prompt}\n\n${turn.model}\n${turn.answer || "（無文字回答）"}`).join("\n\n---\n\n");
  const url = URL.createObjectURL(new Blob([contents], { type: "text/plain;charset=utf-8" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = `local-llm-${new Date().toISOString().slice(0, 10)}.txt`;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
});

try {
  gpuReady = Boolean(await navigator.gpu?.requestAdapter());
} catch (error) {
  console.error("WebGPU availability check failed", error);
}
status(gpuReady ? "按「載入模型」開始。" : "目前無法使用 WebGPU。請用新版 Chrome 或 Edge，並確認已啟用圖形加速。", !gpuReady);
refresh();
