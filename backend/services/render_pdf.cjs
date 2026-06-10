const puppeteer = require('puppeteer')

function readStdin() {
  return new Promise((resolve, reject) => {
    let data = ''
    process.stdin.setEncoding('utf8')
    process.stdin.on('data', (chunk) => {
      data += chunk
    })
    process.stdin.on('end', () => resolve(data))
    process.stdin.on('error', reject)
  })
}

async function main() {
  const html = await readStdin()
  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'],
  })

  try {
    const page = await browser.newPage()
    // height:1 prevents Chrome from inflating <html> to viewport height,
    // so scrollHeight accurately reflects the actual rendered content height.
    await page.setViewport({
      width: 794,
      height: 1,
      deviceScaleFactor: 1,
    })
    await page.setContent(html, {
      waitUntil: ['load', 'domcontentloaded'],
    })

    let contentHeight = await page.evaluate(
      () => document.documentElement.scrollHeight
    )

    // Cap at A4 height in pixels (297mm ≈ 1122px at 96dpi)
    const a4Height = 1122

    // If content overflows A4 height, zoom it down to fit on a single page
    if (contentHeight > a4Height) {
      // Zoom down (cap min scale at 0.85 to keep text readable)
      const scale = Math.max(0.85, a4Height / contentHeight)
      await page.evaluate((s) => {
        document.body.style.zoom = s
      }, scale)

      // Re-measure content height after scaling
      contentHeight = await page.evaluate(
        () => document.documentElement.scrollHeight
      )
    }

    const pdfHeight = Math.min(contentHeight, a4Height)

    const pdf = await page.pdf({
      width: '210mm',
      height: `${pdfHeight}px`,
      margin: { top: '0', right: '0', bottom: '0', left: '0' },
      printBackground: true,
      preferCSSPageSize: false,
    })

    process.stdout.write(pdf)
  } finally {
    await browser.close()
  }
}

main().catch((error) => {
  process.stderr.write(`${error?.stack || error}\n`)
  process.exit(1)
})
