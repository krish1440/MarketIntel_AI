export interface StockSearchResult {
  symbol: string
  company_name: string
  exchange: string
  token?: string | null
  isin?: string | null
  is_top_300: boolean
}

export interface StockQuote {
  symbol: string
  company_name?: string
  sector?: string
  exchange?: string
  ltp: number
  open?: number
  high?: number
  low?: number
  close?: number
  prev_close?: number
  volume?: number
  vwap?: number | null
  pct_change?: number
  change?: number
  change_pct?: number
  high_52w?: number | null
  low_52w?: number | null
  updated_at?: string
}

export interface TopUniverseItem {
  symbol: string
  company_name?: string
  price?: number
  current_price?: number
  turnover_20d_cr?: number
  turnover_20d_avg_cr?: number
  pct_change?: number
  change_pct?: number
  rank: number
}

export interface MarketBreadth {
  advances: number
  declines: number
  unchanged: number
  adv_dec_ratio?: number
  advance_decline_ratio?: number
  timestamp?: string
}

export interface CandleItem {
  time: number
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export interface ChartCandlesResponse {
  symbol: string
  timeframe: string
  count: number
  candles: CandleItem[]
}

export type ChartResponse = ChartCandlesResponse

export interface CorridorForecast {
  symbol: string
  current_price: number
  p05_floor: number
  p25_lower: number
  p50_median: number
  p75_target1: number
  q90_runner: number
  q90_runner_target?: number
  corridor_width_pct: number
  volatility_band_pct?: number
  asymmetry_ratio: number
}

export interface ScreenerCandidateItem {
  rank: number
  symbol: string
  current_price: number
  rank_score: number
  conviction_score?: number
  action: string
  confidence_pct: number
  turnover_cr: number
  turnover_20d_cr?: number
  gap_pct?: number
  sector?: string
}

export interface AISignalResponse {
  symbol: string
  action: string
  confidence_pct: number
  calibrated_probability?: number
  current_price: number
  recommended_entry: number
  dynamic_stop_loss: number
  stop_loss_price?: number
  target_1: number
  target_1_price?: number
  target_2: number
  target_2_price?: number
  risk_reward_ratio: number
  regime?: string
  generated_at: string
}

export interface PortfolioSummaryResponse {
  initial_capital: number
  current_cash: number
  total_portfolio_value: number
  total_invested: number
  total_unrealized_pnl: number
  total_realized_pnl: number
  total_return_pct: number
  open_positions_count: number
  max_drawdown_pct: number
  daily_pnl_pct: number
  circuit_breaker_tripped: boolean
}

export interface PositionItem {
  symbol: string
  trade_id: string
  entry_time: string
  entry_price: number
  quantity: number
  current_price: number
  allocated_capital: number
  unrealized_pnl: number
  unrealized_pnl_pct: number
  ml_stop_price: number
  ml_target_1: number
  ml_target_2: number
  partial_exit_done: boolean
  highest_price_seen: number
}

export interface TradeItem {
  trade_id: string
  symbol: string
  entry_time: string
  exit_time: string
  holding_days: number
  quantity: number
  entry_price: number
  exit_price: number
  gross_pnl: number
  gross_pnl_pct: number
  total_transaction_frictions: number
  capital_gains_tax: number
  tax_type: string
  net_pnl: number
  net_pnl_pct: number
  exit_trigger: string
}

export interface ManualOrderRequest {
  symbol: string
  direction: 'BUY' | 'SELL'
  quantity?: number
  price?: number
}

export interface ManualOrderResponse {
  order_id: string
  status: string
  symbol: string
  direction: string
  quantity: number
  filled_price: number
  total_value: number
  execution_mode: string
}

export interface SystemHealth {
  status: string
  uptime_seconds: number
  memory_rss_mb: number
  redis_connected: boolean
  duckdb_active: boolean
  lakehouse_records_parity: boolean
  active_background_tasks: number
}

export interface SectorStockItem {
  symbol: string
  company_name: string
  ltp: number
  pct_change: number
  action: string
}

export interface SectorHeatmapItem {
  sector_id: string
  sector_name: string
  avg_change_pct: number
  advances: number
  declines: number
  total_stocks: number
  strong_buys_count: number
  top_stocks: SectorStockItem[]
}
