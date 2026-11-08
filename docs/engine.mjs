import { CreateWebWorkerMLCEngine, WebWorkerMLCEngineHandler } from
  "https://cdn.jsdelivr.net/npm/@mlc-ai/web-llm@0.2.87/lib/index.js";

if (typeof WorkerGlobalScope !== "undefined" && self instanceof WorkerGlobalScope) {
  const handler = new WebWorkerMLCEngineHandler();
  self.onmessage = (event) => handler.onmessage(event);
}

export { CreateWebWorkerMLCEngine };
