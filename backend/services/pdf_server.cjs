/**
 * pdf_server.cjs — Persistent Puppeteer PDF HTTP server
 *
 * Keeps ONE Chromium browser instance alive for the lifetime of the process.
 * Handles POST / with raw HTML body → returns raw PDF bytes.
 * Listens on 127.0.0.1:PDF_SERVER_PORT (default 9009).
 *
 * Benefits vs one-shot subprocess:
 *  - No browser cold-start per request (saves 3–8s each call)
 *  - No subprocess spawn overhead
 *  - Pages are created/closed per request; browser stays warm
 */

'use strict'

const http = require('http')
const puppeteer = require('puppeteer')

const PORT = parseInt(process.env.PDF_SERVER_PORT || '9009', 10)
const HOST = '127.0.0.1'

// A4 height in pixels at 96 dpi (297 mm)
const A4_HEIGHT_PX = 1122

let browser = null

// ── Browser lifecycle ─────────────────────────────────────────────────────────

async function getBrowser() {
  if (browser && browser.connected) return browser

  const executablePath = process.env.PUPPETEER_EXECUTABLE_PATH || undefined

  browser = await puppeteer.launch({
    headless: 'new',
    executablePath,           // uses system Chromium in Docker; auto-detects locally
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-dev-shm-usage',
      '--disable-gpu',
      '--disable-extensions',
      '--disable-background-networking',
      '--disable-sync',
      '--no-first-run',
      '--font-render-hinting=none',  // faster font rendering
    ],
  })

  browser.on('disconnected', () => {
    // Browser crashed — clear the reference so next request relaunches it
    browser = null
    console.error('[pdf-server] Browser disconnected — will relaunch on next request')
  })

  console.log('[pdf-server] Browser launched')
  return browser
}

// ── PDF rendering ─────────────────────────────────────────────────────────────

async function renderPdf(html) {
  const b = await getBrowser()
  const page = await b.newPage()

  try {
    // height:1 prevents Chrome from inflating <html> to viewport height
    await page.setViewport({ width: 794, height: 1, deviceScaleFactor: 1 })

    await page.setContent(html, {
      // 'domcontentloaded' only — do NOT wait for external resources (fonts, images)
      // This prevents hanging when the server has no internet access
      waitUntil: 'domcontentloaded',
      timeout: 15000,
    })

    // Small settle time to let CSS paint (no network wait needed)
    await new Promise(r => setTimeout(r, 150))

    let contentHeight = await page.evaluate(
      () => document.documentElement.scrollHeight
    )

    // If content overflows A4 height, zoom it down to fit on a single page
    if (contentHeight > A4_HEIGHT_PX) {
      const scale = Math.max(0.85, A4_HEIGHT_PX / contentHeight)
      await page.evaluate((s) => { document.body.style.zoom = s }, scale)
      contentHeight = await page.evaluate(
        () => document.documentElement.scrollHeight
      )
    }

    const pdfHeight = Math.min(contentHeight, A4_HEIGHT_PX)

    const pdf = await page.pdf({
      width: '210mm',
      height: `${pdfHeight}px`,
      margin: { top: '0', right: '0', bottom: '0', left: '0' },
      printBackground: true,
      preferCSSPageSize: false,
      timeout: 20000,
    })

    return pdf
  } finally {
    await page.close()
  }
}

// ── HTTP server ───────────────────────────────────────────────────────────────

const server = http.createServer(async (req, res) => {
  if (req.method !== 'POST' || req.url !== '/') {
    res.writeHead(405)
    res.end('Method Not Allowed')
    return
  }

  // Read raw HTML body
  const chunks = []
  req.on('data', chunk => chunks.push(chunk))
  req.on('end', async () => {
    const html = Buffer.concat(chunks).toString('utf8')

    try {
      const pdf = await renderPdf(html)
      res.writeHead(200, {
        'Content-Type': 'application/pdf',
        'Content-Length': pdf.length,
      })
      res.end(pdf)
    } catch (err) {
      console.error('[pdf-server] Render error:', err?.message || err)
      // Force browser restart on next request if it errored badly
      try { await browser?.close() } catch (_) {}
      browser = null
      res.writeHead(500, { 'Content-Type': 'text/plain' })
      res.end(`PDF render error: ${err?.message || String(err)}`)
    }
  })
})

// ── Startup ───────────────────────────────────────────────────────────────────

async function start() {
  // Eagerly launch browser so first request has no cold-start
  try {
    await getBrowser()
  } catch (err) {
    console.error('[pdf-server] Could not pre-launch browser:', err?.message)
    // Non-fatal — browser will be retried on first request
  }

  server.listen(PORT, HOST, () => {
    // Signal to Python that the server is ready
    process.stdout.write(`READY:${PORT}\n`)
    console.log(`[pdf-server] Listening on http://${HOST}:${PORT}`)
  })
}

// Graceful shutdown
async function shutdown() {
  console.log('[pdf-server] Shutting down')
  server.close()
  if (browser) {
    await browser.close().catch(() => {})
  }
  process.exit(0)
}

process.on('SIGTERM', shutdown)
process.on('SIGINT', shutdown)

start().catch(err => {
  console.error('[pdf-server] Fatal startup error:', err)
  process.exit(1)
})
