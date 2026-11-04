import React, { useState } from 'react'
import {
  BrainCircuit,
  TrendingUp,
  TrendingDown,
  ShieldCheck,
  Target,
  Sliders,
  Sparkles,
  Zap,
  Info,
  CheckCircle2,
  ChevronRight,
  RefreshCw,
  Loader2
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { CorridorForecast, AISignalResponse, ScreenerCandidateItem } from '../../types'

interface AIPanelProps {
  symbol: string
  corridor: CorridorForecast | null
  signal: AISignalResponse | null
  screenerList: ScreenerCandidateItem[]
  onSelectSymbol: (symbol: string) => void
  onRefresh?: () => void
  isRefreshing?: boolean
}

export const AIPanel: React.FC<AIPanelProps> = ({
  symbol,
  corridor,
  signal,
  screenerList,
  onSelectSymbol,
  onRefresh,
  isRefreshing = false,
}) => {
  const [activeTab, setActiveTab] = useState<'signal' | 'corridor' | 'screener'>('signal')

  const getActionColor = (action: string) => {
    switch (action?.toUpperCase()) {
      case 'STRONG_BUY':
        return 'text-white bg-emerald-600 border-emerald-500 font-black shadow-md shadow-emerald-500/25'
      case 'BUY':
        return 'text-emerald-700 bg-emerald-100 dark:text-emerald-300 dark:bg-emerald-500/20 border-emerald-500/50 font-bold'
      case 'STRONG_SELL':
        return 'text-white bg-rose-600 border-rose-500 font-black shadow-md shadow-rose-500/25'
      case 'SELL':
        return 'text-rose-700 bg-rose-100 dark:text-rose-300 dark:bg-rose-500/20 border-rose-500/50 font-bold'
      default:
        return 'text-amber-700 bg-amber-100 dark:text-amber-300 dark:bg-amber-500/20 border-amber-500/50 font-bold'
    }
  }

  // Model 4 defensive extraction
  const confidence = signal?.confidence_pct ?? (signal?.calibrated_probability ? signal.calibrated_probability * 100 : 75)
  const stopLoss = signal?.dynamic_stop_loss ?? signal?.stop_loss_price ?? 0
  const target1 = signal?.target_1 ?? signal?.target_1_price ?? 0
  const target2 = signal?.target_2 ?? signal?.target_2_price ?? 0
  const rrRatio = signal?.risk_reward_ratio ?? 2.5
  const regimeName = signal?.regime ?? 'QUANT_MOMENTUM_EXPANSION'

  // Model 3 defensive extraction
  const curPrice = corridor?.current_price ?? 0
  const p05 = corridor?.p05_floor ?? 0
  const p25 = corridor?.p25_lower ?? 0
  const p50 = corridor?.p50_median ?? 0
  const p75 = corridor?.p75_target1 ?? 0
  const q90 = corridor?.q90_runner ?? corridor?.q90_runner_target ?? 0
  const corridorWidth = corridor?.corridor_width_pct ?? corridor?.volatility_band_pct ?? 0
  const asymmetry = corridor?.asymmetry_ratio ?? 1.8

  // Calculate position within corridor (0% at p05 to 100% at q90)
  const corridorSpan = q90 > p05 ? q90 - p05 : 1
  const pricePctInCorridor = Math.max(0, Math.min(100, ((curPrice - p05) / corridorSpan) * 100))

  return (
    <div className="glass-panel rounded-2xl h-full flex flex-col overflow-hidden border border-[var(--border-subtle)]">
      {/* Panel Header */}
      <div className="p-3.5 border-b border-[var(--border-subtle)] bg-[var(--surface-raised)] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-md bg-gradient-to-tr from-indigo-500 to-purple-500 flex items-center justify-center text-white shadow-md shadow-indigo-500/20">
            <BrainCircuit className="w-3.5 h-3.5" />
          </div>
          <div>
            <h2 className="text-xs font-bold font-mono tracking-tight text-[var(--text-primary)]">
              AI QUANT INTELLIGENCE
            </h2>
            <p className="text-[10px] font-mono text-[var(--text-muted)]">
              MODELS 0, 3, 4 ENSEMBLE
            </p>
          </div>
        </div>

        <div className="flex items-center gap-1.5">
          {/* Tab Switcher Pills */}
          <div className="flex items-center gap-1 bg-[var(--surface)] p-1 rounded-xl border border-[var(--border-subtle)]">
            {(['signal', 'corridor', 'screener'] as const).map((t) => (
              <button
                key={t}
                onClick={() => setActiveTab(t)}
                className={`relative px-2.5 py-1 rounded-lg text-[10px] font-mono transition-all capitalize interactive-btn ${
                  activeTab === t
                    ? 'text-blue-400 font-bold'
                    : 'text-[var(--text-muted)] hover:text-[var(--text-primary)]'
                }`}
              >
                {activeTab === t && (
                  <motion.div
                    layoutId="ai-tab-indicator"
                    className="absolute inset-0 bg-blue-500/10 border border-blue-500/30 rounded-lg"
                    transition={{ type: 'spring', stiffness: 400, damping: 30 }}
                  />
                )}
                <span className="relative z-10">{t}</span>
              </button>
            ))}
          </div>

          {/* Quick AI Refresh Button */}
          {onRefresh && (
            <button
              onClick={onRefresh}
              disabled={isRefreshing}
              className="p-1.5 rounded-xl bg-[var(--surface)] border border-[var(--border-subtle)] hover:border-blue-500/40 hover:text-blue-400 transition-all text-[var(--text-muted)] interactive-btn disabled:opacity-50"
              title={`Recalculate AI Quant Models for ${symbol}`}
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin text-blue-400' : ''}`} />
            </button>
          )}
        </div>
      </div>

      {/* Panel Body */}
      <div className="p-3.5 flex-1 overflow-y-auto space-y-3.5">
        <AnimatePresence mode="wait">
          {/* TAB 1: MODEL 4 TRADING SIGNALS */}
          {activeTab === 'signal' && (
            <motion.div
              key="signal-tab"
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.15 }}
              className="space-y-3"
            >
              {signal ? (
                <>
                  {/* Action Recommendation Hero Card */}
                  <div className="p-4 rounded-xl bg-[var(--surface-raised)] border border-[var(--border-subtle)] space-y-3 relative overflow-hidden">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] font-mono uppercase text-[var(--text-muted)] tracking-wider">
                        Model 4 Calibrated Action
                      </span>
                      <span
                        className={`px-3 py-1 rounded-full text-xs font-mono font-bold border tracking-wider ${getActionColor(
                          signal.action
                        )}`}
                      >
                        {signal.action || 'HOLD'}
                      </span>
                    </div>

                    <div className="flex items-baseline justify-between pt-1">
                      <div>
                        <div className="text-2xl font-mono font-bold text-[var(--text-primary)] tnum">
                          {confidence.toFixed(1)}%
                        </div>
                        <div className="text-[10px] text-[var(--text-muted)] font-mono">
                          Platt-Calibrated Conviction
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-sm font-mono font-semibold text-blue-400 tnum">
                          1 : {rrRatio.toFixed(1)}
                        </div>
                        <div className="text-[10px] text-[var(--text-muted)] font-mono">
                          Risk / Reward Ratio
                        </div>
                      </div>
                    </div>

                    {/* Probability Progress Track */}
                    <div className="w-full h-1.5 rounded-full bg-[var(--surface)] overflow-hidden border border-[var(--border-subtle)]">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${Math.min(confidence, 100)}%` }}
                        transition={{ duration: 0.5, ease: 'easeOut' }}
                        className="h-full bg-gradient-to-r from-blue-500 via-indigo-400 to-emerald-400"
                      />
                    </div>
                  </div>

                  {/* Execution Guardrails Cards */}
                  <div className="grid grid-cols-3 gap-2">
                    <div className="p-2.5 rounded-xl bg-[var(--surface-raised)] border border-rose-500/20 text-center">
                      <div className="text-[10px] uppercase font-mono text-rose-400">Stop-Loss</div>
                      <div className="text-sm font-mono font-bold text-[var(--text-primary)] pt-1 tnum">
                        ₹{stopLoss > 0 ? stopLoss.toFixed(2) : '—'}
                      </div>
                    </div>

                    <div className="p-2.5 rounded-xl bg-[var(--surface-raised)] border border-blue-500/20 text-center">
                      <div className="text-[10px] uppercase font-mono text-blue-400">Target 1 (35%)</div>
                      <div className="text-sm font-mono font-bold text-[var(--text-primary)] pt-1 tnum">
                        ₹{target1 > 0 ? target1.toFixed(2) : '—'}
                      </div>
                    </div>

                    <div className="p-2.5 rounded-xl bg-[var(--surface-raised)] border border-emerald-500/20 text-center">
                      <div className="text-[10px] uppercase font-mono text-emerald-400">Target 2 (Runner)</div>
                      <div className="text-sm font-mono font-bold text-[var(--text-primary)] pt-1 tnum">
                        ₹{target2 > 0 ? target2.toFixed(2) : '—'}
                      </div>
                    </div>
                  </div>

                  {/* Market Regime Badge */}
                  <div className="p-3 rounded-xl bg-[var(--surface-raised)] border border-[var(--border-subtle)] flex items-center justify-between text-xs font-mono">
                    <span className="text-[var(--text-muted)]">Macro Regime:</span>
                    <span className="text-blue-400 font-semibold">{regimeName}</span>
                  </div>
                </>
              ) : (
                <div className="py-16 flex flex-col items-center justify-center space-y-3 text-center">
                  <div className="w-9 h-9 rounded-full bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400">
                    <Loader2 className="w-4 h-4 animate-spin" />
                  </div>
                  <div className="text-xs font-mono font-bold text-[var(--text-primary)]">
                    Calculating Model 4 Signal for {symbol}...
                  </div>
                  <div className="text-[10px] text-[var(--text-muted)] font-mono max-w-[200px]">
                    Evaluating directional probability matrix and dynamic guardrails
                  </div>
                </div>
              )}
            </motion.div>
          )}

          {/* TAB 2: MODEL 3 PRICE CORRIDOR */}
          {activeTab === 'corridor' && (
            <motion.div
              key="corridor-tab"
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.15 }}
              className="space-y-3"
            >
              {corridor ? (
                <>
                  {/* Current Position in Corridor Bar */}
                  <div className="p-3.5 rounded-xl bg-[var(--surface-raised)] border border-[var(--border-subtle)] space-y-2">
                    <div className="flex items-center justify-between text-xs font-mono">
                      <span className="text-[var(--text-muted)]">Price Position:</span>
                      <span className="font-bold text-[var(--text-primary)] tnum">
                        {pricePctInCorridor.toFixed(0)}% of Range
                      </span>
                    </div>
                    <div className="w-full h-2 rounded-full bg-[var(--surface)] overflow-hidden border border-[var(--border-subtle)] relative">
                      <div
                        className="h-full bg-gradient-to-r from-rose-500 via-amber-400 via-blue-500 to-purple-500"
                        style={{ width: `${pricePctInCorridor}%` }}
                      />
                    </div>
                    <div className="flex justify-between text-[9px] font-mono text-[var(--text-muted)]">
                      <span>P05 (₹{p05.toFixed(2)})</span>
                      <span>P50 (₹{p50.toFixed(2)})</span>
                      <span>Q90 (₹{q90.toFixed(2)})</span>
                    </div>
                  </div>

                  {/* Quant Level Ladder with Plain-English Financial Explanations */}
                  <div className="space-y-2 font-mono text-xs">
                    {/* Q90 Runner */}
                    <div className="p-2.5 rounded-xl bg-purple-500/10 border border-purple-500/25 text-purple-400 space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-bold tracking-wider">Q90 BULL RUNNER</span>
                        <span className="font-bold text-sm tnum text-purple-300">₹{q90.toFixed(2)}</span>
                      </div>
                      <p className="text-[10px] text-purple-300/80 font-sans leading-tight">
                        90th percentile optimistic tail expansion. Maximum swing runner target before mean-reversion risk.
                      </p>
                    </div>

                    {/* P75 Target 1 */}
                    <div className="p-2.5 rounded-xl bg-emerald-500/10 border border-emerald-500/25 text-emerald-400 space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-bold tracking-wider">P75 PROFIT TARGET 1</span>
                        <span className="font-bold text-sm tnum text-emerald-300">₹{p75.toFixed(2)}</span>
                      </div>
                      <p className="text-[10px] text-emerald-300/80 font-sans leading-tight">
                        75th percentile resistance. Primary profit-take where 50% position is de-risked to breakeven.
                      </p>
                    </div>

                    {/* P50 Median */}
                    <div className="p-2.5 rounded-xl bg-blue-500/10 border border-blue-500/25 text-blue-400 space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-bold tracking-wider">P50 BASELINE MEDIAN</span>
                        <span className="font-bold text-sm tnum text-blue-300">₹{p50.toFixed(2)}</span>
                      </div>
                      <p className="text-[10px] text-blue-300/80 font-sans leading-tight">
                        50th percentile central fair-value path. Prices sustained above P50 reflect institutional momentum.
                      </p>
                    </div>

                    {/* P25 Lower Bound */}
                    <div className="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/25 text-amber-400 space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-bold tracking-wider">P25 CONSERVATIVE SUPPORT</span>
                        <span className="font-bold text-sm tnum text-amber-300">₹{p25.toFixed(2)}</span>
                      </div>
                      <p className="text-[10px] text-amber-300/80 font-sans leading-tight">
                        25th percentile value accumulation dip. High-probability swing support in bull market regimes.
                      </p>
                    </div>

                    {/* P05 Tail Stop Floor */}
                    <div className="p-2.5 rounded-xl bg-rose-500/10 border border-rose-500/25 text-rose-400 space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-bold tracking-wider">P05 TAIL STOP FLOOR</span>
                        <span className="font-bold text-sm tnum text-rose-300">₹{p05.toFixed(2)}</span>
                      </div>
                      <p className="text-[10px] text-rose-300/80 font-sans leading-tight">
                        5th percentile structural risk floor. Complete quantitative thesis invalidation; hard structural stop-loss.
                      </p>
                    </div>
                  </div>

                  {/* Metric Pills */}
                  <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                    <div className="p-2.5 rounded-xl bg-[var(--surface-raised)] border border-[var(--border-subtle)] text-center">
                      <span className="text-[10px] text-[var(--text-muted)] block">Corridor Width</span>
                      <span className="font-bold text-[var(--text-primary)] tnum">±{corridorWidth.toFixed(2)}%</span>
                    </div>
                    <div className="p-2.5 rounded-xl bg-[var(--surface-raised)] border border-[var(--border-subtle)] text-center">
                      <span className="text-[10px] text-[var(--text-muted)] block">Asymmetry Ratio</span>
                      <span className="font-bold text-emerald-400 tnum">{asymmetry.toFixed(2)}x</span>
                    </div>
                  </div>
                </>
              ) : (
                <div className="py-12 text-center text-xs font-mono text-[var(--text-muted)]">
                  Loading Model 3 probabilistic corridor forecast...
                </div>
              )}
            </motion.div>
          )}

          {/* TAB 3: MODEL 0 PRE-MARKET SCREENER */}
          {activeTab === 'screener' && (
            <motion.div
              key="screener-tab"
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.15 }}
              className="space-y-2"
            >
              <div className="text-[10px] font-mono uppercase text-[var(--text-muted)] tracking-wider pb-1">
                09:08 Pre-Market High Conviction Leads ({screenerList.length})
              </div>

              {screenerList.length === 0 ? (
                <div className="py-12 text-center text-xs font-mono text-[var(--text-muted)]">
                  No pre-market gap breakout candidates detected yet.
                </div>
              ) : (
                screenerList.map((cand) => {
                  const score = cand.conviction_score ?? cand.rank_score ?? 0.8
                  const turnover = cand.turnover_cr ?? cand.turnover_20d_cr ?? 150
                  return (
                    <button
                      key={cand.symbol}
                      onClick={() => onSelectSymbol(cand.symbol)}
                      className={`w-full p-2.5 rounded-xl border flex items-center justify-between text-left transition-all interactive-btn ${
                        cand.symbol === symbol
                          ? 'bg-blue-500/10 border-blue-500/40'
                          : 'bg-[var(--surface-raised)] border-[var(--border-subtle)] hover:border-blue-500/30'
                      }`}
                    >
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-bold font-mono text-[var(--text-primary)]">
                            #{cand.rank} {cand.symbol}
                          </span>
                          <span
                            className={`px-1.5 py-0.2 rounded text-[9px] font-mono font-bold ${
                              cand.action === 'BUY'
                                ? 'bg-emerald-500/10 text-emerald-400'
                                : 'bg-rose-500/10 text-rose-400'
                            }`}
                          >
                            {cand.action}
                          </span>
                        </div>
                        <div className="text-[10px] text-[var(--text-muted)] font-mono pt-0.5">
                          Turnover: ₹{turnover.toFixed(0)} Cr
                        </div>
                      </div>

                      <div className="text-right font-mono">
                        <div className="text-xs font-bold text-[var(--text-primary)] tnum">
                          ₹{(cand.current_price ?? 0).toFixed(2)}
                        </div>
                        <div className="text-[10px] text-emerald-400 font-semibold tnum">
                          Score: {(score * 100).toFixed(0)}%
                        </div>
                      </div>
                    </button>
                  )
                })
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}
