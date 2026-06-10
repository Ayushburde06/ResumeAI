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

    await page.addStyleTag({
      content: `
        html, body {
          font-size: 11px !important;
          line-height: 1.35 !important;
        }
        section, div { page-break-inside: avoid; }
      `
    })

    const pdf = await page.pdf({
      format: 'A4',
      margin: { top: '8mm', right: '8mm', bottom: '8mm', left: '8mm' },
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
