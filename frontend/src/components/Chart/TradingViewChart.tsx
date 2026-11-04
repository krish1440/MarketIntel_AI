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
import { CandleItem, CorridorForecast, StockQuote, AISignalResponse } from '../../types'
import { api } from '../../services/api'
import { wsService } from '../../services/websocket'
import { Loader2, TrendingUp, Layers, Eye, Activity, Sparkles, Clock, Target, ShieldAlert, Sliders } from 'lucide-react'

interface TradingViewChartProps {
  symbol: string
  corridor: CorridorForecast | null
  quote?: StockQuote | null
  signal?: AISignalResponse | null
}

const TIMEFRAMES = [
  { label: '1m', value: '1m' },
  { label: '5m', value: '5m' },
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

function computeBollingerBands(candles: CandleItem[], period = 20, multiplier = 2): {
  upper: LineData<Time>[]
  lower: LineData<Time>[]
  middle: LineData<Time>[]
} {
  const upper: LineData<Time>[] = []
  const lower: LineData<Time>[] = []
  const middle: LineData<Time>[] = []

  for (let i = period - 1; i < candles.length; i++) {
    const slice = candles.slice(i - period + 1, i + 1)
    const mean = slice.reduce((acc, c) => acc + c.close, 0) / period
    const variance = slice.reduce((acc, c) => acc + Math.pow(c.close - mean, 2), 0) / period
    const stdDev = Math.sqrt(variance)
    const timeVal = candles[i].time as Time

    middle.push({ time: timeVal, value: Number(mean.toFixed(2)) })
    upper.push({ time: timeVal, value: Number((mean + multiplier * stdDev).toFixed(2)) })
    lower.push({ time: timeVal, value: Number((mean - multiplier * stdDev).toFixed(2)) })
  }
  return { upper, lower, middle }
}

export const TradingViewChart: React.FC<TradingViewChartProps> = ({ symbol, corridor, quote, signal }) => {
  const chartContainerRef = useRef<HTMLDivElement | null>(null)
  const chartInstance = useRef<IChartApi | null>(null)
  const candleSeries = useRef<any>(null)
  const volumeSeries = useRef<any>(null)
  const ema20Series = useRef<any>(null)
  const ema50Series = useRef<any>(null)
  const vwapSeries = useRef<any>(null)
  const bbUpperSeries = useRef<any>(null)
  const bbLowerSeries = useRef<any>(null)
  const activePriceLines = useRef<any[]>([])

  const [timeframe, setTimeframe] = useState<string>('5m')
  const [isLoading, setIsLoading] = useState<boolean>(true)
  const [isLoadingPast, setIsLoadingPast] = useState<boolean>(false)
  const [candles, setCandles] = useState<CandleItem[]>([])

  const candlesRef = useRef<CandleItem[]>([])
  candlesRef.current = candles

  const isLoadingPastRef = useRef<boolean>(false)
  const hasMorePastRef = useRef<boolean>(true)

  // Technical Indicators Toggles
  const [showEMA20, setShowEMA20] = useState<boolean>(true)
  const [showEMA50, setShowEMA50] = useState<boolean>(false)
  const [showVWAP, setShowVWAP] = useState<boolean>(true)
  const [showBB, setShowBB] = useState<boolean>(false)
  const [showSR, setShowSR] = useState<boolean>(false)
  const [showAIPosition, setShowAIPosition] = useState<boolean>(true)

  // Floating Crosshair Hover Legend
  const [hoverData, setHoverData] = useState<{
    time?: number
    open: number
    high: number
    low: number
    close: number
    volume?: number
  } | null>(null)

  // Reset pagination state when symbol or timeframe changes
  useEffect(() => {
    hasMorePastRef.current = true
    isLoadingPastRef.current = false
  }, [symbol, timeframe])

  // Initial Load candle data from backend
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

  // Initialize Lightweight Charts with institutional precision
  useEffect(() => {
    if (!chartContainerRef.current) return

    const isDark = document.documentElement.classList.contains('dark')
    const bgColor = isDark ? '#0c1017' : '#ffffff'
    const textColor = isDark ? '#94a3b8' : '#475569'
    const gridColor = isDark ? 'rgba(255, 255, 255, 0.03)' : 'rgba(0, 0, 0, 0.03)'

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
          autoScale: true,
        },
        handleScale: {
          axisPressedMouseMove: {
            time: true,
            price: true, // Smooth TradingView vertical price drag
          },
          mouseWheel: true,
          pinch: true,
        },
        handleScroll: {
          mouseWheel: true,
          pressedMouseMove: true, // Smooth chart panning
          horzTouchDrag: true,
          vertTouchDrag: true,
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
              hour12: true,
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

      // Candlestick Series
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
        priceScaleId: '',
      })

      volume.priceScale().applyOptions({
        scaleMargins: {
          top: 0.78,
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

      const bbUpper = chart.addSeries(LineSeries, {
        color: 'rgba(59, 130, 246, 0.45)',
        lineWidth: 1,
        title: 'BB Upper',
        crosshairMarkerVisible: false,
      })

      const bbLower = chart.addSeries(LineSeries, {
        color: 'rgba(59, 130, 246, 0.45)',
        lineWidth: 1,
        title: 'BB Lower',
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

      // Infinite Past Scroll: Fetch older candles when user scrolls near left boundary
      chart.timeScale().subscribeVisibleLogicalRangeChange(async (logicalRange) => {
        if (!logicalRange) return
        if (
          logicalRange.from < 5 &&
          !isLoadingPastRef.current &&
          hasMorePastRef.current &&
          candlesRef.current.length > 0
        ) {
          isLoadingPastRef.current = true
          setIsLoadingPast(true)
          const earliestTime = candlesRef.current[0].time
          try {
            const res = await api.getChartCandles(symbol, timeframe, 500, earliestTime)
            if (res.candles && res.candles.length > 0) {
              const older = res.candles.filter((c) => c.time < earliestTime)
              if (older.length > 0) {
                setCandles((prev) => [...older, ...prev])
              } else {
                hasMorePastRef.current = false
              }
            } else {
              hasMorePastRef.current = false
            }
          } catch (err) {
            console.error('Failed to load past candles:', err)
          } finally {
            isLoadingPastRef.current = false
            setIsLoadingPast(false)
          }
        }
      })

      chartInstance.current = chart
      candleSeries.current = candle
      volumeSeries.current = volume
      ema20Series.current = ema20
      ema50Series.current = ema50
      vwapSeries.current = vwap
      bbUpperSeries.current = bbUpper
      bbLowerSeries.current = bbLower
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
      if (bbUpperSeries.current && bbLowerSeries.current) {
        if (showBB) {
          const bb = computeBollingerBands(candles, 20, 2)
          bbUpperSeries.current.setData(bb.upper)
          bbLowerSeries.current.setData(bb.lower)
        } else {
          bbUpperSeries.current.setData([])
          bbLowerSeries.current.setData([])
        }
      }

      // Clear previous price lines
      activePriceLines.current.forEach((line) => {
        try {
          candleSeries.current.removePriceLine(line)
        } catch (e) {}
      })
      activePriceLines.current = []

      // If showAIPosition is OFF, do not draw any target/corridor lines and clear markers
      if (!showAIPosition) {
        if (candleSeries.current) {
          candleSeries.current.setMarkers([])
        }
        return
      }

      const curPrice = quote?.ltp || (candles.length > 0 ? candles[candles.length - 1].close : 0)

      // 1. AI Position Box Overlay (Entry, Target 1, Runner Target 2, Stop Loss)
      if (signal && curPrice > 0 && candleSeries.current) {
        try {
          const entryPx = signal.recommended_entry || curPrice

          // Entry Level
          const entryLine = candleSeries.current.createPriceLine({
            price: entryPx,
            color: '#3b82f6',
            lineWidth: 1,
            lineStyle: 1, // Dotted
            axisLabelVisible: true,
            title: `ENTRY: ₹${entryPx.toFixed(2)}`,
          })
          activePriceLines.current.push(entryLine)

          // Target 1 Level
          if (signal.target_1 && signal.target_1 > 0) {
            const diffPct = (((signal.target_1 - entryPx) / entryPx) * 100).toFixed(1)
            const t1Line = candleSeries.current.createPriceLine({
              price: signal.target_1,
              color: '#10b981',
              lineWidth: 2,
              lineStyle: 0, // Solid
              axisLabelVisible: true,
              title: `TGT 1: ₹${signal.target_1.toFixed(2)} (${Number(diffPct) >= 0 ? '+' : ''}${diffPct}%)`,
            })
            activePriceLines.current.push(t1Line)
          }

          // Runner Target 2 Level
          if (signal.target_2 && signal.target_2 > 0) {
            const diffPct2 = (((signal.target_2 - entryPx) / entryPx) * 100).toFixed(1)
            const t2Line = candleSeries.current.createPriceLine({
              price: signal.target_2,
              color: '#8b5cf6',
              lineWidth: 1,
              lineStyle: 2, // Dashed
              axisLabelVisible: true,
              title: `RUNNER: ₹${signal.target_2.toFixed(2)} (${Number(diffPct2) >= 0 ? '+' : ''}${diffPct2}%)`,
            })
            activePriceLines.current.push(t2Line)
          }

          // Dynamic Stop Loss Level
          if (signal.dynamic_stop_loss && signal.dynamic_stop_loss > 0) {
            const diffSlPct = (((signal.dynamic_stop_loss - entryPx) / entryPx) * 100).toFixed(1)
            const slLine = candleSeries.current.createPriceLine({
              price: signal.dynamic_stop_loss,
              color: '#f43f5e',
              lineWidth: 2,
              lineStyle: 0, // Solid
              axisLabelVisible: true,
              title: `STOP LOSS: ₹${signal.dynamic_stop_loss.toFixed(2)} (${diffSlPct}%)`,
            })
            activePriceLines.current.push(slLine)
          }
        } catch (posErr) {
          console.error('Error drawing AI position box lines:', posErr)
        }
      }

      // 2. Horizontal Quant Corridor Levels (Clamped defensively to prevent scale distortion)
      if (corridor && candleSeries.current && curPrice > 0 && !signal) {
        try {
          // Only draw corridor lines if within +-25% on intraday to maintain pristine chart scale
          const isWithinIntradayRange = (val: number) => {
            if (timeframe === '1d') return true
            return Math.abs(val - curPrice) / curPrice <= 0.25
          }

          if (corridor.p05_floor && isWithinIntradayRange(corridor.p05_floor)) {
            const l = candleSeries.current.createPriceLine({
              price: corridor.p05_floor,
              color: '#f43f5e',
              lineWidth: 1,
              lineStyle: 2,
              axisLabelVisible: true,
              title: 'P05 Quant Stop',
            })
            activePriceLines.current.push(l)
          }

          if (corridor.p50_median && isWithinIntradayRange(corridor.p50_median)) {
            const l = candleSeries.current.createPriceLine({
              price: corridor.p50_median,
              color: '#3b82f6',
              lineWidth: 1,
              lineStyle: 1,
              axisLabelVisible: true,
              title: 'P50 Median',
            })
            activePriceLines.current.push(l)
          }

          if (corridor.p75_target1 && isWithinIntradayRange(corridor.p75_target1)) {
            const l = candleSeries.current.createPriceLine({
              price: corridor.p75_target1,
              color: '#10b981',
              lineWidth: 1,
              lineStyle: 2,
              axisLabelVisible: true,
              title: 'P75 Target 1',
            })
            activePriceLines.current.push(l)
          }

          if (corridor.q90_runner && isWithinIntradayRange(corridor.q90_runner)) {
            const l = candleSeries.current.createPriceLine({
              price: corridor.q90_runner,
              color: '#8b5cf6',
              lineWidth: 1,
              lineStyle: 2,
              axisLabelVisible: true,
              title: 'Q90 Runner',
            })
            activePriceLines.current.push(l)
          }
        } catch (e) {}
      }

      // 3. AI Buy / Sell Signal Markers on Candles
      if (signal && candleSeries.current && candles.length > 0) {
        try {
          const lastCandle = candles[candles.length - 1]
          const isBuy = signal.action === 'STRONG_BUY' || signal.action === 'BUY'
          const isSell = signal.action === 'STRONG_SELL' || signal.action === 'SELL'

          if (isBuy || isSell) {
            candleSeries.current.setMarkers([
              {
                time: lastCandle.time as Time,
                position: isBuy ? 'belowBar' : 'aboveBar',
                color: isBuy ? '#10b981' : '#f43f5e',
                shape: isBuy ? 'arrowUp' : 'arrowDown',
                text: `AI ${signal.action} (${signal.confidence_pct?.toFixed(0)}%)`,
              },
            ])
          } else {
            candleSeries.current.setMarkers([])
          }
        } catch (markerErr) {}
      }

      // 4. Institutional Support & Resistance Levels (Key Swing High & Low)
      if (showSR && candleSeries.current && candles.length >= 10) {
        try {
          const recentSlice = candles.slice(-50)
          const highPx = Math.max(...recentSlice.map((c) => c.high))
          const lowPx = Math.min(...recentSlice.map((c) => c.low))

          const resLine = candleSeries.current.createPriceLine({
            price: highPx,
            color: '#f59e0b',
            lineWidth: 1,
            lineStyle: 2,
            axisLabelVisible: true,
            title: `RES: ₹${highPx.toFixed(2)}`,
          })
          const supLine = candleSeries.current.createPriceLine({
            price: lowPx,
            color: '#06b6d4',
            lineWidth: 1,
            lineStyle: 2,
            axisLabelVisible: true,
            title: `SUP: ₹${lowPx.toFixed(2)}`,
          })
          activePriceLines.current.push(resLine, supLine)
        } catch (srErr) {}
      }
    } catch (setDataErr) {
      console.error('Error setting chart data:', setDataErr)
    }
  }, [candles, corridor, signal, quote?.ltp, showEMA20, showEMA50, showVWAP, showBB, showSR, showAIPosition, timeframe])

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
          } catch (e) {}

          const next = [...prevCandles]
          next[lastIdx] = updated
          return next
        })
      }
    })

    return () => {
      unsubscribe()
    }
  }, [symbol])

  // Active display bar for hover legend
  const displayBar = useMemo(() => {
    if (hoverData) return hoverData
    if (candles.length > 0) return candles[candles.length - 1]
    return null
  }, [hoverData, candles])

  const barChangePct = useMemo(() => {
    if (!displayBar || !displayBar.open) return 0
    return ((displayBar.close - displayBar.open) / displayBar.open) * 100
  }, [displayBar])

  const isUp = barChangePct >= 0

  return (
    <div className="w-full h-full flex flex-col glass-panel rounded-2xl overflow-hidden border border-[var(--border-subtle)] bg-[var(--surface)]">
      {/* 1. Institutional Chart Header Bar */}
      <div className="flex flex-wrap items-center justify-between px-4 py-2 border-b border-[var(--border-subtle)] bg-[var(--surface-raised)] gap-2">
        {/* Symbol & Sector Identification */}
        <div className="flex items-center gap-2.5">
          <div className="flex items-center gap-1.5">
            <span className="font-mono font-black text-sm tracking-wide text-[var(--text-primary)]">
              {symbol}
            </span>
            <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-[var(--surface)] text-[var(--text-muted)] border border-[var(--border-subtle)] uppercase">
              NSE:EQ
            </span>
          </div>

          {quote?.sector && (
            <span className="hidden sm:inline-flex items-center gap-1 text-[10px] font-mono px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20">
              <Sparkles className="w-2.5 h-2.5" />
              {quote.sector}
            </span>
          )}

          {isLoadingPast && (
            <span className="inline-flex items-center gap-1 text-[10px] font-mono text-blue-400 animate-pulse">
              <Loader2 className="w-3 h-3 animate-spin" />
              Loading history...
            </span>
          )}
        </div>

        {/* Dynamic Floating OHLCV Hover Legend with IST */}
        {displayBar && (
          <div className="flex flex-wrap items-center gap-2 sm:gap-3 text-xs font-mono bg-[var(--surface)] px-2.5 py-1 rounded-lg border border-[var(--border-subtle)]">
            {displayBar.time && (
              <span className="text-[var(--text-secondary)] font-medium flex items-center gap-1 pr-1 border-r border-[var(--border-subtle)]">
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

      {/* 2. Timeframe Selector (1m, 5m, 1D) & Technical Indicator Toggles Bar */}
      <div className="flex flex-wrap items-center justify-between px-4 py-1.5 border-b border-[var(--border-subtle)] bg-[var(--surface)] gap-2">
        {/* Timeframes: 1m, 5m, 1D */}
        <div className="flex items-center gap-1 bg-[var(--surface-raised)] p-0.5 rounded-lg border border-[var(--border-subtle)]">
          {TIMEFRAMES.map((tf) => {
            const isActive = timeframe === tf.value
            return (
              <button
                key={tf.value}
                onClick={() => setTimeframe(tf.value)}
                className={`px-3 py-0.5 text-xs font-mono rounded-md transition-all interactive-btn ${
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

        {/* Technical Overlays & AI Position Box Toggle Pills */}
        <div className="flex flex-wrap items-center gap-1.5">
          {/* AI Trade Position Box Overlay Toggle */}
          <button
            onClick={() => setShowAIPosition(!showAIPosition)}
            className={`px-2.5 py-0.5 text-[10px] font-mono rounded-md border transition-all flex items-center gap-1 shadow-sm ${
              showAIPosition
                ? 'bg-emerald-500/20 border-emerald-500/60 text-emerald-400 font-black shadow-emerald-500/20'
                : 'bg-[var(--surface-raised)] border-[var(--border-subtle)] text-[var(--text-muted)] hover:text-[var(--text-primary)]'
            }`}
            title="Toggle AI Target / Stop-Loss Position Box"
          >
            <Target className="w-3 h-3 text-emerald-400" />
            AI Targets: {showAIPosition ? 'ON' : 'OFF'}
          </button>

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

          <button
            onClick={() => setShowBB(!showBB)}
            className={`px-2 py-0.5 text-[10px] font-mono rounded-md border transition-all flex items-center gap-1 ${
              showBB
                ? 'bg-blue-500/15 border-blue-500/40 text-blue-400 font-bold'
                : 'bg-[var(--surface-raised)] border-[var(--border-subtle)] text-[var(--text-muted)]'
            }`}
            title="Bollinger Bands (20, 2)"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-blue-400" />
            BB (20, 2)
          </button>

          {/* S/R Key Levels Toggle */}
          <button
            onClick={() => setShowSR(!showSR)}
            className={`px-2 py-0.5 text-[10px] font-mono rounded-md border transition-all flex items-center gap-1 ${
              showSR
                ? 'bg-amber-500/15 border-amber-500/40 text-amber-400 font-bold'
                : 'bg-[var(--surface-raised)] border-[var(--border-subtle)] text-[var(--text-muted)]'
            }`}
            title="Key Technical Support & Resistance Levels"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
            S/R Levels
          </button>

          {/* Reset Auto-Fit button */}
          <button
            onClick={() => chartInstance.current?.timeScale().fitContent()}
            className="px-2 py-0.5 text-[10px] font-mono rounded-md border bg-[var(--surface-raised)] border-[var(--border-subtle)] text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-all"
            title="Reset Chart View to Fit All Visible Bars"
          >
            Fit View
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