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
  Radio
} from 'lucide-react'
import { StockQuote, StockSearchResult, SystemHealth, MarketBreadth } from '../types'
import { api } from '../services/api'

interface HeaderProps {
  quote: StockQuote | null
  health: SystemHealth | null
  breadth: MarketBreadth | null
  activeSymbol: string
  onSelectSymbol: (symbol: string) => void
  onOpenSystemModal: () => void
  onToggleUniverseDrawer: () => void
  isWsConnected: boolean
}

export const Header: React.FC<HeaderProps> = ({
  quote,
  health,
  breadth,
  activeSymbol,
  onSelectSymbol,
  onOpenSystemModal,
  onToggleUniverseDrawer,
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

  const isBullish = (quote?.change ?? 0) >= 0

  return (
    <header className="sticky top-0 z-40 w-full glass-panel border-b border-[var(--border-subtle)] px-4 py-2.5 transition-colors duration-200">
      <div className="max-w-[1920px] mx-auto flex items-center justify-between gap-4">
        
        {/* Brand & Symbol Search */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-blue-600/10 border border-blue-500/30 flex items-center justify-center text-blue-500 font-bold tracking-wider">
              <Activity className="w-4 h-4 animate-pulse" />
            </div>
            <div className="hidden sm:block">
              <div className="text-sm font-bold tracking-wider uppercase bg-gradient-to-r from-blue-400 to-indigo-400 bg-clip-text text-transparent">
                MarketIntel
              </div>
              <div className="text-[10px] text-[var(--text-muted)] tracking-widest uppercase font-mono">
                Institutional v2
              </div>
            </div>
          </div>

          {/* Quick Search Input */}
          <div ref={searchRef} className="relative w-56 md:w-72">
            <div className="relative flex items-center">
              <Search className="w-4 h-4 absolute left-3 text-[var(--text-muted)] pointer-events-none" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onFocus={() => searchResults.length > 0 && setShowSearchDropdown(true)}
                placeholder="Search 2,357 NSE Equities..."
                className="w-full bg-[var(--surface-raised)] border border-[var(--border-subtle)] focus:border-[var(--accent-blue)] rounded-lg pl-9 pr-3 py-1.5 text-xs text-[var(--text-primary)] placeholder-[var(--text-muted)] outline-none transition-all duration-150"
              />
            </div>

            {/* Dropdown Results */}
            {showSearchDropdown && searchResults.length > 0 && (
              <div className="absolute left-0 mt-1.5 w-80 glass-panel-raised rounded-xl shadow-2xl py-1.5 z-50 max-h-96 overflow-y-auto border border-[var(--border-strong)]">
                {searchResults.map((stock) => (
                  <button
                    key={stock.symbol}
                    onClick={() => {
                      onSelectSymbol(stock.symbol)
                      setShowSearchDropdown(false)
                      setSearchQuery('')
                    }}
                    className="w-full px-3 py-2 text-left hover:bg-blue-500/10 flex items-center justify-between border-b border-[var(--border-subtle)] last:border-0 transition-colors"
                  >
                    <div>
                      <div className="flex items-center gap-1.5">
                        <span className="font-mono font-semibold text-xs text-[var(--text-primary)]">
                          {stock.symbol}
                        </span>
                        {stock.is_top_300 && (
                          <span className="px-1.5 py-0.5 rounded text-[9px] bg-blue-500/10 text-blue-400 border border-blue-500/20 font-mono">
                            TOP 300
                          </span>
                        )}
                      </div>
                      <div className="text-[11px] text-[var(--text-secondary)] truncate max-w-[200px]">
                        {stock.company_name}
                      </div>
                    </div>
                    <span className="text-[10px] font-mono text-[var(--text-muted)]">
                      {stock.exchange}
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Top 300 Universe Drawer Toggle */}
          <button
            onClick={onToggleUniverseDrawer}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-raised)] hover:border-blue-500/40 text-[var(--text-secondary)] hover:text-[var(--text-primary)] text-xs transition-colors"
            title="Open Top 300 Institutional Leaders Universe"
          >
            <Layers className="w-3.5 h-3.5 text-blue-500" />
            <span className="hidden md:inline font-mono">Top 300</span>
          </button>
        </div>

        {/* Live Active Stock Ticker Details */}
        {quote && (
          <div className="hidden lg:flex items-center gap-6 px-4 py-1.5 rounded-xl bg-[var(--surface-raised)] border border-[var(--border-subtle)]">
            <div className="flex items-baseline gap-2">
              <span className="font-mono font-bold text-sm tracking-tight text-[var(--text-primary)]">
                {quote.symbol}
              </span>
              <span className="text-xs font-mono font-bold text-[var(--text-primary)] tnum">
                ₹{quote.ltp.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </span>
              <span
                className={`flex items-center gap-0.5 font-mono text-xs font-semibold tnum ${
                  isBullish ? 'text-[var(--bull)]' : 'text-[var(--bear)]'
                }`}
              >
                {isBullish ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                {isBullish ? '+' : ''}
                {quote.change.toFixed(2)} ({isBullish ? '+' : ''}
                {quote.change_pct.toFixed(2)}%)
              </span>
            </div>

            <div className="flex items-center gap-4 text-[11px] text-[var(--text-muted)] font-mono border-l border-[var(--border-subtle)] pl-4">
              <div>
                <span className="text-[10px] uppercase text-[var(--text-secondary)]">Open: </span>
                <span className="text-[var(--text-primary)] tnum">₹{quote.open?.toFixed(2) || '—'}</span>
              </div>
              <div>
                <span className="text-[10px] uppercase text-[var(--text-secondary)]">High: </span>
                <span className="text-[var(--text-primary)] tnum">₹{quote.high?.toFixed(2) || '—'}</span>
              </div>
              <div>
                <span className="text-[10px] uppercase text-[var(--text-secondary)]">Low: </span>
                <span className="text-[var(--text-primary)] tnum">₹{quote.low?.toFixed(2) || '—'}</span>
              </div>
              <div>
                <span className="text-[10px] uppercase text-[var(--text-secondary)]">VWAP: </span>
                <span className="text-blue-400 tnum">₹{quote.vwap?.toFixed(2) || '—'}</span>
              </div>
              <div>
                <span className="text-[10px] uppercase text-[var(--text-secondary)]">Vol: </span>
                <span className="text-[var(--text-primary)] tnum">{quote.volume?.toLocaleString('en-IN') || '—'}</span>
              </div>
            </div>
          </div>
        )}

        {/* Global Controls & Telemetry */}
        <div className="flex items-center gap-3">
          {/* Market Regime Badge */}
          {health?.market && (
            <div className="hidden sm:flex items-center gap-2 px-2.5 py-1 rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-raised)] text-xs font-mono">
              <Clock className="w-3.5 h-3.5 text-blue-500" />
              <span className="text-[11px] text-[var(--text-secondary)]">
                {health.market.ist_time.split(' ')[1]} IST
              </span>
              <span
                className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${
                  health.market.is_market_open
                    ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                    : 'bg-amber-500/10 text-amber-400 border border-amber-500/30'
                }`}
              >
                {health.market.session_state}
              </span>
            </div>
          )}

          {/* WebSocket Status Indicator */}
          <div
            className={`flex items-center gap-1.5 px-2 py-1 rounded-lg text-[10px] font-mono border ${
              isWsConnected
                ? 'border-emerald-500/30 text-emerald-400 bg-emerald-500/10'
                : 'border-rose-500/30 text-rose-400 bg-rose-500/10'
            }`}
            title={isWsConnected ? 'WebSocket Live Feed Online' : 'WebSocket Disconnected'}
          >
            <Radio className="w-3 h-3 animate-pulse" />
            <span className="hidden md:inline">{isWsConnected ? 'LIVE' : 'OFFLINE'}</span>
          </div>

          {/* System Telemetry & Operations Modal Trigger */}
          <button
            onClick={onOpenSystemModal}
            className="p-1.5 rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-raised)] hover:border-blue-500/40 text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
            title="System Telemetry & Lakehouse Sync Operations"
          >
            <Database className="w-4 h-4 text-blue-500" />
          </button>

          {/* Light / Dark Mode Toggle */}
          <button
            onClick={toggleTheme}
            className="p-1.5 rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-raised)] hover:border-blue-500/40 text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
            title={`Switch to ${theme === 'dark' ? 'Light' : 'Dark'} Mode`}
          >
            {theme === 'dark' ? (
              <Sun className="w-4 h-4 text-amber-400" />
            ) : (
              <Moon className="w-4 h-4 text-blue-500" />
            )}
          </button>
        </div>

      </div>
    </header>
  )
}
