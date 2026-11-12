import { defineConfig, type Plugin } from 'vite'
import react from '@vitejs/plugin-react'
import tailwind from '@tailwindcss/vite'
import { spawn } from 'node:child_process'
import { createInterface } from 'node:readline'
import { createReadStream } from 'node:fs'
import { realpath, stat } from 'node:fs/promises'
import { join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { readFileSync } from 'node:fs'
import { execFileSync } from 'node:child_process'

function previewWorker(port: number): Plugin {
  return {
    name: 'development-only-local-worker',
    configureServer(server) {
      const worker = process.env.LOCALLLM_PREVIEW_DATA && process.env.LOCALLLM_PREVIEW_WORKER
      const args = [worker || fileURLToPath(new URL('../desktop_worker.py', import.meta.url))]
      if (process.env.LOCALLLM_PREVIEW_DATA) args.push('--data', process.env.LOCALLLM_PREVIEW_DATA)
      const child = spawn(process.env.LOCALLLM_PYTHON || 'python', args,
        { windowsHide: true, stdio: ['pipe', 'pipe', 'inherit'] })
      let failed = false
      const queue: Array<(line: string) => void> = []
      const fail = () => {
        failed = true
        for (const respond of queue.splice(0)) respond(JSON.stringify({ ok: false, error: '開發工作程序已停止。' }))
      }
      child.once('exit', fail)
      child.once('error', fail)
      child.stdin.on('error', fail)
      createInterface({ input: child.stdout }).on('line', line => queue.shift()?.(line))
      server.httpServer?.once('close', () => child.stdin.end())
      server.middlewares.use(async (req, res, next) => {
        const output = /^\/__desktop_dev_output\/([a-f0-9]{12}\.(png|webm|flac))$/.exec(req.url ?? '')
        if (output && process.env.LOCALLLM_PREVIEW_DATA) {
          if (req.method !== 'GET' || req.headers.host !== `127.0.0.1:${port}` ||
              (req.headers['sec-fetch-site'] && req.headers['sec-fetch-site'] !== 'same-origin')) {
            res.writeHead(403).end()
            return
          }
          try {
            const directory = join(await realpath(resolve(process.env.LOCALLLM_PREVIEW_DATA)), 'outputs')
            if (await realpath(directory) !== directory) throw Error('Invalid preview directory')
            const file = join(directory, output[1])
            if (await realpath(file) !== file || !(await stat(file)).isFile()) throw Error('Invalid preview asset')
            const types = {png:'image/png', webm:'video/webm', flac:'audio/flac'}
            res.writeHead(200, {'Content-Type':types[output[2] as keyof typeof types], 'Cache-Control':'no-store',
              'X-Content-Type-Options':'nosniff', 'Cross-Origin-Resource-Policy':'same-origin'})
            createReadStream(file).on('error', () => res.destroy()).pipe(res)
          } catch { res.writeHead(404).end() }
          return
        }
        if (req.url !== '/__desktop_dev_rpc') return next()
        if (req.method !== 'POST' || req.headers.host !== `127.0.0.1:${port}`
          || req.headers.origin !== `http://127.0.0.1:${port}` || req.headers['content-type'] !== 'application/json') {
          res.writeHead(403).end()
          return
        }
        let total = 0
        const chunks: Buffer[] = []
        try {
          for await (const chunk of req) {
            if ((total += chunk.length) > 256 * 1024) { res.writeHead(413).end(); return }
            chunks.push(chunk)
          }
          const line = JSON.stringify(JSON.parse(Buffer.concat(chunks).toString('utf8')))
          if (failed || queue.length >= 32) throw new Error('無法連接開發工作程序。')
          queue.push(result => res.writeHead(200, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' }).end(result))
          child.stdin.write(line + '\n')
        } catch {
          res.writeHead(400).end()
        }
      })
    }
  }
}

export default defineConfig(({ mode }) => {
  const version = JSON.parse(readFileSync(new URL('./package.json', import.meta.url), 'utf8')).version
  let commit = 'unknown'
  try { commit = execFileSync('git', ['rev-parse','HEAD'], {cwd:fileURLToPath(new URL('../',import.meta.url)),encoding:'utf8'}).trim() } catch {}
  const preview = mode === 'preview-worker'
  const port = preview && process.env.LOCALLLM_PREVIEW_PORT ? Number(process.env.LOCALLLM_PREVIEW_PORT) : 1420
  return {
    define: {__WORKSPACE_VERSION__:JSON.stringify(version), __WORKSPACE_COMMIT__:JSON.stringify(commit)},
    plugins: [react(), tailwind(), ...(preview ? [previewWorker(port)] : [])],
    server: { host: '127.0.0.1', port, strictPort: true, cors: false },
    clearScreen: false,
    build: { target: 'es2022' }
  }
})
