import React, { useState } from 'react'
import { X, Search, TrendingUp, TrendingDown, ArrowUpDown, Filter } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { TopUniverseItem } from '../../types'

interface TopUniverseDrawerProps {
  isOpen: boolean
  onClose: () => void
  universe: TopUniverseItem[]
  activeSymbol: string
  onSelectSymbol: (symbol: string) => void
}

export const TopUniverseDrawer: React.FC<TopUniverseDrawerProps> = ({
  isOpen,
  onClose,
  universe,
  activeSymbol,
  onSelectSymbol,
}) => {
  const [search, setSearch] = useState('')
  const [sortBy, setSortBy] = useState<'rank' | 'turnover' | 'price' | 'change'>('rank')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc')

  if (!isOpen) return null

  const filtered = universe
    .filter(
      (item) =>
        item.symbol.toLowerCase().includes(search.toLowerCase()) ||
        (item.company_name && item.company_name.toLowerCase().includes(search.toLowerCase()))
    )
    .sort((a, b) => {
      let aVal = 0
      let bVal = 0

      if (sortBy === 'rank') {
        aVal = a.rank
        bVal = b.rank
      } else if (sortBy === 'turnover') {
        aVal = a.turnover_20d_cr ?? a.turnover_20d_avg_cr ?? 0
        bVal = b.turnover_20d_cr ?? b.turnover_20d_avg_cr ?? 0
      } else if (sortBy === 'price') {
        aVal = a.price ?? a.current_price ?? 0
        bVal = b.price ?? b.current_price ?? 0
      } else if (sortBy === 'change') {
        aVal = a.pct_change ?? a.change_pct ?? 0
        bVal = b.pct_change ?? b.change_pct ?? 0
      }

      return sortOrder === 'asc' ? aVal - bVal : bVal - aVal
    })

  const toggleSort = (field: 'rank' | 'turnover' | 'price' | 'change') => {
    if (sortBy === field) {
      setSortOrder((prev) => (prev === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortBy(field)
      setSortOrder('desc')
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-sm transition-opacity">
      <motion.div
        initial={{ x: '100%' }}
        animate={{ x: 0 }}
        exit={{ x: '100%' }}
        transition={{ type: 'spring', damping: 25, stiffness: 300 }}
        className="w-full max-w-md h-full glass-panel-raised border-l border-[var(--border-strong)] flex flex-col shadow-2xl"
      >
        {/* Drawer Header */}
        <div className="p-4 border-b border-[var(--border-subtle)] flex items-center justify-between">
          <div>
            <h2 className="text-sm font-bold font-mono text-[var(--text-primary)]">
              Top 300 Turnover Leaders
            </h2>
            <p className="text-xs text-[var(--text-muted)] font-mono">
              Institutional Liquidity Universe (NSE)
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg bg-[var(--surface)] hover:bg-[var(--border-subtle)] transition-colors text-[var(--text-secondary)] interactive-btn"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Search & Sort Controls */}
        <div className="p-3 border-b border-[var(--border-subtle)] space-y-2">
          <div className="flex items-center px-3 py-1.5 rounded-lg bg-[var(--surface)] border border-[var(--border-subtle)]">
            <Search className="w-3.5 h-3.5 text-[var(--text-muted)] mr-2" />
            <input
              type="text"
              placeholder="Filter by symbol or name..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-transparent text-xs text-[var(--text-primary)] placeholder-[var(--text-muted)] outline-none font-mono"
            />
          </div>

          <div className="flex items-center gap-1.5 overflow-x-auto text-[11px] font-mono">
            <span className="text-[var(--text-muted)] text-[10px] uppercase">Sort:</span>
            {(['rank', 'turnover', 'price', 'change'] as const).map((s) => (
              <button
                key={s}
                onClick={() => toggleSort(s)}
                className={`px-2 py-0.5 rounded-md border text-[10px] capitalize transition-all interactive-btn ${
                  sortBy === s
                    ? 'bg-blue-500/10 text-blue-400 border-blue-500/30 font-bold'
                    : 'bg-[var(--surface)] text-[var(--text-muted)] border-[var(--border-subtle)] hover:text-[var(--text-primary)]'
                }`}
              >
                {s} {sortBy === s && (sortOrder === 'asc' ? '↑' : '↓')}
              </button>
            ))}
          </div>
        </div>

        {/* List of 300 Stocks */}
        <div className="flex-1 overflow-y-auto divide-y divide-[var(--border-subtle)]">
          {filtered.map((item) => {
            const price = item.price ?? item.current_price ?? 0
            const change = item.pct_change ?? item.change_pct ?? 0
            const turnover = item.turnover_20d_cr ?? item.turnover_20d_avg_cr ?? 0
            const isBullish = change >= 0

            return (
              <button
                key={item.symbol}
                onClick={() => {
                  onSelectSymbol(item.symbol)
                  onClose()
                }}
                className={`w-full px-4 py-2.5 text-left flex items-center justify-between hover:bg-blue-500/10 transition-colors interactive-btn ${
                  item.symbol === activeSymbol ? 'bg-blue-500/15' : ''
                }`}
              >
                <div className="flex items-center gap-2.5">
                  <span className="w-6 text-center text-[10px] font-mono text-[var(--text-muted)] font-bold">
                    #{item.rank}
                  </span>
                  <div>
                    <div className="font-mono font-bold text-xs text-[var(--text-primary)]">
                      {item.symbol}
                    </div>
                    <div className="text-[10px] text-[var(--text-muted)] font-mono">
                      ₹{turnover.toFixed(0)} Cr/day
                    </div>
                  </div>
                </div>

                <div className="text-right font-mono">
                  <div className="text-xs font-semibold text-[var(--text-primary)] tnum">
                    ₹{price.toFixed(2)}
                  </div>
                  <div
                    className={`text-[10px] flex items-center justify-end gap-0.5 font-bold tnum ${
                      isBullish ? 'text-emerald-400' : 'text-rose-400'
                    }`}
                  >
                    {isBullish ? '+' : ''}
                    {change.toFixed(2)}%
                  </div>
                </div>
              </button>
            )
          })}
        </div>
      </motion.div>
    </div>
  )
}
