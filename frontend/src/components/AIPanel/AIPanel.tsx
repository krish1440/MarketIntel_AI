import React, { useState } from 'react'
import {
  BrainCircuit,
  Target,
  Sparkles,
  ShieldAlert,
  ArrowUpRight,
  TrendingUp,
  Sliders,
  CheckCircle2,
  ChevronRight
} from 'lucide-react'
import {
  ScreenerCandidateItem,
  CorridorForecast,
  AISignalResponse
} from '../../types'

interface AIPanelProps {
  symbol: string
  corridor: CorridorForecast | null
  signal: AISignalResponse | null
  screenerList: ScreenerCandidateItem[]
  onSelectSymbol: (symbol: string) => void
}

export const AIPanel: React.FC<AIPanelProps> = ({
  symbol,
  corridor,
  signal,
  screenerList,
  onSelectSymbol,
}) => {
  const [activeTab, setActiveTab] = useState<'screener' | 'corridor' | 'signal'>('signal')

  const getActionColor = (action?: string) => {
    switch (action) {
      case 'STRONG_BUY':
        return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
      case 'BUY':
        return 'bg-blue-500/10 text-blue-400 border-blue-500/30'
      case 'HOLD':
        return 'bg-amber-500/10 text-amber-400 border-amber-500/30'
      default:
        return 'bg-rose-500/10 text-rose-400 border-rose-500/30'
    }
  }

  return (
    <div className="flex flex-col h-full glass-panel rounded-2xl overflow-hidden border border-[var(--border-subtle)]">
      {/* Header & Tabs */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-[var(--border-subtle)] bg-[var(--surface-raised)]">
        <div className="flex items-center gap-2">
          <BrainCircuit className="w-4 h-4 text-blue-500" />
          <span className="font-mono text-xs font-bold uppercase tracking-wider text-[var(--text-primary)]">
            AI Quantitative Engine
          </span>
        </div>

        {/* Tab Switcher */}
        <div className="flex items-center gap-1 bg-[var(--surface)] p-0.5 rounded-lg border border-[var(--border-subtle)]">
          <button
            onClick={() => setActiveTab('signal')}
            className={`px-2 py-1 text-[11px] font-mono rounded-md transition-all ${
              activeTab === 'signal'
                ? 'bg-blue-600 text-white font-semibold shadow-sm'
                : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
            }`}
          >
            Signal
          </button>
          <button
            onClick={() => setActiveTab('corridor')}
            className={`px-2 py-1 text-[11px] font-mono rounded-md transition-all ${
              activeTab === 'corridor'
                ? 'bg-blue-600 text-white font-semibold shadow-sm'
                : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
            }`}
          >
            Price Corridor
          </button>
          <button
            onClick={() => setActiveTab('screener')}
            className={`px-2 py-1 text-[11px] font-mono rounded-md transition-all ${
              activeTab === 'screener'
                ? 'bg-blue-600 text-white font-semibold shadow-sm'
                : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
            }`}
          >
            09:08 Screener
          </button>
        </div>
      </div>

      {/* Tab 1: Calibrated Signal & Action (Model 4) */}
      {activeTab === 'signal' && (
        <div className="p-4 flex-1 overflow-y-auto space-y-4">
          {signal ? (
            <>
              {/* Action Recommendation Card */}
              <div className="p-4 rounded-xl bg-[var(--surface-raised)] border border-[var(--border-subtle)] space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-mono uppercase text-[var(--text-secondary)]">
                    Model 4 Calibrated Action
                  </span>
                  <span
                    className={`px-2.5 py-1 rounded-full text-xs font-mono font-bold border tracking-wide ${getActionColor(
                      signal.action
                    )}`}
                  >
                    {signal.action}
                  </span>
                </div>

                <div className="flex items-baseline justify-between pt-1">
                  <div>
                    <div className="text-2xl font-mono font-bold text-[var(--text-primary)] tnum">
                      {(signal.calibrated_probability * 100).toFixed(1)}%
                    </div>
                    <div className="text-[10px] text-[var(--text-muted)] font-mono">
                      Platt-Calibrated Conviction
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-sm font-mono font-semibold text-blue-400 tnum">
                      1 : {signal.risk_reward_ratio?.toFixed(1) || '2.5'}
                    </div>
                    <div className="text-[10px] text-[var(--text-muted)] font-mono">
                      Risk / Reward Ratio
                    </div>
                  </div>
                </div>

                {/* Probability Bar */}
                <div className="w-full h-2 rounded-full bg-[var(--surface)] overflow-hidden border border-[var(--border-subtle)]">
                  <div
                    className="h-full bg-gradient-to-r from-blue-500 to-emerald-400 transition-all duration-500"
                    style={{ width: `${Math.min(signal.calibrated_probability * 100, 100)}%` }}
                  />
                </div>
              </div>

              {/* Execution Guardrails */}
              <div className="grid grid-cols-3 gap-2">
                <div className="p-2.5 rounded-xl bg-[var(--surface-raised)] border border-rose-500/20 text-center">
                  <div className="text-[10px] uppercase font-mono text-rose-400">Stop-Loss</div>
                  <div className="text-sm font-mono font-bold text-[var(--text-primary)] pt-1 tnum">
                    ₹{signal.stop_loss_price?.toFixed(2) || '—'}
                  </div>
                </div>

                <div className="p-2.5 rounded-xl bg-[var(--surface-raised)] border border-blue-500/20 text-center">
                  <div className="text-[10px] uppercase font-mono text-blue-400">Target 1 (35%)</div>
                  <div className="text-sm font-mono font-bold text-[var(--text-primary)] pt-1 tnum">
                    ₹{signal.target_1_price?.toFixed(2) || '—'}
                  </div>
                </div>

                <div className="p-2.5 rounded-xl bg-[var(--surface-raised)] border border-emerald-500/20 text-center">
                  <div className="text-[10px] uppercase font-mono text-emerald-400">Target 2 (Runner)</div>
                  <div className="text-sm font-mono font-bold text-[var(--text-primary)] pt-1 tnum">
                    ₹{signal.target_2_price?.toFixed(2) || '—'}
                  </div>
                </div>
              </div>

              {/* Regime Badge */}
              <div className="p-3 rounded-xl bg-[var(--surface-raised)] border border-[var(--border-subtle)] flex items-center justify-between text-xs font-mono">
                <span className="text-[var(--text-muted)]">Market Regime:</span>
                <span className="text-blue-400 font-semibold">{signal.regime}</span>
              </div>
            </>
          ) : (
            <div className="py-12 text-center text-xs font-mono text-[var(--text-muted)]">
              No active AI signal generated for {symbol} yet today.
            </div>
          )}
        </div>
      )}

      {/* Tab 2: Price Corridor Forecaster (Model 3) */}
      {activeTab === 'corridor' && (
        <div className="p-4 flex-1 overflow-y-auto space-y-3">
          {corridor ? (
            <>
              <div className="text-xs font-mono text-[var(--text-secondary)]">
                Quantile Regression Multi-Target Expectations for <span className="font-bold text-[var(--text-primary)]">{symbol}</span>
              </div>

              <div className="space-y-2 pt-1 font-mono text-xs">
                {/* Q90 Runner */}
                <div className="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-amber-400" />
                    <span className="text-[11px] text-amber-300">Q90 Volatility Runner</span>
                  </div>
                  <span className="font-bold text-[var(--text-primary)] tnum">
                    ₹{corridor.q90_runner_target.toFixed(2)}
                  </span>
                </div>

                {/* P75 Target 1 */}
                <div className="p-2.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-emerald-400" />
                    <span className="text-[11px] text-emerald-300">P75 Target 1 (Book 35%)</span>
                  </div>
                  <span className="font-bold text-[var(--text-primary)] tnum">
                    ₹{corridor.p75_target1.toFixed(2)}
                  </span>
                </div>

                {/* P50 Median */}
                <div className="p-2.5 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-blue-400" />
                    <span className="text-[11px] text-blue-300">P50 Expected Median</span>
                  </div>
                  <span className="font-bold text-[var(--text-primary)] tnum">
                    ₹{corridor.p50_median.toFixed(2)}
                  </span>
                </div>

                {/* P25 Lower */}
                <div className="p-2.5 rounded-xl bg-[var(--surface-raised)] border border-[var(--border-subtle)] flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-slate-400" />
                    <span className="text-[11px] text-[var(--text-secondary)]">P25 Lower Expectation</span>
                  </div>
                  <span className="font-bold text-[var(--text-primary)] tnum">
                    ₹{corridor.p25_lower.toFixed(2)}
                  </span>
                </div>

                {/* P05 Floor */}
                <div className="p-2.5 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-rose-400" />
                    <span className="text-[11px] text-rose-300">P05 Downside Floor (Stop)</span>
                  </div>
                  <span className="font-bold text-[var(--text-primary)] tnum">
                    ₹{corridor.p05_floor.toFixed(2)}
                  </span>
                </div>
              </div>

              <div className="p-3 rounded-xl bg-[var(--surface-raised)] border border-[var(--border-subtle)] flex items-center justify-between text-xs font-mono">
                <span className="text-[var(--text-muted)]">Corridor Bandwidth:</span>
                <span className="text-[var(--text-primary)] font-bold tnum">
                  ±{corridor.volatility_band_pct.toFixed(2)}%
                </span>
              </div>
            </>
          ) : (
            <div className="py-12 text-center text-xs font-mono text-[var(--text-muted)]">
              No corridor forecast calculated for {symbol}.
            </div>
          )}
        </div>
      )}

      {/* Tab 3: Pre-Market Focus Screener (Model 0) */}
      {activeTab === 'screener' && (
        <div className="flex-1 overflow-y-auto divide-y divide-[var(--border-subtle)]">
          {screenerList.length > 0 ? (
            screenerList.map((cand) => (
              <button
                key={cand.symbol}
                onClick={() => onSelectSymbol(cand.symbol)}
                className={`w-full px-4 py-2.5 text-left flex items-center justify-between hover:bg-blue-500/10 transition-colors ${
                  cand.symbol === symbol ? 'bg-blue-500/10' : ''
                }`}
              >
                <div className="flex items-center gap-3">
                  <span className="w-5 text-center font-mono text-xs font-bold text-[var(--text-muted)]">
                    #{cand.rank}
                  </span>
                  <div>
                    <div className="font-mono font-semibold text-xs text-[var(--text-primary)] flex items-center gap-1.5">
                      <span>{cand.symbol}</span>
                      <span className="text-[10px] text-[var(--text-muted)] font-normal truncate max-w-[120px]">
                        {cand.company_name}
                      </span>
                    </div>
                    <div className="text-[10px] text-[var(--text-secondary)] font-mono">
                      {cand.sector} • {cand.turnover_20d_cr.toFixed(1)} Cr/day
                    </div>
                  </div>
                </div>

                <div className="text-right">
                  <div
                    className={`text-xs font-mono font-bold ${
                      cand.gap_pct >= 0 ? 'text-[var(--bull)]' : 'text-[var(--bear)]'
                    }`}
                  >
                    {cand.gap_pct >= 0 ? '+' : ''}
                    {cand.gap_pct.toFixed(2)}%
                  </div>
                  <div className="text-[10px] font-mono text-[var(--text-muted)]">
                    Score: {(cand.conviction_score * 100).toFixed(0)}
                  </div>
                </div>
              </button>
            ))
          ) : (
            <div className="py-12 text-center text-xs font-mono text-[var(--text-muted)]">
              Generating 09:08 AM Focus Screener list...
            </div>
          )}
        </div>
      )}
    </div>
  )
}
