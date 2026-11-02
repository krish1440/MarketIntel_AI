import React, { Component, ErrorInfo, ReactNode } from 'react'
import { AlertTriangle, RefreshCw } from 'lucide-react'

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  }

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo)
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-[#090a0f] text-white flex items-center justify-center p-6">
          <div className="max-w-md w-full p-6 rounded-2xl bg-[#111318] border border-rose-500/30 text-center space-y-4">
            <div className="w-12 h-12 rounded-full bg-rose-500/10 border border-rose-500/30 flex items-center justify-center mx-auto text-rose-400">
              <AlertTriangle className="w-6 h-6" />
            </div>
            <h2 className="text-lg font-bold font-mono">Render Issue Detected</h2>
            <p className="text-xs text-slate-400 font-mono">
              {this.state.error?.message || 'An unexpected client-side error occurred.'}
            </p>
            <button
              onClick={() => window.location.reload()}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-xs font-mono font-bold transition-all"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              Reload Platform
            </button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}

