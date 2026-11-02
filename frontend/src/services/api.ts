import {
  StockSearchResult,
  StockQuote,
  TopUniverseItem,
  MarketBreadth,
  ChartResponse,
  ScreenerCandidateItem,
  CorridorForecast,
  AISignalResponse,
  PortfolioSummaryResponse,
  PositionItem,
  TradeItem,
  SystemHealth
} from '../types'

const BASE_URL = '/api'

async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  })

  if (!res.ok) {
    let errorDetail = res.statusText
    try {
      const errJson = await res.json()
      errorDetail = errJson.detail || errorDetail
    } catch {
      // ignore
    }
    throw new Error(`API Error (${res.status}): ${errorDetail}`)
  }

  return res.json()
}

export const api = {
  // Stocks & Universe
  searchStocks: (query: string, limit = 20) =>
    request<StockSearchResult[]>(`/stocks/search?q=${encodeURIComponent(query)}&limit=${limit}`),

  getStockQuote: (symbol: string) =>
    request<StockQuote>(`/stocks/quote/${encodeURIComponent(symbol)}`),

  getTopUniverse: (limit = 300) =>
    request<TopUniverseItem[]>(`/stocks/universe/top300?limit=${limit}`),

  getMarketBreadth: () =>
    request<MarketBreadth>('/stocks/breadth'),

  // Candlesticks Charts
  getChartCandles: (symbol: string, timeframe = '1m', limit = 500) =>
    request<ChartResponse>(`/charts/${encodeURIComponent(symbol)}?timeframe=${timeframe}&limit=${limit}&auto_backfill=true`),

  // AI Quantitative Intelligence
  getScreenerWatchlist: () =>
    request<ScreenerCandidateItem[]>('/ai/screener/focus'),

  getCorridorForecast: (symbol: string) =>
    request<CorridorForecast>(`/ai/forecast/corridor/${encodeURIComponent(symbol)}`),

  getAISignal: (symbol: string) =>
    request<AISignalResponse>(`/ai/signal/${encodeURIComponent(symbol)}`),

  // Trading & Risk Governance
  getPortfolioSummary: () =>
    request<PortfolioSummaryResponse>('/trading/portfolio'),

  getActivePositions: () =>
    request<PositionItem[]>('/trading/positions'),

  getTradeHistory: (limit = 50) =>
    request<TradeItem[]>(`/trading/trades?limit=${limit}`),

  placeOrder: (order: { symbol: string; direction: 'BUY' | 'SELL'; quantity?: number; price?: number }) =>
    request<any>('/trading/order', {
      method: 'POST',
      body: JSON.stringify(order),
    }),

  closePosition: (symbol: string) =>
    request<any>(`/trading/close/${encodeURIComponent(symbol)}`, {
      method: 'POST',
    }),

  // System & Engine Operations
  getSystemHealth: () =>
    request<SystemHealth>('/system/health'),

  triggerSync: (mode: 'daily' | 'hybrid' | 'refresh_ranking') =>
    request<{ status: string; mode: string; message: string }>(`/system/sync?mode=${mode}`, {
      method: 'POST',
    }),
}
