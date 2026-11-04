import React, { useState, useEffect, useRef } from 'react'
import {
  Search,
  Sun,
  Moon,
  Activity,
  Layers,
  Clock,
  TrendingUp,
  TrendingDown,
  Database,
  Radio,
  Zap,
  CheckCircle2,
  AlertCircle,
  RefreshCw
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { StockQuote, StockSearchResult, SystemHealth, MarketBreadth, AISignalResponse } from '../types'
import { api } from '../services/api'

interface HeaderProps {
  quote: StockQuote | null
  health: SystemHealth | null
  breadth: MarketBreadth | null
  signal: AISignalResponse | null
  activeSymbol: string
  onSelectSymbol: (symbol: string) => void
  onOpenSystemModal: () => void
  onToggleUniverseDrawer: () => void
  onOpenSectorHeatmap?: () => void
  onRefresh?: () => void
  isRefreshing?: boolean
  isWsConnected: boolean
}

export const Header: React.FC<HeaderProps> = ({
  quote,
  health,
  breadth,
  signal,
  activeSymbol,
  onSelectSymbol,
  onOpenSystemModal,
  onToggleUniverseDrawer,
  onOpenSectorHeatmap,
  onRefresh,
  isRefreshing = false,
  isWsConnected,
}) => {
  const [theme, setTheme] = useState<'dark' | 'light'>('dark')
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<StockSearchResult[]>([])
  const [isSearching, setIsSearching] = useState(false)
  const [showSearchDropdown, setShowSearchDropdown] = useState(false)
  const searchRef = useRef<HTMLDivElement | null>(null)

  // Initialize theme
  useEffect(() => {
    const savedTheme = localStorage.getItem('theme') as 'dark' | 'light' | null
    const initial = savedTheme || 'dark'
    setTheme(initial)
    if (initial === 'dark') {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }, [])

  const toggleTheme = () => {
    const next = theme === 'dark' ? 'light' : 'dark'
    setTheme(next)
    localStorage.setItem('theme', next)
    if (next === 'dark') {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }

  // Handle outside click to close search dropdown
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) {
        setShowSearchDropdown(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Auto-complete search with debouncing
  useEffect(() => {
    if (!searchQuery.trim()) {
      setSearchResults([])
      return
    }

    const timer = setTimeout(async () => {
      setIsSearching(true)
      try {
        const results = await api.searchStocks(searchQuery, 8)
        setSearchResults(results)
        setShowSearchDropdown(true)
      } catch (e) {
        console.error('Search failed:', e)
      } finally {
        setIsSearching(false)
      }
    }, 150)

    return () => clearTimeout(timer)
  }, [searchQuery])

  // Defensive calculations for genuine Day-Wise price change (vs Previous Day's Close)
  const currentLtp = quote?.ltp ?? 0
  const baselinePrice = quote?.prev_close ?? (quote?.open ?? currentLtp)
  const changeValue = quote?.change ?? (currentLtp - baselinePrice)
  const changePct = quote?.pct_change ?? quote?.change_pct ?? (baselinePrice > 0 ? (changeValue / baselinePrice) * 100 : 0)
  const isNeutral = Math.abs(changeValue) < 0.001
  const isBullish = changeValue > 0

  return (
    <header className="sticky top-0 z-40 w-full glass-panel border-b border-[var(--border-subtle)] px-3 sm:px-4 py-2 backdrop-blur-xl">
      <div className="max-w-[1920px] mx-auto flex flex-col md:flex-row items-center justify-between gap-2.5">
        
        {/* Left Section: Platform Brand & Universal Search */}
        <div className="flex items-center gap-3 w-full md:w-auto justify-between md:justify-start">
          {/* Typographical Brand Logo - The Name IS the Logo */}
          <div className="flex items-center gap-2 select-none cursor-pointer group shrink-0" onClick={() => onSelectSymbol('RELIANCE')}>
            <div className="flex flex-col">
              <div className="flex items-center gap-1.5">
                <span className="font-black text-sm sm:text-base tracking-[0.2em] text-transparent bg-clip-text bg-gradient-to-r from-blue-400 via-indigo-200 to-emerald-400 drop-shadow-sm font-sans uppercase">
                  MARKET<span className="text-blue-400 font-medium">INTEL</span>
                </span>
              </div>
              <div className="flex items-center gap-1.5 text-[8.5px] text-[var(--text-muted)] font-mono tracking-widest uppercase">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse shadow-sm shadow-emerald-500/50" />
                <span>LIVE QUANT DESK</span>
              </div>
            </div>
          </div>

          {/* Universal 2,357 Equities Search Bar */}
          <div className="relative w-36 sm:w-48 md:w-56" ref={searchRef}>
            <div className="flex items-center px-2.5 py-1.5 rounded-lg bg-[var(--surface-raised)] border border-[var(--border-subtle)] focus-within:border-blue-500 focus-within:ring-2 focus-within:ring-blue-500/20 transition-all">
              <Search className="w-3.5 h-3.5 text-[var(--text-muted)] mr-2 shrink-0" />
              <input
                type="text"
                placeholder="Search ticker, company..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onFocus={() => {
                  if (searchResults.length > 0) setShowSearchDropdown(true)
                }}
                className="w-full bg-transparent text-xs text-[var(--text-primary)] placeholder-[var(--text-muted)] outline-none font-sans"
              />
              {isSearching && (
                <div className="w-3 h-3 border-2 border-blue-500 border-t-transparent rounded-full animate-spin shrink-0" />
              )}
            </div>

            {/* Dropdown Results */}
            <AnimatePresence>
              {showSearchDropdown && searchResults.length > 0 && (
                <motion.div
                  initial={{ opacity: 0, y: -4 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -4 }}
                  transition={{ duration: 0.15 }}
                  className="absolute left-0 right-0 mt-1.5 glass-panel-raised rounded-xl overflow-hidden shadow-2xl z-50 max-h-80 overflow-y-auto"
                >
                  <div className="p-1.5 text-[10px] uppercase font-mono text-[var(--text-muted)] tracking-wider px-3 border-b border-[var(--border-subtle)]">
                    Equities Match ({searchResults.length})
                  </div>
                  {searchResults.map((item) => (
                    <button
                      key={item.symbol}
                      onClick={() => {
                        onSelectSymbol(item.symbol)
                        setShowSearchDropdown(false)
                        setSearchQuery('')
                      }}
                      className="w-full flex items-center justify-between px-3 py-2 hover:bg-blue-500/10 transition-colors text-left group"
                    >
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-bold text-[var(--text-primary)] group-hover:text-blue-400">
                          {item.symbol}
                        </span>
                        {item.is_top_300 && (
                          <span className="text-[9px] px-1 py-0.2 rounded bg-amber-500/10 text-amber-400 font-mono border border-amber-500/20">
                            TOP 300
                          </span>
                        )}
                      </div>
                      <span className="text-[11px] text-[var(--text-muted)] truncate max-w-[140px]">
                        {item.company_name}
                      </span>
                    </button>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>

        {/* Center Section: Active Stock Ticker Strip (Compact, High-Density, Never Cropped) */}
        <div className="flex items-center gap-2.5 py-1 px-3 rounded-xl bg-[var(--surface-raised)] border border-[var(--border-subtle)] shrink-0">
          <div className="flex items-center gap-1.5">
            <span className="text-xs font-mono font-bold text-[var(--text-primary)] tracking-wide">
              {activeSymbol}
            </span>
            <span className="text-[9px] font-mono text-[var(--text-muted)] uppercase px-1 py-0.2 rounded bg-[var(--surface)] border border-[var(--border-subtle)]">
              NSE EQ
            </span>
          </div>

          <div className="h-3.5 w-[1px] bg-[var(--border-subtle)]" />

          {/* LTP & Price Delta */}
          <div className="flex items-center gap-2 font-mono">
            <span className="text-sm font-bold text-[var(--text-primary)] tnum">
              ₹{currentLtp.toFixed(2)}
            </span>
            <span
              className={`flex items-center gap-0.5 text-xs font-semibold px-2 py-0.5 rounded tnum border ${
                isNeutral
                  ? 'text-[var(--text-muted)] bg-[var(--surface)] border-[var(--border-subtle)]'
                  : isBullish
                  ? 'text-emerald-500 bg-emerald-500/10 border-emerald-500/30'
                  : 'text-rose-500 bg-rose-500/10 border-rose-500/30'
              }`}
            >
              {!isNeutral && (isBullish ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />)}
              {isNeutral
                ? '0.00 (0.00%)'
                : `${isBullish ? '+' : ''}${changeValue.toFixed(2)} (${isBullish ? '+' : ''}${changePct.toFixed(2)}%)`}
            </span>
          </div>

          {/* AI Quant Recommendation Pill */}
          {signal && (
            <div className="flex items-center gap-2 pl-2 border-l border-[var(--border-subtle)] font-mono text-[11px]">
              <span
                className={`px-2.5 py-0.5 rounded-md text-[10px] font-bold border tracking-wider shadow-sm ${
                  signal.action === 'STRONG_BUY'
                    ? 'bg-emerald-600 text-white border-emerald-500 shadow-emerald-500/20'
                    : signal.action === 'BUY'
                    ? 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-500/40'
                    : signal.action === 'STRONG_SELL'
                    ? 'bg-rose-600 text-white border-rose-500 shadow-rose-500/20'
                    : signal.action === 'SELL'
                    ? 'bg-rose-500/15 text-rose-600 dark:text-rose-400 border-rose-500/40'
                    : 'bg-amber-500/15 text-amber-600 dark:text-amber-400 border-amber-500/40'
                }`}
              >
                AI {signal.action} ({signal.confidence_pct?.toFixed(0)}%)
              </span>
            </div>
          )}
        </div>

        {/* Right Section: Telemetry & Actions (Compact, Never Clipped) */}
        <div className="flex items-center gap-1.5 shrink-0">
          {/* Manual Platform Refresh */}
          {onRefresh && (
            <button
              onClick={onRefresh}
              disabled={isRefreshing}
              className="flex items-center gap-1 px-2 py-1 rounded-lg bg-[var(--surface-raised)] border border-[var(--border-subtle)] hover:border-blue-500/50 hover:bg-blue-500/10 transition-all text-xs font-mono interactive-btn disabled:opacity-50"
              title="Manual Refresh Quotes, AI Signals & Corridor Forecasts"
            >
              <RefreshCw className={`w-3.5 h-3.5 text-blue-400 ${isRefreshing ? 'animate-spin' : ''}`} />
              <span className="hidden lg:inline text-[var(--text-primary)]">Refresh</span>
            </button>
          )}

          {/* Top 300 Institutional Drawer Trigger */}
          <button
            onClick={onToggleUniverseDrawer}
            className="flex items-center gap-1 px-2 py-1 rounded-lg bg-[var(--surface-raised)] border border-[var(--border-subtle)] hover:border-blue-500/50 hover:bg-blue-500/10 transition-all text-xs font-mono interactive-btn"
            title="Open Top 300 Turnover Universe"
          >
            <Layers className="w-3.5 h-3.5 text-blue-400" />
            <span className="hidden lg:inline text-[var(--text-primary)]">Universe</span>
          </button>

          {/* Sector Heatmap Trigger */}
          {onOpenSectorHeatmap && (
            <button
              onClick={onOpenSectorHeatmap}
              className="flex items-center gap-1 px-2 py-1 rounded-lg bg-[var(--surface-raised)] border border-[var(--border-subtle)] hover:border-indigo-500/50 hover:bg-indigo-500/10 transition-all text-xs font-mono interactive-btn"
              title="Open Sector Momentum Heatmap & Strong Buys"
            >
              <Activity className="w-3.5 h-3.5 text-indigo-400" />
              <span className="hidden lg:inline text-[var(--text-primary)]">Sectors</span>
            </button>
          )}

          {/* Engine Health / System Modal Trigger */}
          <button
            onClick={onOpenSystemModal}
            className="flex items-center gap-1 px-2 py-1 rounded-lg bg-[var(--surface-raised)] border border-[var(--border-subtle)] hover:border-emerald-500/50 hover:bg-emerald-500/10 transition-all text-xs font-mono interactive-btn"
            title="System & Lakehouse Parity Telemetry"
          >
            <div className={`w-2 h-2 rounded-full ${health?.status === 'HEALTHY' ? 'bg-emerald-400' : 'bg-amber-400'} animate-ping`} />
            <span className="hidden lg:inline text-[var(--text-primary)]">Telemetry</span>
          </button>

          {/* Real-time WS Socket Pulse Badge */}
          <div
            className={`flex items-center gap-1 px-1.5 py-1 rounded-lg text-[10px] font-mono border ${
              isWsConnected
                ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                : 'bg-rose-500/10 text-rose-400 border-rose-500/20'
            }`}
            title={isWsConnected ? 'WebSocket Stream Connected' : 'WebSocket Reconnecting...'}
          >
            <Radio className="w-3 h-3 animate-pulse" />
            <span className="hidden xl:inline">{isWsConnected ? 'LIVE' : 'DISCONNECTED'}</span>
          </div>

          {/* Theme Toggle (Dark / Light) */}
          <button
            onClick={toggleTheme}
            className="p-1.5 rounded-lg bg-[var(--surface-raised)] border border-[var(--border-subtle)] hover:border-amber-500/40 hover:text-amber-400 transition-all text-[var(--text-secondary)] interactive-btn"
            title={`Switch to ${theme === 'dark' ? 'Light' : 'Dark'} mode`}
          >
            {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>
        </div>

      </div>
    </header>
  )
}
