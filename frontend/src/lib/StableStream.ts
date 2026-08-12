export class StableStream {
  private url: string
  private onChunk: (chunk: string) => void
  private onDone: (finalBuffer: string) => void
  private onError?: (error: Error) => void
  private buffer: string = ''
  private attempts: number = 0
  private maxAttempts: number = 2
  private abortController: AbortController | null = null
  private options: RequestInit

  constructor(
    url: string,
    options: RequestInit,
    onChunk: (chunk: string) => void,
    onDone: (finalBuffer: string) => void,
    onError?: (error: Error) => void
  ) {
    this.url = url
    this.options = options
    this.onChunk = onChunk
    this.onDone = onDone
    this.onError = onError
  }

  public async connect(resumeFrom: number = 0) {
    this.abortController = new AbortController()
    
    const headers = new Headers(this.options.headers)
    if (resumeFrom > 0) {
      headers.set('Last-Event-ID', resumeFrom.toString())
    }

    try {
      const res = await fetch(this.url, {
        ...this.options,
        headers,
        signal: this.abortController.signal
      })

      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`)
      }

      if (!res.body) {
        throw new Error('Response body is null')
      }

      const reader = res.body.getReader()
      const decoder = new TextDecoder()

      while (true) {
        const { done, value } = await reader.read()
        if (done) {
          this.onDone(this.buffer)
          return
        }
        
        const chunk = decoder.decode(value, { stream: true })
        this.buffer += chunk
        this.onChunk(chunk)
      }
    } catch (err: any) {
      if (err.name === 'AbortError') {
        return // Intentionally aborted
      }

      if (this.attempts < this.maxAttempts) {
        this.attempts++
        console.warn(`[StableStream] Connection dropped, reconnecting attempt ${this.attempts}...`)
        await new Promise(resolve => setTimeout(resolve, 1000))
        this.connect(this.buffer.length)
      } else {
        console.error('[StableStream] Max attempts reached, failing gracefully.', err)
        if (this.onError) this.onError(err)
        this.onDone(this.buffer) // Return partial
      }
    }
  }

  public abort() {
    if (this.abortController) {
      this.abortController.abort()
    }
  }
}
