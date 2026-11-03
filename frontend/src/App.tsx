import React, { useState, useEffect } from 'react'
import { Header } from './components/Header'
import { TradingViewChart } from './components/Chart/TradingViewChart'
import { AIPanel } from './components/AIPanel/AIPanel'
import { TradingPanel } from './components/Trading/TradingPanel'
import { TopUniverseDrawer } from './components/Universe/TopUniverseDrawer'
import { SectorHeatmapModal } from './components/Universe/SectorHeatmapModal'
import { SystemModal } from './components/System/SystemModal'
import { ParticleBackdrop } from './components/ParticleBackdrop'
import { api } from './services/api'
import { wsService } from './services/websocket'
import {
  StockQuote,
  SystemHealth,
  MarketBreadth,
  CorridorForecast,
  AISignalResponse,
  ScreenerCandidateItem,
  PortfolioSummaryResponse,
  PositionItem,
  TradeItem,
  TopUniverseItem
} from './types'

export const App: React.FC = () => {
  const [activeSymbol, setActiveSymbol] = useState<string>('RELIANCE')
  const [quote, setQuote] = useState<StockQuote | null>(null)
  const [health, setHealth] = useState<SystemHealth | null>(null)
  const [breadth, setBreadth] = useState<MarketBreadth | null>(null)
  const [corridor, setCorridor] = useState<CorridorForecast | null>(null)
  const [signal, setSignal] = useState<AISignalResponse | null>(null)
  const [screenerList, setScreenerList] = useState<ScreenerCandidateItem[]>([])
  const [portfolio, setPortfolio] = useState<PortfolioSummaryResponse | null>(null)
  const [positions, setPositions] = useState<PositionItem[]>([])
  const [trades, setTrades] = useState<TradeItem[]>([])
  const [universe, setUniverse] = useState<TopUniverseItem[]>([])

  const [isUniverseDrawerOpen, setIsUniverseDrawerOpen] = useState(false)
  const [isHeatmapOpen, setIsHeatmapOpen] = useState(false)
  const [isSystemModalOpen, setIsSystemModalOpen] = useState(false)
  const [isWsConnected, setIsWsConnected] = useState(false)
  const [isRefreshing, setIsRefreshing] = useState(false)

  // 1. Initial Load of Global Data
  const loadGlobalData = async () => {
    try {
      const [h, b, port, pos, tr, univ, scr] = await Promise.allSettled([
        api.getSystemHealth(),
        api.getMarketBreadth(),
        api.getPortfolioSummary(),
        api.getActivePositions(),
        api.getTradeHistory(50),
        api.getTopUniverse(300),
        api.getScreenerWatchlist(),
      ])

      if (h.status === 'fulfilled') setHealth(h.value)
      if (b.status === 'fulfilled') setBreadth(b.value)
      if (port.status === 'fulfilled') setPortfolio(port.value)
      if (pos.status === 'fulfilled') setPositions(pos.value)
      if (tr.status === 'fulfilled') setTrades(tr.value)
      if (univ.status === 'fulfilled') setUniverse(univ.value)
      if (scr.status === 'fulfilled') setScreenerList(scr.value)
    } catch (e) {
      console.error('Error fetching global telemetry:', e)
    }
  }

  // 2. Load Stock Specific Data
  const loadStockData = async (symbol: string) => {
    // Clear previous stock's corridor and signal immediately so new stock values reload cleanly
    setCorridor(null)
    setSignal(null)
    try {
      const [q, corr, sig] = await Promise.allSettled([
        api.getStockQuote(symbol),
        api.getCorridorForecast(symbol),
        api.getAISignal(symbol),
      ])

      if (q.status === 'fulfilled') setQuote(q.value)
      if (corr.status === 'fulfilled') setCorridor(corr.value)
      if (sig.status === 'fulfilled') setSignal(sig.value)
    } catch (e) {
      console.error(`Error fetching stock data for ${symbol}:`, e)
    }
  }

  // Manual Trigger to re-fetch all active quotes, models & telemetry
  const handleManualRefresh = async () => {
    setIsRefreshing(true)
    try {
      await Promise.allSettled([
        loadGlobalData(),
        loadStockData(activeSymbol),
      ])
    } finally {
      setTimeout(() => setIsRefreshing(false), 400)
    }
  }

  useEffect(() => {
    loadGlobalData()
  }, [])

  useEffect(() => {
    loadStockData(activeSymbol)
    wsService.subscribeSymbol(activeSymbol)
  }, [activeSymbol])

  // 3. Setup WebSocket Connection & Event Handlers
  useEffect(() => {
    wsService.connect()

    const checkInterval = setInterval(() => {
      setIsWsConnected(wsService.getStatus())
    }, 2000)

    // Handle live ticks
    const unsubscribeLive = wsService.subscribeLive((msg) => {
      if (msg.type === 'TICK' && msg.data) {
        const tick = msg.data
        if (tick.symbol === activeSymbol) {
          setQuote((prev) => {
            if (!prev) return prev
            const newLtp = Number(tick.ltp || tick.close || prev.ltp)
            const openPx = Number(prev.open || prev.close || newLtp)
            const newChange = Number((newLtp - openPx).toFixed(2))
            const newChangePct = openPx > 0 ? Number(((newChange / openPx) * 100).toFixed(2)) : (prev.pct_change || 0)
            return {
              ...prev,
              ltp: newLtp,
              change: newChange,
              change_pct: newChangePct,
              pct_change: newChangePct,
              high: Math.max(Number(prev.high) || 0, newLtp),
              low: Math.min(Number(prev.low) || newLtp, newLtp),
              volume: Number(tick.volume) || prev.volume,
            }
          })
        }
      }
    })

    // Handle trade execution alerts
    const unsubscribeTrades = wsService.subscribeTrades((msg) => {
      if (msg.type === 'TRADE_EVENT') {
        // Refresh positions and portfolio summary
        api.getPortfolioSummary().then(setPortfolio).catch(() => {})
        api.getActivePositions().then(setPositions).catch(() => {})
        api.getTradeHistory(50).then(setTrades).catch(() => {})
      }
    })

    return () => {
      clearInterval(checkInterval)
      unsubscribeLive()
      unsubscribeTrades()
    }
  }, [activeSymbol])

  return (
    <div className="relative min-h-screen flex flex-col bg-[var(--canvas)] text-[var(--text-primary)] transition-colors duration-200">
      {/* Ambient 3D Particle Constellation */}
      <ParticleBackdrop />

      {/* Global Header */}
      <Header
        quote={quote}
        health={health}
        breadth={breadth}
        signal={signal}
        activeSymbol={activeSymbol}
        onSelectSymbol={setActiveSymbol}
        onOpenSystemModal={() => setIsSystemModalOpen(true)}
        onToggleUniverseDrawer={() => setIsUniverseDrawerOpen(true)}
        onOpenSectorHeatmap={() => setIsHeatmapOpen(true)}
        onRefresh={handleManualRefresh}
        isRefreshing={isRefreshing}
        isWsConnected={isWsConnected}
      />

      {/* Main Workspace Layout */}
      <main className="relative z-10 flex-1 max-w-[1920px] w-full mx-auto p-3 md:p-4 grid grid-cols-1 lg:grid-cols-12 gap-3 md:gap-4">
        
        {/* Left Column: Charting Canvas & Trading Governance (8 Cols) */}
        <div className="lg:col-span-8 flex flex-col gap-3 md:gap-4">
          {/* Candlestick Chart Pane with Dynamic Sizing */}
          <div className="h-[490px] md:h-[530px] flex flex-col">
            <TradingViewChart symbol={activeSymbol} corridor={corridor} quote={quote} />
          </div>

          {/* Execution & Risk Governance Pane */}
          <div className="h-[360px] md:h-[390px]">
            <TradingPanel
              portfolio={portfolio}
              positions={positions}
              trades={trades}
              activeSymbol={activeSymbol}
              onRefreshData={() => {
                api.getPortfolioSummary().then(setPortfolio).catch(() => {})
                api.getActivePositions().then(setPositions).catch(() => {})
                api.getTradeHistory(50).then(setTrades).catch(() => {})
              }}
            />
          </div>
        </div>

        {/* Right Column: AI Quantitative Intelligence (4 Cols) */}
        <div className="lg:col-span-4 h-full min-h-[500px]">
          <AIPanel
            symbol={activeSymbol}
            corridor={corridor}
            signal={signal}
            screenerList={screenerList}
            onSelectSymbol={setActiveSymbol}
            onRefresh={handleManualRefresh}
            isRefreshing={isRefreshing}
          />
        </div>

      </main>

      {/* Top 300 Institutional Universe Drawer */}
      <TopUniverseDrawer
        isOpen={isUniverseDrawerOpen}
        onClose={() => setIsUniverseDrawerOpen(false)}
        universe={universe}
        activeSymbol={activeSymbol}
        onSelectSymbol={setActiveSymbol}
      />

      {/* Sector Momentum Heatmap & Strong Buy Modal */}
      <SectorHeatmapModal
        isOpen={isHeatmapOpen}
        onClose={() => setIsHeatmapOpen(false)}
        onSelectSymbol={setActiveSymbol}
      />

      {/* Engine Telemetry & Lakehouse Sync Modal */}
      <SystemModal
        isOpen={isSystemModalOpen}
        onClose={() => setIsSystemModalOpen(false)}
        health={health}
        onRefreshHealth={() => api.getSystemHealth().then(setHealth).catch(() => {})}
      />
    </div>
  )
}

export default App

