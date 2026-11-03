type MessageHandler = (data: any) => void

class WebSocketService {
  private liveWs: WebSocket | null = null
  private tradesWs: WebSocket | null = null
  private liveHandlers: Set<MessageHandler> = new Set()
  private tradeHandlers: Set<MessageHandler> = new Set()
  private pingInterval: any = null
  private isConnected = false

  public connect() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host // Uses Vite proxy in development

    // 1. Live Ticks Stream
    try {
      this.liveWs = new WebSocket(`${protocol}//${host}/ws/live`)
      
      this.liveWs.onopen = () => {
        this.isConnected = true
        this.startHeartbeat()
      }

      this.liveWs.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data)
          this.liveHandlers.forEach((handler) => handler(payload))
        } catch (e) {
          console.debug('Failed to parse WebSocket message:', e)
        }
      }

      this.liveWs.onclose = () => {
        this.isConnected = false
        setTimeout(() => this.connect(), 3000)
      }
    } catch (e) {
      console.warn('Live WebSocket connection failed:', e)
    }

    // 2. Trades & Alert Events Stream
    try {
      this.tradesWs = new WebSocket(`${protocol}//${host}/ws/trades`)

      this.tradesWs.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data)
          this.tradeHandlers.forEach((handler) => handler(payload))
        } catch (e) {
          console.debug('Failed to parse Trade WS message:', e)
        }
      }

      this.tradesWs.onclose = () => {
        setTimeout(() => this.connect(), 3000)
      }
    } catch (e) {
      console.warn('Trades WebSocket connection failed:', e)
    }
  }

  private startHeartbeat() {
    if (this.pingInterval) clearInterval(this.pingInterval)
    this.pingInterval = setInterval(() => {
      if (this.liveWs && this.liveWs.readyState === WebSocket.OPEN) {
        this.liveWs.send(JSON.stringify({ action: 'ping' }))
      }
      if (this.tradesWs && this.tradesWs.readyState === WebSocket.OPEN) {
        this.tradesWs.send(JSON.stringify({ action: 'ping' }))
      }
    }, 15000)
  }

  public subscribeLive(handler: MessageHandler) {
    this.liveHandlers.add(handler)
    return () => {
      this.liveHandlers.delete(handler)
    }
  }

  public subscribeTrades(handler: MessageHandler) {
    this.tradeHandlers.add(handler)
    return () => {
      this.tradeHandlers.delete(handler)
    }
  }

  public subscribeSymbol(symbol: string) {
    if (this.liveWs && this.liveWs.readyState === WebSocket.OPEN) {
      this.liveWs.send(JSON.stringify({ action: 'subscribe', symbols: [symbol] }))
    }
  }

  public getStatus() {
    return this.isConnected
  }
}

export const wsService = new WebSocketService()

