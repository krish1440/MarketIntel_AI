import React, { useEffect, useRef, useState, useMemo } from 'react'
import {
  createChart,
  CandlestickSeries,
  HistogramSeries,
  LineSeries,
  IChartApi,
  CandlestickData,
  HistogramData,
  LineData,
  Time
} from 'lightweight-charts'
import { CandleItem, CorridorForecast, StockQuote } from '../../types'
import { api } from '../../services/api'
import { wsService } from '../../services/websocket'
import { Loader2, TrendingUp, Layers, Eye, Activity, Sparkles, Clock } from 'lucide-react'

interface TradingViewChartProps {
  symbol: string
  corridor: CorridorForecast | null
  quote?: StockQuote | null
}

const TIMEFRAMES = [
  { label: '1m', value: '1m' },
  { label: '5m', value: '5m' },
  { label: '15m', value: '15m' },
  { label: '1h', value: '1h' },
  { label: '1D', value: '1d' },
]

function computeEMA(candles: CandleItem[], period: number): LineData<Time>[] {
  if (candles.length < period) return []
  const k = 2 / (period + 1)
  const result: LineData<Time>[] = []
  let ema = candles[0].close

  for (let i = 0; i < candles.length; i++) {
    const c = candles[i]
    if (i === 0) {
      ema = c.close
    } else {
      ema = c.close * k + ema * (1 - k)
    }
    if (i >= period - 1) {
      result.push({ time: c.time as Time, value: Number(ema.toFixed(2)) })
    }
  }
  return result
}

function computeVWAP(candles: CandleItem[]): LineData<Time>[] {
  const result: LineData<Time>[] = []
  let cumVol = 0
  let cumPV = 0

  for (let i = 0; i < candles.length; i++) {
    const c = candles[i]
    const typicalPrice = (c.high + c.low + c.close) / 3
    const vol = c.volume || 1
    cumPV += typicalPrice * vol
    cumVol += vol
    result.push({
      time: c.time as Time,
      value: Number((cumPV / cumVol).toFixed(2)),
    })
  }
  return result
}

