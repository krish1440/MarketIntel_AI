import React, { useEffect, useRef, useState } from 'react'
import {
  createChart,
  IChartApi,
  ISeriesApi,
  CandlestickData,
  HistogramData,
  Time
} from 'lightweight-charts'
import { CandleItem, CorridorForecast } from '../../types'
import { api } from '../../services/api'
import { Loader2, Maximize2 } from 'lucide-react'

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
  const candleSeries = useRef<ISeriesApi<'Candlestick'> | null>(null)
  const volumeSeries = useRef<ISeriesApi<'Histogram'> | null>(null)

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
    const bgColor = isDark ? '#0f1118' : '#ffffff'
    const textColor = isDark ? '#94a3b8' : '#475569'
    const gridColor = isDark ? 'rgba(255, 255, 255, 0.04)' : 'rgba(0, 0, 0, 0.04)'

    // Clear existing
    if (chartInstance.current) {
      chartInstance.current.remove()
      chartInstance.current = null
    }

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

    // Candlestick Series
    const candle = (chart as any).addCandlestickSeries({
      upColor: isDark ? '#10b981' : '#059669',
      downColor: isDark ? '#f43f5e' : '#e11d48',
      borderVisible: false,
      wickUpColor: isDark ? '#10b981' : '#059669',
      wickDownColor: isDark ? '#f43f5e' : '#e11d48',
    })

    // Volume Series
    const volume = (chart as any).addHistogramSeries({
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
          ? isDark ? 'rgba(16, 185, 129, 0.25)' : 'rgba(5, 150, 105, 0.25)'
          : isDark ? 'rgba(244, 63, 94, 0.25)' : 'rgba(225, 29, 72, 0.25)',
      })
    })

    candleSeries.current.setData(formattedCandles)
    volumeSeries.current.setData(formattedVolumes)

    // Add horizontal price corridor lines if available
    if (corridor && candleSeries.current) {
      try {
        // P05 Floor
        candleSeries.current.createPriceLine({
          price: corridor.p05_floor,
          color: '#f43f5e',
          lineWidth: 1,
          lineStyle: 2, // Dashed
          axisLabelVisible: true,
          title: 'P05 Stop',
        })

        // P50 Median
        candleSeries.current.createPriceLine({
          price: corridor.p50_median,
          color: '#3b82f6',
          lineWidth: 1,
          lineStyle: 1, // Dotted
          axisLabelVisible: true,
          title: 'P50 Median',
        })

        // P75 Target 1
        candleSeries.current.createPriceLine({
          price: corridor.p75_target1,
          color: '#10b981',
          lineWidth: 1,
          lineStyle: 2, // Dashed
          axisLabelVisible: true,
          title: 'P75 Target 1',
        })

        // Q90 Runner Target
        candleSeries.current.createPriceLine({
          price: corridor.q90_runner_target,
          color: '#f59e0b',
          lineWidth: 1,
          lineStyle: 2, // Dashed
          axisLabelVisible: true,
          title: 'Q90 Runner',
        })
      } catch (e) {
        // ignore line creation error
      }
    }

    if (chartInstance.current) {
      chartInstance.current.timeScale().fitContent()
    }
  }, [candles, corridor])

  return (
    <div className="flex flex-col h-full glass-panel rounded-2xl overflow-hidden border border-[var(--border-subtle)]">
      {/* Timeframe & Chart Tools Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-[var(--border-subtle)] bg-[var(--surface-raised)]">
        <div className="flex items-center gap-1 bg-[var(--surface)] p-0.5 rounded-lg border border-[var(--border-subtle)]">
          {TIMEFRAMES.map((tf) => (
            <button
              key={tf.value}
              onClick={() => setTimeframe(tf.value)}
              className={`px-2.5 py-1 text-xs font-mono font-medium rounded-md transition-all ${
                timeframe === tf.value
                  ? 'bg-blue-600 text-white shadow-sm font-semibold'
                  : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-raised)]'
              }`}
            >
              {tf.label}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-3 text-xs font-mono text-[var(--text-muted)]">
          {isLoading && (
            <div className="flex items-center gap-1.5 text-blue-500">
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
              <span className="text-[11px]">Syncing Lakehouse...</span>
            </div>
          )}
          <span>{candles.length} bars</span>
        </div>
      </div>

      {/* Candlestick Canvas Container */}
      <div className="relative flex-1 w-full min-h-[480px]">
        <div ref={chartContainerRef} className="absolute inset-0 w-full h-full" />
      </div>
    </div>
  )
}
