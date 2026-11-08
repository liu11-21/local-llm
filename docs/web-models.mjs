export const models = {
  "Qwen2.5-0.5B-Instruct-q4f32_1-MLC": { name: "Qwen 2.5 · 0.5B", description: "適合先試繁體中文問答。" },
  "SmolLM2-360M-Instruct-q4f32_1-MLC": { name: "SmolLM2 · 360M", description: "較輕量，適合英文短問答。" },
};

export async function openModel(id, progress, signal) {
  const { CreateWebWorkerMLCEngine } = await import("./engine.mjs");
  signal?.throwIfAborted();
  const worker = new Worker(new URL("./engine.mjs", import.meta.url), { type: "module" });
  let abort;
  try {
    const stopped = new Promise((_, reject) => {
      abort = () => reject(signal.reason);
      signal?.addEventListener("abort", abort, { once: true });
      worker.addEventListener("error", () => reject(new Error("無法啟動本機推論引擎。")), { once: true });
    });
    const engine = await Promise.race([CreateWebWorkerMLCEngine(worker, id, { initProgressCallback: progress }), stopped]);
    return { engine, close: () => worker.terminate() };
  } catch (error) {
    worker.terminate();
    throw error;
  } finally {
    signal?.removeEventListener("abort", abort);
  }
}

export const webGPU = (async () => {
  try { return Boolean(await navigator.gpu?.requestAdapter()); }
  catch { return false; }
})();