export const TradingViewChart: React.FC<TradingViewChartProps> = ({ symbol, corridor, quote }) => {
  const chartContainerRef = useRef<HTMLDivElement | null>(null)
  const chartInstance = useRef<IChartApi | null>(null)
  const candleSeries = useRef<any>(null)
  const volumeSeries = useRef<any>(null)
  const ema20Series = useRef<any>(null)
  const ema50Series = useRef<any>(null)
  const vwapSeries = useRef<any>(null)
  const activePriceLines = useRef<any[]>([])

  const [timeframe, setTimeframe] = useState<string>('5m')
  const [isLoading, setIsLoading] = useState<boolean>(true)
  const [candles, setCandles] = useState<CandleItem[]>([])

  // Technical Indicators Toggles
  const [showEMA20, setShowEMA20] = useState<boolean>(true)
  const [showEMA50, setShowEMA50] = useState<boolean>(false)
  const [showVWAP, setShowVWAP] = useState<boolean>(true)

  // Floating Crosshair Hover Legend
  const [hoverData, setHoverData] = useState<{
    time?: number
    open: number
    high: number
    low: number
    close: number
    volume?: number
  } | null>(null)

  // Load candle data from backend
  const loadCandles = async (sym: string, tf: string) => {
    setIsLoading(true)
    try {
      const res = await api.getChartCandles(sym, tf, 500)
      setCandles(res.candles || [])
    } catch (e) {
      console.error(`Failed to load candles for ${sym} (${tf}):`, e)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadCandles(symbol, timeframe)
  }, [symbol, timeframe])

  // Dynamic Browser Tab Title updating with live price
  useEffect(() => {
    const currentPx = quote?.ltp || (candles.length > 0 ? candles[candles.length - 1].close : null)
    if (currentPx) {
      document.title = `₹${currentPx.toLocaleString('en-IN', { minimumFractionDigits: 2 })} | ${symbol} - MarketIntel AI`
    } else {
      document.title = `${symbol} - MarketIntel AI`
    }
  }, [symbol, quote?.ltp, candles])

  // Initialize and update Lightweight Charts with precision height sizing
  useEffect(() => {
    if (!chartContainerRef.current) return

    const isDark = document.documentElement.classList.contains('dark')
    const bgColor = isDark ? '#0c1017' : '#ffffff'
    const textColor = isDark ? '#94a3b8' : '#475569'
    const gridColor = isDark ? 'rgba(255, 255, 255, 0.03)' : 'rgba(0, 0, 0, 0.03)'

    // Clear existing chart
    if (chartInstance.current) {
      chartInstance.current.remove()
      chartInstance.current = null
    }

    try {
      const rect = chartContainerRef.current.getBoundingClientRect()
      const initialHeight = Math.max(rect.height, 360)

      const chart = createChart(chartContainerRef.current, {
        width: rect.width || chartContainerRef.current.clientWidth,
        height: initialHeight,
        layout: {
          background: { color: bgColor },
          textColor: textColor,
          fontFamily: "'JetBrains Mono', 'Inter', monospace",
          fontSize: 11,
        },
        grid: {
          vertLines: { color: gridColor },
          horzLines: { color: gridColor },
        },
        crosshair: {
          mode: 1, // Magnet
        },
        rightPriceScale: {
          borderColor: isDark ? 'rgba(255, 255, 255, 0.08)' : 'rgba(0, 0, 0, 0.08)',
          scaleMargins: {
            top: 0.1,
            bottom: 0.22, // Space for volume
          },
        },
        localization: {
          locale: 'en-IN',
          dateFormat: 'yyyy-MM-dd',
          timeFormatter: (timestamp: number) => {
            const d = new Date(timestamp * 1000)
            return d.toLocaleTimeString('en-IN', {
              timeZone: 'Asia/Kolkata',
              hour: '2-digit',
              minute: '2-digit',
              hour12: false,
            }) + ' IST'
          },
        },
        timeScale: {
          borderColor: isDark ? 'rgba(255, 255, 255, 0.08)' : 'rgba(0, 0, 0, 0.08)',
          timeVisible: true,
          secondsVisible: false,
          tickMarkFormatter: (time: number) => {
            const d = new Date(time * 1000)
            if (timeframe === '1d') {
              return d.toLocaleDateString('en-IN', {
                timeZone: 'Asia/Kolkata',
                day: '2-digit',
                month: 'short',
              })
            }
            return d.toLocaleTimeString('en-IN', {
              timeZone: 'Asia/Kolkata',
              hour: '2-digit',
              minute: '2-digit',
              hour12: false,
            })
          },
        },
      })

      // Candlestick Series (Lightweight Charts v5)
      const candle = chart.addSeries(CandlestickSeries, {
        upColor: isDark ? '#10b981' : '#059669',
        downColor: isDark ? '#f43f5e' : '#e11d48',
        borderVisible: false,
        wickUpColor: isDark ? '#10b981' : '#059669',
        wickDownColor: isDark ? '#f43f5e' : '#e11d48',
      })

      // Volume Series
      const volume = chart.addSeries(HistogramSeries, {
        priceFormat: {
          type: 'volume',
        },
        priceScaleId: '', // Overlay over price scale
      })

      volume.priceScale().applyOptions({
        scaleMargins: {
          top: 0.78, // Align volume to bottom 22%
          bottom: 0,
        },
      })

      // Technical Overlays
      const ema20 = chart.addSeries(LineSeries, {
        color: '#06b6d4',
        lineWidth: 2,
        title: 'EMA 20',
        crosshairMarkerVisible: false,
      })

      const ema50 = chart.addSeries(LineSeries, {
        color: '#f59e0b',
        lineWidth: 2,
        title: 'EMA 50',
        crosshairMarkerVisible: false,
      })

      const vwap = chart.addSeries(LineSeries, {
        color: '#a855f7',
        lineWidth: 2,
        title: 'VWAP',
        crosshairMarkerVisible: false,
      })

      // Floating Crosshair Move Listener
      chart.subscribeCrosshairMove((param) => {
        if (param.time && candle) {
          const d = param.seriesData.get(candle) as any
          if (d && d.close !== undefined) {
            setHoverData({
              time: typeof param.time === 'number' ? param.time : undefined,
              open: d.open,
              high: d.high,
              low: d.low,
              close: d.close,
            })
            return
          }
        }
        setHoverData(null)
      })

      chartInstance.current = chart
      candleSeries.current = candle
      volumeSeries.current = volume
      ema20Series.current = ema20
      ema50Series.current = ema50
      vwapSeries.current = vwap
    } catch (err) {
      console.error('Failed to initialize TradingView chart:', err)
    }

    // Precision Resize Observer to prevent bottom cropping
    const handleResize = () => {
      if (chartContainerRef.current && chartInstance.current) {
        const rect = chartContainerRef.current.getBoundingClientRect()
        if (rect.width > 0 && rect.height > 0) {
          chartInstance.current.applyOptions({
            width: rect.width,
            height: rect.height,
          })
        }
      }
    }

    const ro = new ResizeObserver(handleResize)
    ro.observe(chartContainerRef.current)

    return () => {
      ro.disconnect()
      if (chartInstance.current) {
        chartInstance.current.remove()
        chartInstance.current = null
      }
    }
  }, [timeframe])

  // Populate Candlesticks, Volume, and Indicators
  useEffect(() => {
    if (!candleSeries.current || !volumeSeries.current || candles.length === 0) return

    const formattedCandles: CandlestickData<Time>[] = []
    const formattedVolumes: HistogramData<Time>[] = []
    const isDark = document.documentElement.classList.contains('dark')

    candles.forEach((c) => {
      const timeVal = c.time as Time
      formattedCandles.push({
        time: timeVal,
        open: c.open,
        high: c.high,
        low: c.low,
        close: c.close,
      })

      const isUp = c.close >= c.open
      formattedVolumes.push({
        time: timeVal,
        value: c.volume,
        color: isUp
          ? isDark
            ? 'rgba(16, 185, 129, 0.25)'
            : 'rgba(5, 150, 105, 0.25)'
          : isDark
          ? 'rgba(244, 63, 94, 0.25)'
          : 'rgba(225, 29, 72, 0.25)',
      })
    })

    try {
      candleSeries.current.setData(formattedCandles)
      volumeSeries.current.setData(formattedVolumes)

      // Technical Overlays Calculation
      if (ema20Series.current) {
        ema20Series.current.setData(showEMA20 ? computeEMA(candles, 20) : [])
      }
      if (ema50Series.current) {
        ema50Series.current.setData(showEMA50 ? computeEMA(candles, 50) : [])
      }
      if (vwapSeries.current) {
        vwapSeries.current.setData(showVWAP ? computeVWAP(candles) : [])
      }

      // Add horizontal price corridor lines if available
      if (corridor && candleSeries.current) {
        try {
          // Remove previous price lines to avoid duplicates
          activePriceLines.current.forEach((line) => {
            try {
              candleSeries.current.removePriceLine(line)
            } catch (e) {}
          })
          activePriceLines.current = []

          // P05 Floor
          if (corridor.p05_floor && corridor.p05_floor > 0) {
            const l = candleSeries.current.createPriceLine({
              price: corridor.p05_floor,
              color: '#f43f5e',
              lineWidth: 1,
              lineStyle: 2, // Dashed
              axisLabelVisible: true,
              title: 'P05 Stop',
            })
            activePriceLines.current.push(l)
          }

          // P50 Median
          if (corridor.p50_median && corridor.p50_median > 0) {
            const l = candleSeries.current.createPriceLine({
              price: corridor.p50_median,
              color: '#3b82f6',
              lineWidth: 1,
              lineStyle: 1, // Dotted
              axisLabelVisible: true,
              title: 'P50 Median',
            })
            activePriceLines.current.push(l)
          }

          // P75 Target 1
          if (corridor.p75_target1 && corridor.p75_target1 > 0) {
            const l = candleSeries.current.createPriceLine({
              price: corridor.p75_target1,
              color: '#10b981',
              lineWidth: 1,
              lineStyle: 2, // Dashed
              axisLabelVisible: true,
              title: 'P75 Target 1',
            })
            activePriceLines.current.push(l)
          }

          // Q90 Runner
          if (corridor.q90_runner && corridor.q90_runner > 0) {
            const l = candleSeries.current.createPriceLine({
              price: corridor.q90_runner,
              color: '#8b5cf6',
              lineWidth: 1,
              lineStyle: 2, // Dashed
              axisLabelVisible: true,
              title: 'Q90 Runner',
            })
            activePriceLines.current.push(l)
          }
        } catch (e) {
          // ignore line creation error
        }
      }

      if (chartInstance.current) {
        chartInstance.current.timeScale().fitContent()
      }
    } catch (setDataErr) {
      console.error('Error setting chart data:', setDataErr)
    }
  }, [candles, corridor, showEMA20, showEMA50, showVWAP])

  // Live tick real-time candle update
  useEffect(() => {
    const unsubscribe = wsService.subscribeLive((msg) => {
      if (msg.type === 'TICK' && msg.data && msg.data.symbol === symbol) {
        if (!candleSeries.current) return
        const tickLtp = Number(msg.data.ltp || msg.data.close)
        if (!tickLtp || isNaN(tickLtp)) return

        setCandles((prevCandles) => {
          if (!prevCandles || prevCandles.length === 0) return prevCandles
          const lastIdx = prevCandles.length - 1
          const lastCandle = prevCandles[lastIdx]

          const updated = {
            ...lastCandle,
            high: Math.max(Number(lastCandle.high) || 0, tickLtp),
            low: Math.min(Number(lastCandle.low) || tickLtp, tickLtp),
            close: tickLtp,
            volume: (Number(lastCandle.volume) || 0) + (Number(msg.data.volume) || 1),
          }

          try {
            candleSeries.current.update({
              time: updated.time as Time,
              open: updated.open,
              high: updated.high,
              low: updated.low,
              close: updated.close,
            })
          } catch (e) {
            // ignore non-monotonic time
          }

          const copy = [...prevCandles]
          copy[lastIdx] = updated
          return copy
        })
      }
    })

    return () => {
      unsubscribe()
    }
  }, [symbol])

  // Latest bar reference for default legend display
  const displayBar = useMemo(() => {
    if (hoverData) return hoverData
    if (candles.length > 0) {
      const last = candles[candles.length - 1]
      return {
        time: last.time,
        open: last.open,
        high: last.high,
        low: last.low,
        close: last.close,
      }
    }
    return null
  }, [hoverData, candles])

  const barChange = displayBar ? displayBar.close - displayBar.open : 0
  const barChangePct = displayBar && displayBar.open > 0 ? (barChange / displayBar.open) * 100 : 0
  const isUp = barChange >= 0

  return (
    <div className="flex flex-col h-full glass-panel rounded-2xl overflow-hidden border border-[var(--border-subtle)] bg-[var(--surface)]">
      {/* 1. Institutional Company Info & Floating OHLCV Legend Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-2.5 border-b border-[var(--border-subtle)] bg-[var(--surface-raised)]">
        {/* Symbol, Name & Sector Tag */}
        <div className="flex items-center gap-2.5">
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-sm font-black text-[var(--text-primary)] tracking-wide">
                {symbol}
              </span>
              <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-blue-500/10 text-blue-400 font-bold border border-blue-500/20">
                NSE:EQ
              </span>
              {quote?.sector && (
                <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-indigo-500/10 text-indigo-400 font-semibold border border-indigo-500/20 hidden sm:inline">
                  {quote.sector}
                </span>
              )}
            </div>
            {quote?.company_name && (
              <span className="text-xs text-[var(--text-muted)] font-sans truncate max-w-[220px] sm:max-w-[320px] block">
                {quote.company_name}
              </span>
            )}
          </div>
        </div>

        {/* Floating Crosshair OHLCV Legend formatted in Indian Standard Time (IST) */}
        {displayBar && (
          <div className="flex flex-wrap items-center gap-2.5 font-mono text-[11px] bg-[var(--surface)] px-2.5 py-1 rounded-lg border border-[var(--border-subtle)] shadow-inner">
            {displayBar.time && (
              <span className="text-blue-400 font-bold flex items-center gap-1 border-r border-[var(--border-subtle)] pr-2">
                <Clock className="w-3 h-3 text-blue-400" />
                {timeframe === '1d'
                  ? new Date(displayBar.time * 1000).toLocaleDateString('en-IN', {
                      timeZone: 'Asia/Kolkata',
                      day: '2-digit',
                      month: 'short',
                      year: 'numeric'
                    })
                  : new Date(displayBar.time * 1000).toLocaleTimeString('en-IN', {
                      timeZone: 'Asia/Kolkata',
                      hour: '2-digit',
                      minute: '2-digit',
                      hour12: true,
                    }) + ' IST'}
              </span>
            )}
            <span className="text-[var(--text-muted)]">
              O: <strong className="text-[var(--text-primary)]">{displayBar.open.toFixed(2)}</strong>
            </span>
            <span className="text-[var(--text-muted)]">
              H: <strong className="text-[var(--text-primary)]">{displayBar.high.toFixed(2)}</strong>
            </span>
            <span className="text-[var(--text-muted)]">
              L: <strong className="text-[var(--text-primary)]">{displayBar.low.toFixed(2)}</strong>
            </span>
            <span className="text-[var(--text-muted)]">
              C: <strong className="text-[var(--text-primary)]">{displayBar.close.toFixed(2)}</strong>
            </span>
            <span className={`font-bold ${isUp ? 'text-emerald-400' : 'text-rose-400'}`}>
              {isUp ? '+' : ''}{barChangePct.toFixed(2)}%
            </span>
          </div>
        )}
      </div>

      {/* 2. Timeframe Selector & Technical Indicator Toggles Bar */}
      <div className="flex items-center justify-between px-4 py-1.5 border-b border-[var(--border-subtle)] bg-[var(--surface)]">
        {/* Timeframes */}
        <div className="flex items-center gap-1 bg-[var(--surface-raised)] p-0.5 rounded-lg border border-[var(--border-subtle)]">
          {TIMEFRAMES.map((tf) => {
            const isActive = timeframe === tf.value
            return (
              <button
                key={tf.value}
                onClick={() => setTimeframe(tf.value)}
                className={`px-2.5 py-0.5 text-xs font-mono rounded-md transition-all interactive-btn ${
                  isActive
                    ? 'bg-blue-600 text-white font-bold shadow-sm'
                    : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-overlay)]'
                }`}
              >
                {tf.label}
              </button>
            )
          })}
        </div>

        {/* Technical Overlays Toggle Pills */}
        <div className="flex items-center gap-1.5">
          <button
            onClick={() => setShowEMA20(!showEMA20)}
            className={`px-2 py-0.5 text-[10px] font-mono rounded-md border transition-all flex items-center gap-1 ${
              showEMA20
                ? 'bg-cyan-500/15 border-cyan-500/40 text-cyan-400 font-bold'
                : 'bg-[var(--surface-raised)] border-[var(--border-subtle)] text-[var(--text-muted)]'
            }`}
          >
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
            EMA 20
          </button>

          <button
            onClick={() => setShowEMA50(!showEMA50)}
            className={`px-2 py-0.5 text-[10px] font-mono rounded-md border transition-all flex items-center gap-1 ${
              showEMA50
                ? 'bg-amber-500/15 border-amber-500/40 text-amber-400 font-bold'
                : 'bg-[var(--surface-raised)] border-[var(--border-subtle)] text-[var(--text-muted)]'
            }`}
          >
            <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
            EMA 50
          </button>

          <button
            onClick={() => setShowVWAP(!showVWAP)}
            className={`px-2 py-0.5 text-[10px] font-mono rounded-md border transition-all flex items-center gap-1 ${
              showVWAP
                ? 'bg-purple-500/15 border-purple-500/40 text-purple-400 font-bold'
                : 'bg-[var(--surface-raised)] border-[var(--border-subtle)] text-[var(--text-muted)]'
            }`}
          >
            <span className="w-1.5 h-1.5 rounded-full bg-purple-400" />
            VWAP
          </button>
        </div>
      </div>

      {/* 3. Lightweight Charts Canvas Anchor (Strict auto-fitting flex-1) */}
      <div className="flex-1 w-full relative min-h-[340px] overflow-hidden">
        {isLoading && (
          <div className="absolute inset-0 z-20 flex flex-col items-center justify-center bg-[var(--surface)]/80 backdrop-blur-sm">
            <Loader2 className="w-6 h-6 text-blue-500 animate-spin mb-2" />
            <span className="font-mono text-xs text-[var(--text-muted)]">
              Ingesting {symbol} {timeframe} Lakehouse stream...
            </span>
          </div>
        )}
        <div ref={chartContainerRef} className="w-full h-full" />
      </div>
    </div>
  )
}
