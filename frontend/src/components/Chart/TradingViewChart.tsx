import React, { useEffect, useRef, useState } from 'react'
import {
  createChart,
  CandlestickSeries,
  HistogramSeries,
  IChartApi,
  CandlestickData,
  HistogramData,
  Time
} from 'lightweight-charts'
import { CandleItem, CorridorForecast } from '../../types'
import { api } from '../../services/api'
import { wsService } from '../../services/websocket'
import { Loader2, BarChart3, TrendingUp, Layers } from 'lucide-react'
import { motion } from 'framer-motion'

interface TradingViewChartProps {
  symbol: string
  corridor: CorridorForecast | null
}

const TIMEFRAMES = [
  { label: '1m', value: '1m' },
  { label: '5m', value: '5m' },
  { label: '15m', value: '15m' },
  { label: '1h', value: '1h' },
  { label: '1D', value: '1d' },
]

export const TradingViewChart: React.FC<TradingViewChartProps> = ({ symbol, corridor }) => {
  const chartContainerRef = useRef<HTMLDivElement | null>(null)
  const chartInstance = useRef<IChartApi | null>(null)
  const candleSeries = useRef<any>(null)
  const volumeSeries = useRef<any>(null)
  const activePriceLines = useRef<any[]>([])

  const [timeframe, setTimeframe] = useState<string>('5m')
  const [isLoading, setIsLoading] = useState<boolean>(true)
  const [candles, setCandles] = useState<CandleItem[]>([])

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

  // Initialize and update Lightweight Charts
  useEffect(() => {
    if (!chartContainerRef.current) return

    const isDark = document.documentElement.classList.contains('dark')
    const bgColor = isDark ? '#0e121b' : '#ffffff'
    const textColor = isDark ? '#94a3b8' : '#475569'
    const gridColor = isDark ? 'rgba(255, 255, 255, 0.04)' : 'rgba(0, 0, 0, 0.04)'

    // Clear existing
    if (chartInstance.current) {
      chartInstance.current.remove()
      chartInstance.current = null
    }

    try {
      const chart = createChart(chartContainerRef.current, {
        width: chartContainerRef.current.clientWidth,
        height: chartContainerRef.current.clientHeight || 520,
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
            bottom: 0.2, // Leave room for volume
          },
        },
        timeScale: {
          borderColor: isDark ? 'rgba(255, 255, 255, 0.08)' : 'rgba(0, 0, 0, 0.08)',
          timeVisible: true,
          secondsVisible: false,
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

      // Volume Series (Lightweight Charts v5)
      const volume = chart.addSeries(HistogramSeries, {
        priceFormat: {
          type: 'volume',
        },
        priceScaleId: '', // Overlay over price scale
      })

      volume.priceScale().applyOptions({
        scaleMargins: {
          top: 0.8, // Align volume to bottom 20%
          bottom: 0,
        },
      })

      chartInstance.current = chart
      candleSeries.current = candle
      volumeSeries.current = volume
    } catch (err) {
      console.error('Failed to initialize TradingView chart:', err)
    }

    // Resize observer
    const handleResize = () => {
      if (chartContainerRef.current && chartInstance.current) {
        chartInstance.current.applyOptions({
          width: chartContainerRef.current.clientWidth,
          height: chartContainerRef.current.clientHeight,
        })
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

  // Set data whenever candles change
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

          // Q90 Runner Target
          const q90 = corridor.q90_runner ?? corridor.q90_runner_target
          if (q90 && q90 > 0) {
            const l = candleSeries.current.createPriceLine({
              price: q90,
              color: '#a855f7',
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
  }, [candles, corridor])

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

  return (
    <div className="flex flex-col h-full glass-panel rounded-2xl overflow-hidden border border-[var(--border-subtle)]">
      {/* Timeframe & Chart Tools Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-[var(--border-subtle)] bg-[var(--surface-raised)]">
        <div className="flex items-center gap-1 bg-[var(--surface)] p-1 rounded-xl border border-[var(--border-subtle)]">
          {TIMEFRAMES.map((tf) => {
            const isActive = timeframe === tf.value
            return (
              <button
                key={tf.value}
                onClick={() => setTimeframe(tf.value)}
                className={`relative px-3 py-1 text-xs font-mono rounded-lg transition-all interactive-btn ${
                  isActive
                    ? 'text-blue-400 font-bold'
                    : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                }`}
              >
                {isActive && (
                  <motion.div
                    layoutId="tf-pill-active"
                    className="absolute inset-0 bg-blue-500/10 border border-blue-500/30 rounded-lg"
                    transition={{ type: 'spring', stiffness: 400, damping: 30 }}
                  />
                )}
                <span className="relative z-10">{tf.label}</span>
              </button>
            )
          })}
        </div>

        <div className="flex items-center gap-3 text-xs font-mono text-[var(--text-muted)]">
          {isLoading ? (
            <div className="flex items-center gap-1.5 text-blue-400">
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
              <span className="text-[11px]">Syncing Parquet...</span>
            </div>
          ) : (
            <div className="flex items-center gap-1 text-[11px] text-[var(--text-secondary)]">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
              <span>{candles.length} OHLCV Bars</span>
            </div>
          )}
        </div>
      </div>

      {/* Candlestick Canvas Container */}
      <div className="relative flex-1 w-full min-h-[480px]">
        <div ref={chartContainerRef} className="absolute inset-0 w-full h-full" />
      </div>
    </div>
  )
}
