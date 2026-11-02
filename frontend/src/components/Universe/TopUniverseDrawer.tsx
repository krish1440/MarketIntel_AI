import React, { useState } from 'react'
import { X, Search, Layers, TrendingUp, TrendingDown, ArrowUpDown } from 'lucide-react'
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
  const [filterQuery, setFilterQuery] = useState('')
  const [sortBy, setSortBy] = useState<'turnover' | 'change' | 'price'>('turnover')

  if (!isOpen) return null

  const filtered = universe
    .filter(
      (item) =>
        item.symbol.toLowerCase().includes(filterQuery.toLowerCase()) ||
        item.company_name.toLowerCase().includes(filterQuery.toLowerCase())
    )
    .sort((a, b) => {
      if (sortBy === 'turnover') return b.turnover_20d_avg_cr - a.turnover_20d_avg_cr
      if (sortBy === 'change') return b.change_pct - a.change_pct
      return b.current_price - a.current_price
    })

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/50 backdrop-blur-sm animate-fade-in">
      <div className="w-full max-w-md h-full glass-panel-raised flex flex-col border-l border-[var(--border-strong)] shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--border-subtle)] bg-[var(--surface-raised)]">
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-blue-500" />
            <span className="font-mono text-sm font-bold text-[var(--text-primary)]">
              Top 300 Institutional Leaders
            </span>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-slate-500/10 text-[var(--text-muted)] hover:text-[var(--text-primary)]"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Filter & Sort Controls */}
        <div className="p-3 border-b border-[var(--border-subtle)] space-y-2.5">
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-[var(--text-muted)]" />
            <input
              type="text"
              placeholder="Filter by symbol or name..."
              value={filterQuery}
              onChange={(e) => setFilterQuery(e.target.value)}
              className="w-full bg-[var(--surface)] border border-[var(--border-subtle)] rounded-lg pl-9 pr-3 py-1.5 text-xs text-[var(--text-primary)] placeholder-[var(--text-muted)] outline-none"
            />
          </div>

          <div className="flex items-center justify-between text-xs font-mono">
            <span className="text-[10px] uppercase text-[var(--text-muted)]">Sort by:</span>
            <div className="flex items-center gap-1">
              <button
                onClick={() => setSortBy('turnover')}
                className={`px-2 py-0.5 rounded text-[11px] ${
                  sortBy === 'turnover' ? 'bg-blue-600 text-white font-bold' : 'text-[var(--text-secondary)]'
                }`}
              >
                Turnover
              </button>
              <button
                onClick={() => setSortBy('change')}
                className={`px-2 py-0.5 rounded text-[11px] ${
                  sortBy === 'change' ? 'bg-blue-600 text-white font-bold' : 'text-[var(--text-secondary)]'
                }`}
              >
                Change %
              </button>
              <button
                onClick={() => setSortBy('price')}
                className={`px-2 py-0.5 rounded text-[11px] ${
                  sortBy === 'price' ? 'bg-blue-600 text-white font-bold' : 'text-[var(--text-secondary)]'
                }`}
              >
                Price
              </button>
            </div>
          </div>
        </div>

        {/* List of 300 Stocks */}
        <div className="flex-1 overflow-y-auto divide-y divide-[var(--border-subtle)]">
          {filtered.map((item) => {
            const isBullish = item.change_pct >= 0
            return (
              <button
                key={item.symbol}
                onClick={() => {
                  onSelectSymbol(item.symbol)
                  onClose()
                }}
                className={`w-full px-4 py-2.5 text-left flex items-center justify-between hover:bg-blue-500/10 transition-colors ${
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
                    <div className="text-[11px] text-[var(--text-secondary)] truncate max-w-[150px]">
                      {item.company_name}
                    </div>
                  </div>
                </div>

                <div className="text-right font-mono">
                  <div className="text-xs font-semibold text-[var(--text-primary)] tnum">
                    ₹{item.current_price.toFixed(2)}
                  </div>
                  <div
                    className={`text-[10px] flex items-center justify-end gap-0.5 font-bold tnum ${
                      isBullish ? 'text-[var(--bull)]' : 'text-[var(--bear)]'
                    }`}
                  >
                    {isBullish ? '+' : ''}
                    {item.change_pct.toFixed(2)}%
                  </div>
                </div>
              </button>
            )
          })}
        </div>
      </div>
    </div>
  )
}
