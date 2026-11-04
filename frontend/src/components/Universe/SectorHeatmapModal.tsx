import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Layers, TrendingUp, TrendingDown, ArrowUpRight, Flame, BarChart2, ShieldCheck, ChevronRight } from 'lucide-react'
import { SectorHeatmapItem, SectorStockItem } from '../../types'
import { api } from '../../services/api'

interface SectorHeatmapModalProps {
  isOpen: boolean
  onClose: () => void
  onSelectSymbol: (symbol: string) => void
}

export const SectorHeatmapModal: React.FC<SectorHeatmapModalProps> = ({
  isOpen,
  onClose,
  onSelectSymbol,
}) => {
  const [sectors, setSectors] = useState<SectorHeatmapItem[]>([])
  const [selectedSector, setSelectedSector] = useState<SectorHeatmapItem | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    if (isOpen) {
      setIsLoading(true)
      api.getSectorHeatmap()
        .then((data) => {
          setSectors(data)
          if (data.length > 0 && !selectedSector) {
            setSelectedSector(data[0])
          }
        })
        .catch((err) => console.error('Failed to load sector heatmap:', err))
        .finally(() => setIsLoading(false))
    }
  }, [isOpen])

  if (!isOpen) return null

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-black/60 backdrop-blur-md">
        <motion.div
          initial={{ opacity: 0, scale: 0.96 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.96 }}
          transition={{ duration: 0.18 }}
          className="relative w-full max-w-5xl max-h-[90vh] flex flex-col glass-panel-raised rounded-2xl overflow-hidden shadow-2xl border border-[var(--border-subtle)] bg-[var(--surface)]"
        >
          {/* Modal Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-[var(--border-subtle)] bg-[var(--surface-raised)]">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center">
                <Layers className="w-5 h-5 text-indigo-400" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-base font-bold text-[var(--text-primary)] tracking-tight">
                    NSE Sectoral Momentum Heatmap
                  </h2>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 font-bold">
                    LIVE
                  </span>
                </div>
                <p className="text-xs text-[var(--text-muted)]">
                  Macro rotation matrix across 11 official industry sectors with AI Strong Buy drilldown
                </p>
              </div>
            </div>

            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-overlay)] transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Modal Content Layout */}
          <div className="flex-1 overflow-hidden grid grid-cols-1 lg:grid-cols-12 min-h-0">
            {/* Left Column: Sector Grid (7 Cols) */}
            <div className="lg:col-span-7 p-4 overflow-y-auto border-r border-[var(--border-subtle)] space-y-3">
              <div className="flex items-center justify-between text-xs text-[var(--text-muted)] font-mono px-1">
                <span>SECTORS RANKED BY NET MOMENTUM</span>
                <span>{sectors.length} ACTIVE SECTORS</span>
              </div>

              {isLoading ? (
                <div className="h-64 flex items-center justify-center text-xs font-mono text-[var(--text-muted)]">
                  Computing sectoral aggregates...
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                  {sectors.map((sec) => {
                    const isPositive = sec.avg_change_pct >= 0
                    const isSelected = selectedSector?.sector_id === sec.sector_id

                    return (
                      <div
                        key={sec.sector_id}
                        onClick={() => setSelectedSector(sec)}
                        className={`p-3 rounded-xl cursor-pointer border transition-all text-left relative overflow-hidden group ${
                          isSelected
                            ? 'bg-blue-500/10 border-blue-500 shadow-md shadow-blue-500/10'
                            : 'bg-[var(--surface-raised)] border-[var(--border-subtle)] hover:border-blue-500/40 hover:bg-[var(--surface-overlay)]'
                        }`}
                      >
                        {/* Background subtle color wash */}
                        <div
                          className={`absolute inset-0 pointer-events-none opacity-5 transition-opacity group-hover:opacity-10 ${
                            isPositive ? 'bg-emerald-500' : 'bg-rose-500'
                          }`}
                        />

                        <div className="flex items-start justify-between gap-2 relative z-10">
                          <div>
                            <span className="font-bold text-xs text-[var(--text-primary)] block">
                              {sec.sector_name}
                            </span>
                            <span className="text-[10px] text-[var(--text-muted)] font-mono">
                              {sec.total_stocks} Equities
                            </span>
                          </div>

                          <span
                            className={`font-mono text-xs font-bold px-2 py-0.5 rounded-md flex items-center gap-0.5 ${
                              isPositive
                                ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                                : 'bg-rose-500/15 text-rose-400 border border-rose-500/30'
                            }`}
                          >
                            {isPositive ? '+' : ''}{sec.avg_change_pct.toFixed(2)}%
                          </span>
                        </div>

                        <div className="mt-2.5 flex items-center justify-between text-[11px] font-mono relative z-10 border-t border-[var(--border-subtle)] pt-2">
                          <div className="flex items-center gap-2 text-[var(--text-muted)] text-[10px]">
                            <span className="text-emerald-400 font-bold">{sec.advances} Adv</span>
                            <span>/</span>
                            <span className="text-rose-400 font-bold">{sec.declines} Dec</span>
                          </div>

                          {sec.strong_buys_count > 0 && (
                            <span className="flex items-center gap-1 text-[10px] font-bold text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/20">
                              <Flame className="w-3 h-3 text-emerald-400" />
                              {sec.strong_buys_count} Strong Buy
                            </span>
                          )}
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>

            {/* Right Column: Selected Sector Drilldown (5 Cols) */}
            <div className="lg:col-span-5 p-4 flex flex-col bg-[var(--surface-raised)] min-h-0 overflow-y-auto">
              {selectedSector ? (
                <div className="space-y-4">
                  <div>
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] font-mono uppercase text-indigo-400 tracking-wider font-bold">
                        SECTOR BREAKOUT LEADERS
                      </span>
                      <span
                        className={`font-mono text-xs font-bold px-2 py-0.5 rounded ${
                          selectedSector.avg_change_pct >= 0
                            ? 'text-emerald-400 bg-emerald-500/10'
                            : 'text-rose-400 bg-rose-500/10'
                        }`}
                      >
                        {selectedSector.avg_change_pct >= 0 ? '+' : ''}
                        {selectedSector.avg_change_pct.toFixed(2)}%
                      </span>
                    </div>
                    <h3 className="text-lg font-bold text-[var(--text-primary)] tracking-tight">
                      {selectedSector.sector_name}
                    </h3>
                    <p className="text-xs text-[var(--text-muted)] mt-0.5">
                      Top quantitative conviction stocks in this sector
                    </p>
                  </div>

                  {/* Stock List */}
                  <div className="space-y-1.5">
                    {selectedSector.top_stocks.map((stock) => {
                      const isUp = stock.pct_change >= 0
                      const isStrongBuy = stock.action === 'STRONG_BUY'

                      return (
                        <div
                          key={stock.symbol}
                          onClick={() => {
                            onSelectSymbol(stock.symbol)
                            onClose()
                          }}
                          className={`p-2.5 rounded-xl border flex items-center justify-between cursor-pointer transition-all hover:scale-[1.01] ${
                            isStrongBuy
                              ? 'bg-emerald-500/10 border-emerald-500/30 hover:border-emerald-500/60'
                              : 'bg-[var(--surface)] border-[var(--border-subtle)] hover:border-blue-500/40 hover:bg-[var(--surface-overlay)]'
                          }`}
                        >
                          <div>
                            <div className="flex items-center gap-1.5">
                              <span className="font-mono text-xs font-bold text-[var(--text-primary)]">
                                {stock.symbol}
                              </span>
                              <span
                                className={`text-[9px] font-mono font-bold px-1.5 py-0.2 rounded border ${
                                  isStrongBuy
                                    ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30'
                                    : stock.action === 'BUY'
                                    ? 'bg-blue-500/20 text-blue-400 border-blue-500/30'
                                    : 'bg-zinc-500/20 text-zinc-400 border-zinc-500/30'
                                }`}
                              >
                                {stock.action}
                              </span>
                            </div>
                            <span className="text-[10px] text-[var(--text-muted)] font-mono block">
                              ₹{stock.ltp.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                            </span>
                          </div>

                          <div className="flex items-center gap-2">
                            <span
                              className={`font-mono text-xs font-bold ${
                                isUp ? 'text-emerald-400' : 'text-rose-400'
                              }`}
                            >
                              {isUp ? '+' : ''}{stock.pct_change.toFixed(2)}%
                            </span>
                            <ArrowUpRight className="w-4 h-4 text-[var(--text-muted)] group-hover:text-blue-400" />
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>
              ) : (
                <div className="h-full flex items-center justify-center text-xs font-mono text-[var(--text-muted)]">
                  Select a sector to view breakout candidates
                </div>
              )}
            </div>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  )
}

