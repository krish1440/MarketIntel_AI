import React, { useState } from 'react'
import {
  X,
  Database,
  Cpu,
  Clock,
  Radio,
  RefreshCw,
  CheckCircle2,
  AlertCircle
} from 'lucide-react'
import { SystemHealth } from '../../types'
import { api } from '../../services/api'

interface SystemModalProps {
  isOpen: boolean
  onClose: () => void
  health: SystemHealth | null
  onRefreshHealth: () => void
}

export const SystemModal: React.FC<SystemModalProps> = ({
  isOpen,
  onClose,
  health,
  onRefreshHealth,
}) => {
  const [syncMsg, setSyncMsg] = useState<string | null>(null)
  const [isSyncing, setIsSyncing] = useState(false)

  if (!isOpen) return null

  const handleTriggerSync = async (mode: 'daily' | 'hybrid' | 'refresh_ranking') => {
    setIsSyncing(true)
    setSyncMsg(null)
    try {
      const res = await api.triggerSync(mode)
      setSyncMsg(res.message)
      setTimeout(onRefreshHealth, 2000)
    } catch (e: any) {
      setSyncMsg(`Sync failed: ${e.message}`)
    } finally {
      setIsSyncing(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="w-full max-w-xl glass-panel-raised rounded-2xl border border-[var(--border-strong)] shadow-2xl overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-[var(--border-subtle)] bg-[var(--surface-raised)]">
          <div className="flex items-center gap-2">
            <Database className="w-4 h-4 text-blue-500" />
            <span className="font-mono text-sm font-bold text-[var(--text-primary)]">
              Engine Telemetry & Lakehouse Operations
            </span>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-slate-500/10 text-[var(--text-muted)] hover:text-[var(--text-primary)]"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <div className="p-5 space-y-4 font-mono text-xs">
          {/* Telemetry Grid */}
          <div className="grid grid-cols-2 gap-3">
            <div className="p-3 rounded-xl bg-[var(--surface)] border border-[var(--border-subtle)]">
              <div className="flex items-center gap-1.5 text-[var(--text-muted)] text-[10px] uppercase">
                <Cpu className="w-3.5 h-3.5 text-blue-400" />
                <span>Memory Footprint</span>
              </div>
              <div className="text-sm font-bold text-[var(--text-primary)] pt-1 tnum">
                {health?.memory_rss_mb || '—'} MB RSS
              </div>
            </div>

            <div className="p-3 rounded-xl bg-[var(--surface)] border border-[var(--border-subtle)]">
              <div className="flex items-center gap-1.5 text-[var(--text-muted)] text-[10px] uppercase">
                <Radio className="w-3.5 h-3.5 text-emerald-400" />
                <span>In-Memory Broker</span>
              </div>
              <div className="text-sm font-bold text-emerald-400 pt-1">
                {health?.redis_connected ? 'Live Redis Connected' : 'High-Speed RAM Fallback'}
              </div>
            </div>

            <div className="p-3 rounded-xl bg-[var(--surface)] border border-[var(--border-subtle)]">
              <div className="flex items-center gap-1.5 text-[var(--text-muted)] text-[10px] uppercase">
                <Clock className="w-3.5 h-3.5 text-amber-400" />
                <span>Market Session</span>
              </div>
              <div className="text-sm font-bold text-[var(--text-primary)] pt-1">
                {health?.market.session_state || '—'}
              </div>
            </div>

            <div className="p-3 rounded-xl bg-[var(--surface)] border border-[var(--border-subtle)]">
              <div className="flex items-center gap-1.5 text-[var(--text-muted)] text-[10px] uppercase">
                <Database className="w-3.5 h-3.5 text-indigo-400" />
                <span>Lakehouse Parity</span>
              </div>
              <div className="text-sm font-bold text-[var(--text-primary)] pt-1 tnum">
                {health?.lakehouse.silver_1d_stocks || 0} / 2,357 Equities
              </div>
            </div>
          </div>

          {/* Lakehouse Background Sync Triggers */}
          <div className="pt-2 border-t border-[var(--border-subtle)] space-y-2">
            <span className="text-[10px] uppercase text-[var(--text-muted)] tracking-wider">
              Trigger Automated Lakehouse Synchronization
            </span>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 pt-1">
              <button
                onClick={() => handleTriggerSync('daily')}
                disabled={isSyncing || (health?.execution.orchestrator_running ?? false)}
                className="px-3 py-2 rounded-xl border border-[var(--border-subtle)] bg-[var(--surface)] hover:border-blue-500/50 text-[var(--text-primary)] text-left transition-colors disabled:opacity-50"
              >
                <div className="font-bold text-[11px]">Daily 1D Sync</div>
                <div className="text-[9px] text-[var(--text-muted)]">All 2,357 Equities</div>
              </button>

              <button
                onClick={() => handleTriggerSync('hybrid')}
                disabled={isSyncing || (health?.execution.orchestrator_running ?? false)}
                className="px-3 py-2 rounded-xl border border-[var(--border-subtle)] bg-[var(--surface)] hover:border-blue-500/50 text-[var(--text-primary)] text-left transition-colors disabled:opacity-50"
              >
                <div className="font-bold text-[11px]">Intraday 1M Sync</div>
                <div className="text-[9px] text-[var(--text-muted)]">Top 300 Leaders</div>
              </button>

              <button
                onClick={() => handleTriggerSync('refresh_ranking')}
                disabled={isSyncing || (health?.execution.orchestrator_running ?? false)}
                className="px-3 py-2 rounded-xl border border-[var(--border-subtle)] bg-[var(--surface)] hover:border-blue-500/50 text-[var(--text-primary)] text-left transition-colors disabled:opacity-50"
              >
                <div className="font-bold text-[11px]">Re-Rank Top 300</div>
                <div className="text-[9px] text-[var(--text-muted)]">20D Volume ≥ ₹2 Cr</div>
              </button>
            </div>
          </div>

          {/* Sync Feedback Message */}
          {syncMsg && (
            <div className="p-2.5 rounded-xl bg-blue-500/10 border border-blue-500/30 text-blue-400 text-xs flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>{syncMsg}</span>
            </div>
          )}

          {health?.execution.orchestrator_running && (
            <div className="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-400 text-xs flex items-center gap-2">
              <RefreshCw className="w-4 h-4 animate-spin shrink-0" />
              <span>Background gap orchestrator is currently actively running.</span>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
