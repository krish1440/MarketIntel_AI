export interface StockSearchResult {
  symbol: string
  company_name: string
  exchange: string
  token: string
  isin?: string
  is_top_300: boolean
}

export interface StockQuote {
  symbol: string
  company_name: string
  exchange: string
  ltp: number
  change: number
  change_pct: number
  open: number
  high: number
  low: number
  close: number
  volume: number
  vwap?: number | null
  high_52w?: number | null
  low_52w?: number | null
  last_updated?: string
}

export interface TopUniverseItem {
  symbol: string
  company_name: string
  turnover_20d_avg_cr: number
  current_price: number
  change_pct: number
  rank: number
}

export interface MarketBreadth {
  advances: number
  declines: number
  unchanged: number
  total: number
  advance_decline_ratio: number
  timestamp: string
}

export interface CandleItem {
  time: number
  open: number
  high: number
  low: number
  close: number
  volume: number
  vwap?: number | null
}

export interface ChartResponse {
  symbol: string
  timeframe: string
  candles_count: number
  candles: CandleItem[]
}

export interface ScreenerCandidateItem {
  rank: number
  symbol: string
  company_name: string
  sector: string
  turnover_20d_cr: number
  gap_pct: number
  conviction_score: number
}

export interface CorridorForecast {
  symbol: string
  current_price: number
  p05_floor: number
  p25_lower: number
  p50_median: number
  p75_target1: number
  q90_runner_target: number
  volatility_band_pct: number
  forecast_time: string
}

export interface AISignalResponse {
  symbol: string
  action: 'STRONG_BUY' | 'BUY' | 'HOLD' | 'AVOID'
  calibrated_probability: number
  raw_probability: number
  regime: string
  stop_loss_price: number
  target_1_price: number
  target_2_price: number
  risk_reward_ratio: number
  timestamp: string
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

export interface SystemHealth {
  status: string
  timestamp: string
  memory_rss_mb: number
  market: {
    is_market_open: boolean
    session_state: string
    ist_time: string
    weekday: string
  }
  redis_connected: boolean
  lakehouse: {
    base_exists: boolean
    silver_1d_stocks: number
    silver_1m_stocks: number
    gold_features_exists: boolean
  }
  execution: {
    mode: string
    open_positions: number
    circuit_breaker_tripped: boolean
    orchestrator_running: boolean
  }
}
