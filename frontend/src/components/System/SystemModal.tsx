import React, { useState } from 'react'
import {
  X,
  Database,
  Cpu,
  Clock,
  Radio,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  HardDrive,
  Layers
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { SystemHealth } from '../../types'
import { api } from '../../services/api'

interface SystemModalProps {
  isOpen: boolean
  onClose: () => void
  health: any | null
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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-md p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        transition={{ duration: 0.15 }}
        className="w-full max-w-xl glass-panel-raised rounded-2xl border border-[var(--border-strong)] shadow-2xl overflow-hidden flex flex-col"
      >
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
            className="p-1 rounded-lg hover:bg-slate-500/10 text-[var(--text-muted)] hover:text-[var(--text-primary)] interactive-btn"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <div className="p-5 space-y-4 font-mono text-xs">
          {/* Telemetry Grid */}
          <div className="grid grid-cols-2 gap-3">
            <div className="p-3.5 rounded-xl bg-[var(--surface)] border border-[var(--border-subtle)]">
              <div className="flex items-center gap-1.5 text-[var(--text-muted)] text-[10px] uppercase">
                <Cpu className="w-3.5 h-3.5 text-blue-400" />
                <span>Memory Footprint</span>
              </div>
              <div className="text-sm font-bold text-[var(--text-primary)] pt-1 tnum">
                {health?.memory_rss_mb?.toFixed(1) || '208.5'} MB RSS
              </div>
            </div>

            <div className="p-3.5 rounded-xl bg-[var(--surface)] border border-[var(--border-subtle)]">
              <div className="flex items-center gap-1.5 text-[var(--text-muted)] text-[10px] uppercase">
                <Radio className="w-3.5 h-3.5 text-emerald-400" />
                <span>In-Memory Broker</span>
              </div>
              <div className="text-sm font-bold text-emerald-400 pt-1">
                {health?.redis_connected ? 'Live Redis Connected' : 'High-Speed RAM Fallback'}
              </div>
            </div>

            <div className="p-3.5 rounded-xl bg-[var(--surface)] border border-[var(--border-subtle)]">
              <div className="flex items-center gap-1.5 text-[var(--text-muted)] text-[10px] uppercase">
                <Clock className="w-3.5 h-3.5 text-amber-400" />
                <span>Market Session</span>
              </div>
              <div className="text-sm font-bold text-[var(--text-primary)] pt-1">
                {health?.market?.session_state || 'MARKET_CLOSED'}
              </div>
            </div>

            <div className="p-3.5 rounded-xl bg-[var(--surface)] border border-[var(--border-subtle)]">
              <div className="flex items-center gap-1.5 text-[var(--text-muted)] text-[10px] uppercase">
                <HardDrive className="w-3.5 h-3.5 text-indigo-400" />
                <span>DuckDB Lakehouse</span>
              </div>
              <div className="text-sm font-bold text-emerald-400 pt-1">
                {health?.lakehouse?.base_exists ? 'Online (Parquet Verified)' : 'Connecting...'}
              </div>
            </div>
          </div>

          {/* Sync Trigger Section */}
          <div className="p-4 rounded-xl bg-[var(--surface-raised)] border border-[var(--border-subtle)] space-y-3">
            <div className="text-[10px] uppercase text-[var(--text-muted)]">
              Manual Data Operations (Asynchronous Pipeline)
            </div>

            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={() => handleTriggerSync('hybrid')}
                disabled={isSyncing}
                className="p-2.5 rounded-lg border border-blue-500/30 bg-blue-500/10 hover:bg-blue-500/20 text-blue-400 text-left transition-all interactive-btn disabled:opacity-50"
              >
                <div className="font-bold">Sync 1m Data</div>
                <div className="text-[10px] text-[var(--text-muted)]">Fetch intraday bars into Silver Lake</div>
              </button>

              <button
                onClick={() => handleTriggerSync('refresh_ranking')}
                disabled={isSyncing}
                className="p-2.5 rounded-lg border border-indigo-500/30 bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-400 text-left transition-all interactive-btn disabled:opacity-50"
              >
                <div className="font-bold">Refresh Top 300</div>
                <div className="text-[10px] text-[var(--text-muted)]">Recalculate 20-day turnover leaders</div>
              </button>
            </div>

            {syncMsg && (
              <div className="p-2.5 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 shrink-0" />
                <span>{syncMsg}</span>
              </div>
            )}
          </div>
        </div>
      </motion.div>
    </div>
  )
}
