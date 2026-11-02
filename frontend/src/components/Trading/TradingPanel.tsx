import React, { useState } from 'react'
import {
  Wallet,
  Briefcase,
  Send,
  History,
  TrendingUp,
  TrendingDown,
  ShieldCheck,
  ShieldAlert,
  XCircle,
  CheckCircle2,
  AlertTriangle,
  Zap,
  ArrowRight
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  PortfolioSummaryResponse,
  PositionItem,
  TradeItem
} from '../../types'
import { api } from '../../services/api'

interface TradingPanelProps {
  portfolio: PortfolioSummaryResponse | null
  positions: PositionItem[]
  trades: TradeItem[]
  activeSymbol: string
  onRefreshData: () => void
}

export const TradingPanel: React.FC<TradingPanelProps> = ({
  portfolio,
  positions,
  trades,
  activeSymbol,
  onRefreshData,
}) => {
  const [tab, setTab] = useState<'positions' | 'order' | 'portfolio' | 'history'>('positions')
  const [orderDirection, setOrderDirection] = useState<'BUY' | 'SELL'>('BUY')
  const [orderType, setOrderType] = useState<'MARKET' | 'LIMIT'>('MARKET')
  const [quantity, setQuantity] = useState<string>('50')
  const [limitPrice, setLimitPrice] = useState<string>('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [orderMsg, setOrderMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  const handlePlaceOrder = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSubmitting(true)
    setOrderMsg(null)

    try {
      const payload: any = {
        symbol: activeSymbol,
        direction: orderDirection,
      }
      if (quantity && parseInt(quantity) > 0) {
        payload.quantity = parseInt(quantity)
      }
      if (orderType === 'LIMIT' && limitPrice && parseFloat(limitPrice) > 0) {
        payload.price = parseFloat(limitPrice)
      }

      const res = await api.placeOrder(payload)
      setOrderMsg({
        type: 'success',
        text: `Order ${res.status}: ${res.direction} ${res.quantity} shares of ${res.symbol} @ ₹${res.filled_price?.toFixed(2)}`,
      })
      onRefreshData()
    } catch (err: any) {
      setOrderMsg({
        type: 'error',
        text: err.message || 'Order failed risk checks',
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleClosePosition = async (sym: string) => {
    try {
      await api.closePosition(sym)
      onRefreshData()
    } catch (e: any) {
      alert(`Failed to close position: ${e.message}`)
    }
  }

  const [isResetting, setIsResetting] = useState(false)

  const handleResetPortfolio = async () => {
    if (!window.confirm('Are you sure you want to reset your paper trading account to fresh ₹10,00,000 INR? All active positions and trade history will be cleared.')) {
      return
    }
    setIsResetting(true)
    try {
      await api.resetPortfolio(1000000)
      onRefreshData()
    } catch (e: any) {
      alert(`Reset failed: ${e.message}`)
    } finally {
      setIsResetting(false)
    }
  }

  return (
    <div className="glass-panel rounded-2xl h-full flex flex-col overflow-hidden border border-[var(--border-subtle)]">
      {/* Panel Tab Navigation Bar */}
      <div className="p-2 border-b border-[var(--border-subtle)] bg-[var(--surface-raised)] flex items-center justify-between overflow-x-auto">
        <div className="flex items-center gap-1">
          {[
            { id: 'positions', label: `Positions (${positions.length})`, icon: Briefcase },
            { id: 'order', label: 'Paper Order Entry', icon: Send },
            { id: 'portfolio', label: 'Portfolio Risk', icon: Wallet },
            { id: 'history', label: 'Tax & Trades Ledger', icon: History },
          ].map((t) => {
            const Icon = t.icon
            const isActive = tab === t.id
            return (
              <button
                key={t.id}
                onClick={() => setTab(t.id as any)}
                className={`relative flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-mono transition-all interactive-btn whitespace-nowrap ${
                  isActive
                    ? 'text-blue-400 font-bold'
                    : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                }`}
              >
                {isActive && (
                  <motion.div
                    layoutId="trading-tab-active"
                    className="absolute inset-0 bg-blue-500/10 border border-blue-500/30 rounded-xl"
                    transition={{ type: 'spring', stiffness: 400, damping: 30 }}
                  />
                )}
                <Icon className="w-3.5 h-3.5 relative z-10" />
                <span className="relative z-10">{t.label}</span>
              </button>
            )
          })}
        </div>

        {/* Capital Quick Indicator */}
        {portfolio && (
          <div className="hidden sm:flex items-center gap-2 text-xs font-mono pr-2">
            <span className="text-[var(--text-muted)]">Equity:</span>
            <span className="font-bold text-[var(--text-primary)] tnum">
              ₹{(portfolio.total_portfolio_value ?? 1000000).toLocaleString('en-IN', {
                maximumFractionDigits: 0,
              })}
            </span>
          </div>
        )}
      </div>

      {/* Tab 1: Live Positions */}
      {tab === 'positions' && (
        <div className="flex-1 overflow-x-auto overflow-y-auto">
          {positions.length > 0 ? (
            <table className="w-full text-left text-xs font-mono border-collapse">
              <thead>
                <tr className="border-b border-[var(--border-subtle)] bg-[var(--surface-raised)] text-[var(--text-muted)] text-[10px] uppercase">
                  <th className="py-2.5 px-3">Symbol</th>
                  <th className="py-2.5 px-3">Qty</th>
                  <th className="py-2.5 px-3">Entry Price</th>
                  <th className="py-2.5 px-3">LTP</th>
                  <th className="py-2.5 px-3">Unrealized P&L</th>
                  <th className="py-2.5 px-3">ML Stop</th>
                  <th className="py-2.5 px-3">Target 1</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border-subtle)]">
                {positions.map((pos) => {
                  const unPnl = pos.unrealized_pnl ?? 0
                  const unPnlPct = pos.unrealized_pnl_pct ?? 0
                  const isProfit = unPnl >= 0
                  const entryPrice = pos.entry_price ?? 0
                  const curPrice = pos.current_price ?? entryPrice
                  const stopPrice = pos.ml_stop_price ?? 0
                  const t1Price = pos.ml_target_1 ?? 0

                  return (
                    <tr key={pos.symbol} className="hover:bg-blue-500/5 transition-colors">
                      <td className="py-2.5 px-3 font-bold text-[var(--text-primary)]">
                        {pos.symbol}
                      </td>
                      <td className="py-2.5 px-3 text-[var(--text-secondary)] tnum">{pos.quantity}</td>
                      <td className="py-2.5 px-3 tnum">₹{entryPrice.toFixed(2)}</td>
                      <td className="py-2.5 px-3 font-semibold text-[var(--text-primary)] tnum">
                        ₹{curPrice.toFixed(2)}
                      </td>
                      <td
                        className={`py-2.5 px-3 font-bold tnum ${
                          isProfit ? 'text-emerald-400' : 'text-rose-400'
                        }`}
                      >
                        {isProfit ? '+' : ''}₹{unPnl.toFixed(2)} ({isProfit ? '+' : ''}
                        {unPnlPct.toFixed(2)}%)
                      </td>
                      <td className="py-2.5 px-3 text-rose-400 tnum">₹{stopPrice.toFixed(2)}</td>
                      <td className="py-2.5 px-3 text-blue-400 tnum">₹{t1Price.toFixed(2)}</td>
                      <td className="py-2.5 px-3">
                        <span
                          className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${
                            pos.partial_exit_done
                              ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                              : 'bg-slate-500/10 text-[var(--text-muted)]'
                          }`}
                        >
                          {pos.partial_exit_done ? 'Booked 35%' : 'Active 100%'}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-right">
                        <button
                          onClick={() => handleClosePosition(pos.symbol)}
                          className="px-2.5 py-1 rounded-lg text-[10px] font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/30 hover:bg-rose-500/20 transition-all interactive-btn"
                        >
                          Square Off
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          ) : (
            <div className="py-12 text-center text-xs font-mono text-[var(--text-muted)]">
              No open paper trading positions currently active. Place an order or wait for Model 4 signal.
            </div>
          )}
        </div>
      )}

      {/* Tab 2: Manual Simulated Order Placement Form */}
      {tab === 'order' && (
        <form onSubmit={handlePlaceOrder} className="p-4 flex-1 space-y-4 max-w-lg">
          <div className="flex items-center justify-between">
            <div>
              <span className="text-[10px] uppercase font-mono text-[var(--text-muted)]">Selected Ticker</span>
              <div className="text-base font-mono font-bold text-[var(--text-primary)]">{activeSymbol}</div>
            </div>

            {/* BUY / SELL Switcher */}
            <div className="flex items-center gap-1 bg-[var(--surface-raised)] p-1 rounded-xl border border-[var(--border-subtle)]">
              <button
                type="button"
                onClick={() => setOrderDirection('BUY')}
                className={`px-5 py-1.5 text-xs font-mono font-bold rounded-lg transition-all interactive-btn ${
                  orderDirection === 'BUY'
                    ? 'bg-emerald-600 text-white shadow-md'
                    : 'text-[var(--text-secondary)] hover:text-emerald-400'
                }`}
              >
                BUY
              </button>
              <button
                type="button"
                onClick={() => setOrderDirection('SELL')}
                className={`px-5 py-1.5 text-xs font-mono font-bold rounded-lg transition-all interactive-btn ${
                  orderDirection === 'SELL'
                    ? 'bg-rose-600 text-white shadow-md'
                    : 'text-[var(--text-secondary)] hover:text-rose-400'
                }`}
              >
                SELL
              </button>
            </div>
          </div>

          {/* Quick Quantity Chips */}
          <div className="space-y-1.5">
            <label className="text-[10px] uppercase font-mono text-[var(--text-muted)]">Shares Quantity</label>
            <div className="flex items-center gap-2">
              <input
                type="number"
                placeholder="Shares (e.g. 50)"
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
                className="w-36 px-3 py-2 rounded-xl bg-[var(--surface-raised)] border border-[var(--border-subtle)] font-mono text-xs text-[var(--text-primary)] outline-none focus:border-blue-500"
              />
              <div className="flex items-center gap-1 font-mono text-xs">
                {['25', '50', '100', '250', '500'].map((q) => (
                  <button
                    key={q}
                    type="button"
                    onClick={() => setQuantity(q)}
                    className="px-2 py-1 rounded-lg bg-[var(--surface-raised)] border border-[var(--border-subtle)] text-[10px] text-[var(--text-secondary)] hover:text-blue-400 hover:border-blue-500/30 interactive-btn"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Feedback Messages */}
          {orderMsg && (
            <div
              className={`p-3 rounded-xl text-xs font-mono flex items-center gap-2 border ${
                orderMsg.type === 'success'
                  ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                  : 'bg-rose-500/10 text-rose-400 border-rose-500/30'
              }`}
            >
              {orderMsg.type === 'success' ? (
                <CheckCircle2 className="w-4 h-4 shrink-0" />
              ) : (
                <AlertTriangle className="w-4 h-4 shrink-0" />
              )}
              <span>{orderMsg.text}</span>
            </div>
          )}

          <button
            type="submit"
            disabled={isSubmitting || (portfolio?.circuit_breaker_tripped ?? false)}
            className={`w-full py-3 rounded-xl font-mono text-xs font-bold uppercase tracking-wider text-white shadow-xl transition-all interactive-btn ${
              orderDirection === 'BUY'
                ? 'bg-emerald-600 hover:bg-emerald-500 shadow-emerald-600/20'
                : 'bg-rose-600 hover:bg-rose-500 shadow-rose-600/20'
            } disabled:opacity-50 disabled:pointer-events-none`}
          >
            {isSubmitting ? 'Simulating High-Speed Execution...' : `Execute Simulated ${orderDirection}`}
          </button>
        </form>
      )}

      {/* Tab 3: Portfolio Scorecard */}
      {tab === 'portfolio' && (
        <div className="p-4 flex-1 overflow-y-auto space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 font-mono">
            <div className="p-3.5 rounded-xl bg-[var(--surface-raised)] border border-[var(--border-subtle)]">
              <span className="text-[10px] text-[var(--text-muted)] uppercase">Total Equity</span>
              <div className="text-base font-bold text-[var(--text-primary)] pt-1 tnum">
                ₹{(portfolio?.total_portfolio_value ?? 1000000).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
              </div>
            </div>

            <div className="p-3.5 rounded-xl bg-[var(--surface-raised)] border border-[var(--border-subtle)]">
              <span className="text-[10px] text-[var(--text-muted)] uppercase">Available Cash</span>
              <div className="text-base font-bold text-[var(--text-primary)] pt-1 tnum">
                ₹{(portfolio?.current_cash ?? 1000000).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
              </div>
            </div>

            <div className="p-3.5 rounded-xl bg-[var(--surface-raised)] border border-[var(--border-subtle)]">
              <span className="text-[10px] text-[var(--text-muted)] uppercase">Realized P&L</span>
              <div
                className={`text-base font-bold pt-1 tnum ${
                  (portfolio?.total_realized_pnl ?? 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'
                }`}
              >
                {(portfolio?.total_realized_pnl ?? 0) >= 0 ? '+' : ''}₹{(portfolio?.total_realized_pnl ?? 0).toFixed(2)}
              </div>
            </div>

            <div className="p-3.5 rounded-xl bg-[var(--surface-raised)] border border-[var(--border-subtle)]">
              <span className="text-[10px] text-[var(--text-muted)] uppercase">Total Return</span>
              <div
                className={`text-base font-bold pt-1 tnum ${
                  (portfolio?.total_return_pct ?? 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'
                }`}
              >
                {(portfolio?.total_return_pct ?? 0) >= 0 ? '+' : ''}
                {(portfolio?.total_return_pct ?? 0).toFixed(2)}%
              </div>
            </div>
          </div>

          {/* Governance Safeguards */}
          <div className="p-3.5 rounded-xl bg-[var(--surface-raised)] border border-[var(--border-subtle)] flex items-center justify-between font-mono text-xs">
            <div className="flex items-center gap-2">
              {portfolio?.circuit_breaker_tripped ? (
                <ShieldAlert className="w-4 h-4 text-rose-400" />
              ) : (
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
              )}
              <span>Daily Circuit Breaker (-3% Max Drawdown Halt)</span>
            </div>
            <span
              className={`px-2.5 py-1 rounded-lg text-[10px] font-bold ${
                portfolio?.circuit_breaker_tripped
                  ? 'bg-rose-500/10 text-rose-400 border border-rose-500/30'
                  : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
              }`}
            >
              {portfolio?.circuit_breaker_tripped ? 'TRIPPED (HALTED)' : 'ACTIVE & SAFE'}
            </span>
          </div>

          {/* Reset to Fresh ₹10,00,000 INR */}
          <div className="p-3.5 rounded-xl bg-[var(--surface-raised)] border border-[var(--border-subtle)] flex items-center justify-between font-mono text-xs">
            <div>
              <div className="font-bold text-[var(--text-primary)]">Clean Ledger / Fresh Start</div>
              <div className="text-[10px] text-[var(--text-muted)]">
                Reset cash back to ₹10,00,000 & wipe all test trade records.
              </div>
            </div>
            <button
              onClick={handleResetPortfolio}
              disabled={isResetting}
              className="px-3 py-1.5 rounded-xl text-xs font-bold bg-rose-500/10 text-rose-400 border border-rose-500/30 hover:bg-rose-500/20 transition-all interactive-btn disabled:opacity-50"
            >
              {isResetting ? 'Resetting...' : 'Reset to ₹10,00,000'}
            </button>
          </div>
        </div>
      )}

      {/* Tab 4: Closed Trade History & Indian Tax Ledger */}
      {tab === 'history' && (
        <div className="flex-1 overflow-x-auto overflow-y-auto">
          {trades.length > 0 ? (
            <table className="w-full text-left text-xs font-mono border-collapse">
              <thead>
                <tr className="border-b border-[var(--border-subtle)] bg-[var(--surface-raised)] text-[var(--text-muted)] text-[10px] uppercase">
                  <th className="py-2.5 px-3">Symbol</th>
                  <th className="py-2.5 px-3">Exit Date</th>
                  <th className="py-2.5 px-3">Hold Days</th>
                  <th className="py-2.5 px-3">Gross P&L</th>
                  <th className="py-2.5 px-3">Frictions</th>
                  <th className="py-2.5 px-3">Tax</th>
                  <th className="py-2.5 px-3">Net Realized P&L</th>
                  <th className="py-2.5 px-3">Exit Reason</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border-subtle)]">
                {trades.map((t) => {
                  const net = t.net_pnl ?? 0
                  const netPct = t.net_pnl_pct ?? 0
                  const isProfit = net >= 0
                  const gross = t.gross_pnl ?? 0
                  const frictions = t.total_transaction_frictions ?? 0
                  const tax = t.capital_gains_tax ?? 0

                  return (
                    <tr key={t.trade_id} className="hover:bg-blue-500/5 transition-colors">
                      <td className="py-2 px-3 font-bold text-[var(--text-primary)]">{t.symbol}</td>
                      <td className="py-2 px-3 text-[var(--text-secondary)]">{t.exit_time?.split('T')[0] || '—'}</td>
                      <td className="py-2 px-3 text-[var(--text-secondary)] tnum">{t.holding_days ?? 0}d</td>
                      <td className="py-2 px-3 tnum">₹{gross.toFixed(2)}</td>
                      <td className="py-2 px-3 text-rose-400 tnum">₹{frictions.toFixed(2)}</td>
                      <td className="py-2 px-3 text-amber-400 tnum">
                        ₹{tax.toFixed(2)} ({t.tax_type || 'STCG'})
                      </td>
                      <td
                        className={`py-2 px-3 font-bold tnum ${
                          isProfit ? 'text-emerald-400' : 'text-rose-400'
                        }`}
                      >
                        {isProfit ? '+' : ''}₹{net.toFixed(2)} ({isProfit ? '+' : ''}
                        {netPct.toFixed(2)}%)
                      </td>
                      <td className="py-2 px-3 text-[var(--text-muted)] text-[10px]">{t.exit_trigger || 'TARGET'}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          ) : (
            <div className="py-12 text-center text-xs font-mono text-[var(--text-muted)]">
              No closed trade records found in SQLite paper ledger.
            </div>
          )}
        </div>
      )}
    </div>
  )
}
