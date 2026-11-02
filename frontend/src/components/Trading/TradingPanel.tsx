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
  AlertTriangle
} from 'lucide-react'
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
  const [quantity, setQuantity] = useState<string>('')
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
      setQuantity('')
      setLimitPrice('')
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
    if (!window.confirm(`Are you sure you want to close position for ${sym} at current market price?`)) return
    try {
      await api.closePosition(sym)
      onRefreshData()
    } catch (err: any) {
      alert(`Failed to close position: ${err.message}`)
    }
  }

  return (
    <div className="flex flex-col h-full glass-panel rounded-2xl overflow-hidden border border-[var(--border-subtle)]">
      {/* Header & Tabs */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-[var(--border-subtle)] bg-[var(--surface-raised)]">
        <div className="flex items-center gap-2">
          <Briefcase className="w-4 h-4 text-blue-500" />
          <span className="font-mono text-xs font-bold uppercase tracking-wider text-[var(--text-primary)]">
            Execution & Risk Governance
          </span>
        </div>

        {/* Tab Switcher */}
        <div className="flex items-center gap-1 bg-[var(--surface)] p-0.5 rounded-lg border border-[var(--border-subtle)]">
          <button
            onClick={() => setTab('positions')}
            className={`px-2.5 py-1 text-xs font-mono rounded-md transition-all ${
              tab === 'positions'
                ? 'bg-blue-600 text-white font-semibold shadow-sm'
                : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
            }`}
          >
            Positions ({positions.length})
          </button>
          <button
            onClick={() => setTab('order')}
            className={`px-2.5 py-1 text-xs font-mono rounded-md transition-all ${
              tab === 'order'
                ? 'bg-blue-600 text-white font-semibold shadow-sm'
                : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
            }`}
          >
            Place Order
          </button>
          <button
            onClick={() => setTab('portfolio')}
            className={`px-2.5 py-1 text-xs font-mono rounded-md transition-all ${
              tab === 'portfolio'
                ? 'bg-blue-600 text-white font-semibold shadow-sm'
                : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
            }`}
          >
            Scorecard
          </button>
          <button
            onClick={() => setTab('history')}
            className={`px-2.5 py-1 text-xs font-mono rounded-md transition-all ${
              tab === 'history'
                ? 'bg-blue-600 text-white font-semibold shadow-sm'
                : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
            }`}
          >
            Tax Ledger
          </button>
        </div>
      </div>

      {/* Tab 1: Active Positions */}
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
                  <th className="py-2.5 px-3">Partial Exit</th>
                  <th className="py-2.5 px-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border-subtle)]">
                {positions.map((pos) => {
                  const isProfit = pos.unrealized_pnl >= 0
                  return (
                    <tr key={pos.symbol} className="hover:bg-blue-500/5 transition-colors">
                      <td className="py-2.5 px-3 font-bold text-[var(--text-primary)]">
                        {pos.symbol}
                      </td>
                      <td className="py-2.5 px-3 text-[var(--text-secondary)] tnum">{pos.quantity}</td>
                      <td className="py-2.5 px-3 tnum">₹{pos.entry_price.toFixed(2)}</td>
                      <td className="py-2.5 px-3 font-semibold text-[var(--text-primary)] tnum">
                        ₹{pos.current_price.toFixed(2)}
                      </td>
                      <td
                        className={`py-2.5 px-3 font-bold tnum ${
                          isProfit ? 'text-[var(--bull)]' : 'text-[var(--bear)]'
                        }`}
                      >
                        {isProfit ? '+' : ''}₹{pos.unrealized_pnl.toFixed(2)} ({isProfit ? '+' : ''}
                        {pos.unrealized_pnl_pct.toFixed(2)}%)
                      </td>
                      <td className="py-2.5 px-3 text-rose-400 tnum">₹{pos.ml_stop_price.toFixed(2)}</td>
                      <td className="py-2.5 px-3 text-blue-400 tnum">₹{pos.ml_target_1.toFixed(2)}</td>
                      <td className="py-2.5 px-3">
                        <span
                          className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${
                            pos.partial_exit_done
                              ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                              : 'bg-slate-500/10 text-[var(--text-muted)]'
                          }`}
                        >
                          {pos.partial_exit_done ? 'Booked 35%' : 'Pending'}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-right">
                        <button
                          onClick={() => handleClosePosition(pos.symbol)}
                          className="px-2 py-1 rounded-md text-[10px] font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20 hover:bg-rose-500/20 transition-all"
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
              No open paper trading positions currently active.
            </div>
          )}
        </div>
      )}

      {/* Tab 2: Manual Simulated Order Placement Form */}
      {tab === 'order' && (
        <form onSubmit={handlePlaceOrder} className="p-4 flex-1 space-y-4 max-w-md">
          {/* Symbol & Direction */}
          <div className="flex items-center justify-between">
            <div>
              <span className="text-[10px] uppercase font-mono text-[var(--text-muted)]">Active Scrip</span>
              <div className="text-base font-mono font-bold text-[var(--text-primary)]">{activeSymbol}</div>
            </div>

            <div className="flex items-center gap-1 bg-[var(--surface-raised)] p-1 rounded-lg border border-[var(--border-subtle)]">
              <button
                type="button"
                onClick={() => setOrderDirection('BUY')}
                className={`px-4 py-1 text-xs font-mono font-bold rounded-md transition-all ${
                  orderDirection === 'BUY'
                    ? 'bg-emerald-600 text-white shadow-sm'
                    : 'text-[var(--text-secondary)] hover:text-emerald-400'
                }`}
              >
                BUY
              </button>
              <button
                type="button"
                onClick={() => setOrderDirection('SELL')}
                className={`px-4 py-1 text-xs font-mono font-bold rounded-md transition-all ${
                  orderDirection === 'SELL'
                    ? 'bg-rose-600 text-white shadow-sm'
                    : 'text-[var(--text-secondary)] hover:text-rose-400'
                }`}
              >
                SELL
              </button>
            </div>
          </div>

          {/* Order Type & Quantity Inputs */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-[10px] uppercase font-mono text-[var(--text-muted)] block pb-1">
                Order Type
              </label>
              <select
                value={orderType}
                onChange={(e) => setOrderType(e.target.value as any)}
                className="w-full bg-[var(--surface-raised)] border border-[var(--border-subtle)] rounded-lg px-3 py-1.5 text-xs font-mono text-[var(--text-primary)] outline-none"
              >
                <option value="MARKET">MARKET</option>
                <option value="LIMIT">LIMIT</option>
              </select>
            </div>

            <div>
              <label className="text-[10px] uppercase font-mono text-[var(--text-muted)] block pb-1">
                Shares Quantity (or Auto)
              </label>
              <input
                type="number"
                placeholder="Auto-Sized"
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
                className="w-full bg-[var(--surface-raised)] border border-[var(--border-subtle)] focus:border-blue-500 rounded-lg px-3 py-1.5 text-xs font-mono text-[var(--text-primary)] placeholder-[var(--text-muted)] outline-none tnum"
              />
            </div>
          </div>

          {orderType === 'LIMIT' && (
            <div>
              <label className="text-[10px] uppercase font-mono text-[var(--text-muted)] block pb-1">
                Limit Price (₹)
              </label>
              <input
                type="number"
                step="0.05"
                placeholder="Limit Price..."
                value={limitPrice}
                onChange={(e) => setLimitPrice(e.target.value)}
                className="w-full bg-[var(--surface-raised)] border border-[var(--border-subtle)] focus:border-blue-500 rounded-lg px-3 py-1.5 text-xs font-mono text-[var(--text-primary)] outline-none tnum"
              />
            </div>
          )}

          {/* Feedback Messages */}
          {orderMsg && (
            <div
              className={`p-2.5 rounded-xl text-xs font-mono flex items-center gap-2 border ${
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
            className={`w-full py-2.5 rounded-xl font-mono text-xs font-bold uppercase tracking-wider text-white shadow-lg transition-all ${
              orderDirection === 'BUY'
                ? 'bg-emerald-600 hover:bg-emerald-500'
                : 'bg-rose-600 hover:bg-rose-500'
            } disabled:opacity-50 disabled:pointer-events-none`}
          >
            {isSubmitting ? 'Simulating Execution...' : `Execute Simulated ${orderDirection}`}
          </button>
        </form>
      )}

      {/* Tab 3: Portfolio Scorecard */}
      {tab === 'portfolio' && portfolio && (
        <div className="p-4 flex-1 overflow-y-auto space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 font-mono">
            <div className="p-3 rounded-xl bg-[var(--surface-raised)] border border-[var(--border-subtle)]">
              <span className="text-[10px] text-[var(--text-muted)] uppercase">Total Equity</span>
              <div className="text-base font-bold text-[var(--text-primary)] pt-1 tnum">
                ₹{portfolio.total_portfolio_value.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
              </div>
            </div>

            <div className="p-3 rounded-xl bg-[var(--surface-raised)] border border-[var(--border-subtle)]">
              <span className="text-[10px] text-[var(--text-muted)] uppercase">Available Cash</span>
              <div className="text-base font-bold text-[var(--text-primary)] pt-1 tnum">
                ₹{portfolio.current_cash.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
              </div>
            </div>

            <div className="p-3 rounded-xl bg-[var(--surface-raised)] border border-[var(--border-subtle)]">
              <span className="text-[10px] text-[var(--text-muted)] uppercase">Realized P&L</span>
              <div
                className={`text-base font-bold pt-1 tnum ${
                  portfolio.total_realized_pnl >= 0 ? 'text-[var(--bull)]' : 'text-[var(--bear)]'
                }`}
              >
                {portfolio.total_realized_pnl >= 0 ? '+' : ''}₹{portfolio.total_realized_pnl.toFixed(2)}
              </div>
            </div>

            <div className="p-3 rounded-xl bg-[var(--surface-raised)] border border-[var(--border-subtle)]">
              <span className="text-[10px] text-[var(--text-muted)] uppercase">Total Return</span>
              <div
                className={`text-base font-bold pt-1 tnum ${
                  portfolio.total_return_pct >= 0 ? 'text-[var(--bull)]' : 'text-[var(--bear)]'
                }`}
              >
                {portfolio.total_return_pct >= 0 ? '+' : ''}
                {portfolio.total_return_pct.toFixed(2)}%
              </div>
            </div>
          </div>

          {/* Governance Safeguards */}
          <div className="p-3.5 rounded-xl bg-[var(--surface-raised)] border border-[var(--border-subtle)] flex items-center justify-between font-mono text-xs">
            <div className="flex items-center gap-2">
              {portfolio.circuit_breaker_tripped ? (
                <ShieldAlert className="w-4 h-4 text-rose-400" />
              ) : (
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
              )}
              <span>Daily Circuit Breaker (-3% Max Drawdown Halt)</span>
            </div>
            <span
              className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                portfolio.circuit_breaker_tripped
                  ? 'bg-rose-500/10 text-rose-400 border border-rose-500/30'
                  : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
              }`}
            >
              {portfolio.circuit_breaker_tripped ? 'TRIPPED (HALTED)' : 'ACTIVE & SAFE'}
            </span>
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
                  <th className="py-2 px-3">Symbol</th>
                  <th className="py-2 px-3">Exit Time</th>
                  <th className="py-2 px-3">Hold Days</th>
                  <th className="py-2 px-3">Gross P&L</th>
                  <th className="py-2 px-3">Statutory Frictions</th>
                  <th className="py-2 px-3">Tax (STCG/LTCG)</th>
                  <th className="py-2 px-3">Net Realized P&L</th>
                  <th className="py-2 px-3">Exit Reason</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border-subtle)]">
                {trades.map((t) => {
                  const isProfit = t.net_pnl >= 0
                  return (
                    <tr key={t.trade_id} className="hover:bg-blue-500/5 transition-colors">
                      <td className="py-2 px-3 font-bold text-[var(--text-primary)]">{t.symbol}</td>
                      <td className="py-2 px-3 text-[var(--text-secondary)]">{t.exit_time?.split('T')[0]}</td>
                      <td className="py-2 px-3 text-[var(--text-secondary)] tnum">{t.holding_days}d</td>
                      <td className="py-2 px-3 tnum">₹{t.gross_pnl.toFixed(2)}</td>
                      <td className="py-2 px-3 text-rose-400 tnum">₹{t.total_transaction_frictions.toFixed(2)}</td>
                      <td className="py-2 px-3 text-amber-400 tnum">
                        ₹{t.capital_gains_tax.toFixed(2)} ({t.tax_type})
                      </td>
                      <td
                        className={`py-2 px-3 font-bold tnum ${
                          isProfit ? 'text-[var(--bull)]' : 'text-[var(--bear)]'
                        }`}
                      >
                        {isProfit ? '+' : ''}₹{t.net_pnl.toFixed(2)} ({isProfit ? '+' : ''}
                        {t.net_pnl_pct.toFixed(2)}%)
                      </td>
                      <td className="py-2 px-3 text-[var(--text-muted)] text-[10px]">{t.exit_trigger}</td>
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
