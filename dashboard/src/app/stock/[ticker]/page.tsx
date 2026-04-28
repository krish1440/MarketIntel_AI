"use client";

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { ArrowLeft, BrainCircuit, Activity, Zap, TrendingUp, TrendingDown, Target, ShieldAlert, BarChart3, Gauge } from 'lucide-react';

export default function StockDetail() {
  const { ticker } = useParams();
  const router = useRouter();
  const [exchange, setExchange] = useState<'NSE' | 'BSE'>('NSE');
  const [prediction, setPrediction] = useState<any>(null);
  const [modelStatus, setModelStatus] = useState<any>(null);
  const [news, setNews] = useState<any[]>([]);
  const [history, setHistory] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchData = async (ex: 'NSE' | 'BSE') => {
    setLoading(true);
    // Trigger an instant news refresh in the background
    fetch(`http://localhost:8000/api/news/refresh/${ticker}`, { method: 'POST' });
    
    const [predData, newsData, histData, statusData] = await Promise.all([
      fetch(`http://localhost:8000/api/predict/${ticker}?exchange=${ex}`).then(res => res.json()),
      fetch(`http://localhost:8000/api/news/${ticker}`).then(res => res.json()),
      fetch(`http://localhost:8000/api/history/${ticker}?exchange=${ex}`).then(res => res.json()),
      fetch(`http://localhost:8000/api/model-status`).then(res => res.json())
    ]);
    setPrediction(predData);
    setNews(newsData);
    setHistory(histData);
    setModelStatus(statusData);
    setLoading(false);
  };

  useEffect(() => {
    fetchData(exchange);
  }, [ticker, exchange]);

  if (loading && !prediction) return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center">
      <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-indigo-500"></div>
    </div>
  );

  const renderMainChart = () => {
    if (history.length < 5) return null;
    const prices = history.map(h => h.close);
    const min = Math.min(...prices);
    const max = Math.max(...prices);
    const range = (max - min) || 1;
    const width = 800;
    const height = 240;
    
    const points = prices.map((p, i) => {
      const x = (i / (prices.length - 1)) * width;
      const y = height - ((p - min) / range) * height;
      return `${x},${y}`;
    }).join(' ');

    return (
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-full overflow-visible">
        <path d={`M ${points} L ${width},${height} L 0,${height} Z`} fill="url(#mainGradient)" className="opacity-10" />
        <polyline fill="none" stroke={exchange === 'NSE' ? "#818cf8" : "#fbbf24"} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" points={points} />
        <defs>
          <linearGradient id="mainGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={exchange === 'NSE' ? "#818cf8" : "#fbbf24"} stopOpacity="0.4" />
            <stop offset="100%" stopColor="#818cf8" stopOpacity="0" />
          </linearGradient>
        </defs>
      </svg>
    );
  };

  const renderForecastChart = () => {
    if (!prediction?.forecast || history.length < 10) return null;
    const past = history.slice(-10).map(h => h.close);
    const future = prediction.forecast.map((f: any) => f.price);
    const combined = [...past, ...future];
    const min = Math.min(...combined);
    const max = Math.max(...combined);
    const range = (max - min) || 1;
    const width = 600;
    const height = 150;

    let pathD = `M 0,${height - ((past[0] - min) / range) * height}`;
    [...past, ...future].forEach((p, i) => {
        if (i === 0) return;
        const x = (i / (combined.length - 1)) * width;
        const y = height - ((p - min) / range) * height;
        pathD += ` L ${x},${y}`;
    });

    return (
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-full overflow-visible">
        <path d={pathD} fill="none" stroke="#f472b6" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" className="drop-shadow-[0_0_8px_rgba(244,114,182,0.5)]" />
        <line x1={(past.length / combined.length) * width} y1="0" x2={(past.length / combined.length) * width} y2={height} stroke="#1e293b" strokeWidth="1" strokeDasharray="4" />
      </svg>
    );
  };

  const tech = prediction?.technicals || {};

  return (
    <main className="min-h-screen bg-slate-950 text-slate-50 p-4 md:p-8 font-sans">
      <div className="max-w-7xl mx-auto">
        <div className="flex justify-between items-center mb-8">
            <Link href="/market" className="flex items-center text-slate-500 hover:text-white transition-all group">
                <div className="bg-slate-900 p-2 rounded-full mr-3 group-hover:bg-slate-800 transition-colors">
                    <ArrowLeft className="w-4 h-4" />
                </div>
                <span className="text-sm font-bold uppercase tracking-widest">Market Terminal</span>
            </Link>

            <div className="bg-slate-900/80 p-1.5 rounded-2xl border border-slate-800 flex items-center gap-1">
                {['NSE', 'BSE'].map(ex => (
                    <button key={ex} onClick={() => setExchange(ex as any)} className={`px-4 py-1.5 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all ${exchange === ex ? (ex === 'NSE' ? 'bg-indigo-500 shadow-lg' : 'bg-amber-500 shadow-lg') : 'text-slate-500 hover:text-slate-300'}`}>
                        {ex}
                    </button>
                ))}
            </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          <div className="lg:col-span-3 space-y-6">
            
            {/* Header Card */}
            <div className="bg-slate-900/40 border border-slate-800/60 rounded-[2.5rem] p-10 backdrop-blur-3xl shadow-2xl relative overflow-hidden">
              <div className="flex justify-between items-end mb-10 relative z-10">
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <span className={`px-2 py-0.5 text-[10px] font-black uppercase rounded-md border tracking-widest ${exchange === 'NSE' ? 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20' : 'bg-amber-500/10 text-amber-400 border-amber-500/20'}`}>
                        {exchange}: {ticker}
                    </span>
                    <div className="flex items-center gap-1 text-slate-600 text-[10px] font-black uppercase tracking-widest">
                        <Activity className="w-3 h-3" /> Live Analytics
                    </div>
                  </div>
                  <h1 className="text-7xl font-black tracking-tighter italic text-transparent bg-clip-text bg-gradient-to-r from-white via-white to-slate-500">
                    {ticker}
                  </h1>
                </div>
                <div className="text-right">
                  <div className="text-6xl font-mono font-black tracking-tighter text-slate-50">
                    ₹{prediction?.current_price?.toLocaleString()}
                  </div>
                  <p className="text-[10px] text-slate-500 font-bold uppercase tracking-widest mt-1">Real-Time Institutional LTP</p>
                </div>
              </div>
              
              <div className="h-72 w-full relative group z-10">
                 {renderMainChart()}
              </div>
            </div>

            {/* Industrial Technical Suite */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
               {[
                 { label: 'RSI (14)', val: tech.rsi?.toFixed(1), icon: Gauge, color: 'indigo' },
                 { label: 'MACD (12,26)', val: tech.macd?.toFixed(2), icon: BarChart3, color: 'emerald' },
                 { label: 'SMA (20/50)', val: `${tech.sma_20?.toFixed(0)} / ${tech.sma_50?.toFixed(0)}`, icon: TrendingUp, color: 'slate' },
                 { label: 'ATR (Vol)', val: tech.atr?.toFixed(2), icon: ShieldAlert, color: 'rose' }
               ].map((item, i) => (
                 <div key={i} className="bg-slate-900/40 border border-slate-800/60 p-6 rounded-[2rem] backdrop-blur-xl relative overflow-hidden group">
                   <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity"><item.icon className="w-12 h-12" /></div>
                   <p className="text-[10px] text-slate-500 uppercase font-black mb-1 tracking-widest">{item.label}</p>
                   <p className="text-2xl font-mono font-black text-slate-200 tracking-tighter">{item.val}</p>
                 </div>
               ))}
            </div>

            {/* Advanced Forecasting & Bollinger Bands */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="bg-slate-900/40 border border-slate-800/60 rounded-[2.5rem] p-8 backdrop-blur-3xl relative group">
                    <div className="flex items-center gap-3 mb-6">
                        <div className="p-2 bg-pink-500/20 rounded-xl border border-pink-500/30"><Zap className="w-5 h-5 text-pink-400" /></div>
                        <h2 className="text-lg font-black uppercase tracking-tighter text-pink-400">AI Forecasting Engine</h2>
                    </div>
                    <div className="h-40 relative">
                        {renderForecastChart()}
                    </div>
                    <div className="mt-4 flex justify-between items-center bg-slate-950/60 p-4 rounded-2xl border border-slate-800">
                        <div>
                            <p className="text-[10px] text-slate-500 font-bold uppercase">7-Day Target</p>
                            <p className="text-3xl font-mono font-black text-pink-400">₹{prediction?.forecast?.[6]?.price?.toLocaleString(undefined, {maximumFractionDigits:0})}</p>
                        </div>
                        <div className="text-right">
                            <p className="text-[10px] text-slate-500 font-bold uppercase">Expected Move</p>
                            <p className={`text-xl font-mono font-black ${((prediction?.forecast?.[6]?.price / prediction?.current_price) - 1) > 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                                {(((prediction?.forecast?.[6]?.price / prediction?.current_price) - 1) * 100).toFixed(2)}%
                            </p>
                        </div>
                    </div>
                </div>

                <div className="bg-slate-900/40 border border-slate-800/60 rounded-[2.5rem] p-8 backdrop-blur-3xl relative group">
                    <div className="flex items-center gap-3 mb-6">
                        <div className="p-2 bg-indigo-500/20 rounded-xl border border-indigo-500/30"><Target className="w-5 h-5 text-indigo-400" /></div>
                        <h2 className="text-lg font-black uppercase tracking-tighter text-indigo-400">Volatility Bands</h2>
                    </div>
                    <div className="space-y-4">
                        <div className="flex justify-between items-center">
                            <span className="text-[10px] text-slate-500 font-black uppercase">Upper Band</span>
                            <span className="text-lg font-mono font-bold text-slate-300">₹{tech.bb_upper?.toLocaleString()}</span>
                        </div>
                        <div className="h-1 bg-slate-800 rounded-full overflow-hidden">
                            <div 
                                className="h-full bg-gradient-to-r from-indigo-500 to-pink-500" 
                                style={{ width: `${((tech.vwap - tech.bb_lower) / (tech.bb_upper - tech.bb_lower)) * 100}%` }}
                            ></div>
                        </div>
                        <div className="flex justify-between items-center">
                            <span className="text-[10px] text-slate-500 font-black uppercase">Lower Band</span>
                            <span className="text-lg font-mono font-bold text-slate-300">₹{tech.bb_lower?.toLocaleString()}</span>
                        </div>
                        <div className="mt-4 pt-4 border-t border-slate-800 flex justify-between items-center">
                            <span className="text-[10px] text-indigo-400 font-black uppercase">VWAP Benchmark</span>
                            <span className="text-xl font-mono font-black text-indigo-400">₹{tech.vwap?.toLocaleString()}</span>
                        </div>
                    </div>
                </div>
            </div>

          </div>

            <div className="space-y-6">
            {/* Master Signal Card */}
            <div className={`bg-gradient-to-br p-8 rounded-[3rem] border border-white/5 backdrop-blur-xl relative overflow-hidden group ${prediction?.signal === 'BUY' ? 'from-emerald-900/40 to-slate-900/40 shadow-[0_0_50px_-12px_rgba(52,211,153,0.3)]' : prediction?.signal === 'SELL' ? 'from-rose-900/40 to-slate-900/40 shadow-[0_0_50px_-12px_rgba(251,113,133,0.3)]' : 'from-slate-800/40 to-slate-900/40'}`}>
              <div className="absolute -top-10 -right-10 w-40 h-40 bg-white/5 rounded-full blur-3xl transition-transform group-hover:scale-150"></div>
              <h2 className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-6 flex items-center gap-2">
                <BrainCircuit className="w-3 h-3" /> Fusion Signal
              </h2>
              <div className="text-center relative z-10">
                <div className={`text-8xl font-black mb-2 tracking-tighter italic ${prediction?.signal === 'BUY' ? 'text-emerald-400' : prediction?.signal === 'SELL' ? 'text-rose-400' : 'text-slate-200'}`}>
                  {prediction?.signal}
                </div>
                <div className="inline-block px-4 py-1 bg-slate-950/60 rounded-full border border-white/10 text-[10px] text-slate-400 font-bold uppercase tracking-widest mt-4">
                  Confidence: {((prediction?.confidence || 0) * 100).toFixed(0)}%
                </div>
              </div>
            </div>

            {/* Neural Health Card */}
            <div className="bg-slate-900/40 border border-slate-800/60 rounded-[3rem] p-8 backdrop-blur-xl">
                <h2 className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-6 flex items-center gap-2">
                    <ShieldAlert className="w-3 h-3" /> Neural Health
                </h2>
                <div className="space-y-4">
                    <div className="flex justify-between items-center">
                        <span className="text-[10px] text-slate-400 font-bold uppercase">Accuracy (RMSE)</span>
                        <span className="text-sm font-mono font-bold text-emerald-400">± ₹{modelStatus?.rmse_currency?.toFixed(2) || '0.00'}</span>
                    </div>
                    <div className="flex justify-between items-center">
                        <span className="text-[10px] text-slate-400 font-bold uppercase">Learning Mode</span>
                        <span className="text-[10px] px-2 py-0.5 bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 rounded font-black uppercase">Autonomous</span>
                    </div>
                    <div className="pt-4 border-t border-slate-800">
                        <p className="text-[8px] text-slate-600 font-bold uppercase mb-2">Last Background Update</p>
                        <p className="text-[10px] text-slate-400 font-mono">{modelStatus?.last_train ? new Date(modelStatus.last_train).toLocaleString() : 'Pending...'}</p>
                    </div>
                </div>
            </div>

            {/* News Sidebar */}
            <div className="bg-slate-900/40 border border-slate-800/60 rounded-[3rem] p-8 backdrop-blur-xl">
              <div className="flex justify-between items-center mb-8">
                <h2 className="text-[10px] font-black text-slate-500 uppercase tracking-widest flex items-center gap-2">
                  <Activity className="w-3 h-3" /> Market Intel
                </h2>
                <button 
                  onClick={async () => {
                    setLoading(true);
                    await fetch(`http://localhost:8000/api/news/refresh/${ticker}`, { method: 'POST' });
                    const freshNews = await fetch(`http://localhost:8000/api/news/${ticker}`).then(res => res.json());
                    setNews(freshNews);
                    setLoading(false);
                  }}
                  className="p-1.5 hover:bg-slate-800 rounded-lg transition-colors text-slate-500 hover:text-indigo-400"
                  title="Instant News Refresh"
                >
                  <Zap className="w-3.5 h-3.5" />
                </button>
              </div>
              <div className="space-y-6">
                {news.slice(0, 5).map((item, i) => (
                  <a key={i} href={item.url} target="_blank" className="block group">
                    <h3 className="text-xs font-bold text-slate-400 group-hover:text-indigo-400 transition-colors line-clamp-2 leading-relaxed mb-2">{item.title}</h3>
                    <div className="flex items-center gap-2">
                        <div className={`text-[8px] px-2 py-0.5 font-black uppercase rounded-sm ${item.sentiment > 0 ? 'bg-emerald-500/10 text-emerald-500 border border-emerald-500/20' : 'bg-rose-500/10 text-rose-500 border border-rose-500/20'}`}>
                            {item.sentiment > 0 ? 'Bullish' : 'Bearish'}
                        </div>
                        <span className="text-[8px] text-slate-600 font-bold uppercase tracking-tighter italic">Source: Alpha Intelligence</span>
                    </div>
                  </a>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
