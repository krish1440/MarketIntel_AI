'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { Zap, Target, Activity, TrendingUp, TrendingDown, ArrowRight } from 'lucide-react';

interface Opportunity {
  ticker: string;
  name: string;
  signal: string;
  confidence: number;
  current_price: number;
  score: number;
  rsi: number;
  adx: number;
}

interface RadarStock {
  ticker: string;
  pe: number;
  rsi: number;
  signal: string;
  price: number;
}

interface SentimentArticle {
  ticker: string;
  title: string;
  sentiment: number;
  date: string;
  url: string;
}

export default function OpportunitiesClient() {
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [radarData, setRadarData] = useState<RadarStock[]>([]);
  const [sentiment, setSentiment] = useState<SentimentArticle[]>([]);
  const [loading, setLoading] = useState(true);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    Promise.all([
      fetch('http://127.0.0.1:8000/api/top-opportunities').then(res => res.json()),
      fetch('http://127.0.0.1:8000/api/opportunities/radar').then(res => res.json()),
      fetch('http://127.0.0.1:8000/api/global-sentiment').then(res => res.json())
    ]).then(([opps, radar, sent]) => {
      setOpportunities(opps);
      setRadarData(radar);
      setSentiment(sent);
      setLoading(false);
    }).catch(err => {
      console.error('Error fetching dashboard data:', err);
      setLoading(false);
    });
  }, []);

  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-10">
        {[1, 2, 3, 4, 5, 6, 7, 8, 9].map(i => (
          <div key={i} className="h-[400px] bg-white/5 rounded-[2.5rem] animate-pulse border border-white/10" />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-20">
      {/* 2D Opportunity Radar (Scatter Map) */}
      <section className="bg-[#111218]/50 border border-white/5 rounded-[3rem] p-12 backdrop-blur-3xl relative overflow-hidden">
        <div className="absolute top-0 left-0 w-full h-full bg-blue-500/5 blur-[120px] rounded-full pointer-events-none" />
        
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-12 gap-6 relative z-10">
          <div>
            <h2 className="text-4xl font-black tracking-tighter mb-2 flex items-center gap-3">
              <Activity className="w-8 h-8 text-blue-500" /> MULTIMODAL RADAR
            </h2>
            <p className="text-slate-500 font-bold tracking-tight uppercase text-xs">Valuation (P/E) vs Momentum (RSI) Heatmap</p>
          </div>
          <div className="flex gap-4">
             <div className="flex items-center gap-2 px-4 py-2 bg-emerald-500/10 rounded-xl border border-emerald-500/20">
                <div className="w-2 h-2 rounded-full bg-emerald-500" />
                <span className="text-[10px] font-black text-emerald-400 uppercase tracking-widest">Growth Gem</span>
             </div>
             <div className="flex items-center gap-2 px-4 py-2 bg-rose-500/10 rounded-xl border border-rose-500/20">
                <div className="w-2 h-2 rounded-full bg-rose-500" />
                <span className="text-[10px] font-black text-rose-400 uppercase tracking-widest">Over-Extended</span>
             </div>
          </div>
        </div>

        <div className="relative h-[500px] w-full border-l border-b border-white/10 rounded-bl-3xl p-10 bg-white/[0.01]">
          {/* Legend Labels */}
          <div className="absolute -left-12 top-1/2 -rotate-90 text-[10px] font-black text-slate-500 tracking-[0.3em] uppercase">PE RATIO (Value)</div>
          <div className="absolute -bottom-10 left-1/2 -translate-x-1/2 text-[10px] font-black text-slate-500 tracking-[0.3em] uppercase">RSI (Momentum)</div>
          
          <div className="absolute top-4 right-8 text-[9px] font-black text-slate-700 uppercase tracking-widest">Institutional Scatter Plot v4.2</div>

          {/* Grid Lines */}
          <div className="absolute inset-0 grid grid-cols-4 grid-rows-4 pointer-events-none">
            {[1,2,3].map(i => <div key={i} className="border-r border-white/5" />)}
            {[1,2,3].map(i => <div key={i} className="border-b border-white/5" />)}
          </div>

          {/* Radar Points */}
          {radarData.map((s, i) => {
            // Mapping: PE (0-100) -> Y (100-0), RSI (0-100) -> X (0-100)
            const x = Math.min(Math.max(s.rsi, 0), 100);
            const y = Math.min(Math.max(100 - (s.pe * 1.5), 0), 100); // Scaled for Indian market PE
            
            return (
              <Link 
                key={s.ticker} 
                href={`/stock/${s.ticker}`}
                className="absolute group/point"
                style={{ left: `${x}%`, top: `${y}%` }}
              >
                <div className={`w-4 h-4 rounded-full border-2 transition-all duration-500 hover:scale-[4] hover:z-50 cursor-pointer shadow-xl ${
                  s.pe < 25 && s.rsi < 40 ? 'bg-emerald-500 border-emerald-400 shadow-emerald-500/20' :
                  s.pe > 60 || s.rsi > 70 ? 'bg-rose-500 border-rose-400 shadow-rose-500/20' :
                  'bg-blue-500 border-blue-400 shadow-blue-500/20'
                }`} />
                <div className="absolute -top-10 left-1/2 -translate-x-1/2 bg-white text-black text-[10px] font-black px-3 py-1 rounded-lg opacity-0 group-hover/point:opacity-100 transition-all pointer-events-none whitespace-nowrap shadow-2xl z-[100]">
                  {s.ticker}: ₹{s.price} (PE: {s.pe.toFixed(1)})
                </div>
              </Link>
            );
          })}
        </div>
      </section>

      {/* Alpha Opportunity Cards */}
      <div>
        <div className="flex items-center gap-4 mb-10">
          <h2 className="text-4xl font-black tracking-tighter">ALPHA CARDS</h2>
          <div className="h-px flex-1 bg-white/10" />
          <span className="text-xs font-black text-slate-500 uppercase tracking-widest">{opportunities.length} High Conviction Setups</span>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-10">
          {opportunities.map((opp) => (
            <Link 
              key={opp.ticker} 
              href={`/stock/${opp.ticker}`}
              className="group relative overflow-hidden bg-[#111218] border border-white/5 rounded-[2.5rem] p-10 hover:border-blue-500/30 transition-all duration-700 hover:shadow-[0_0_80px_-20px_rgba(59,130,246,0.2)]"
            >
              {/* Dynamic Background Mesh */}
              <div className="absolute -top-32 -right-32 w-64 h-64 bg-blue-500/10 blur-[100px] rounded-full group-hover:bg-blue-500/20 transition-all duration-1000" />
              <div className="absolute -bottom-32 -left-32 w-64 h-64 bg-purple-500/5 blur-[100px] rounded-full group-hover:bg-purple-500/10 transition-all duration-1000" />
              
              <div className="flex justify-between items-start mb-10 relative z-10">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <h2 className="text-2xl font-black tracking-tight group-hover:text-blue-400 transition-colors uppercase truncate max-w-[220px]">{opp.name || opp.ticker}</h2>
                    {opp.signal.includes('BUY') ? <TrendingUp className="w-5 h-5 text-emerald-500" /> : <TrendingDown className="w-5 h-5 text-rose-500" />}
                  </div>
                  <p className="text-slate-400 font-bold text-xs tracking-widest uppercase">{opp.ticker}</p>
                </div>
                <div className={`px-5 py-2 rounded-2xl text-[10px] font-black tracking-[0.2em] uppercase border-2 shadow-lg transition-all ${
                  opp.signal.includes('BUY') 
                    ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20 shadow-emerald-500/10' 
                    : 'bg-rose-500/10 text-rose-400 border-rose-500/20 shadow-rose-500/10'
                }`}>
                  {opp.signal}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-6 mb-10 relative z-10">
                <div className="bg-white/[0.02] rounded-3xl p-6 border border-white/5 backdrop-blur-md group-hover:border-blue-500/10 transition-all">
                  <div className="flex items-center gap-2 mb-2">
                    <Zap className="w-3 h-3 text-blue-400" />
                    <span className="text-[9px] uppercase text-slate-500 font-black tracking-widest">AI Confidence</span>
                  </div>
                  <p className="text-3xl font-mono font-black text-white tracking-tighter">{(opp.confidence * 100).toFixed(0)}<span className="text-sm ml-1 text-slate-600">%</span></p>
                </div>
                <div className="bg-white/[0.02] rounded-3xl p-6 border border-white/5 backdrop-blur-md group-hover:border-purple-500/10 transition-all">
                  <div className="flex items-center gap-2 mb-2">
                    <Target className="w-3 h-3 text-purple-400" />
                    <span className="text-[9px] uppercase text-slate-500 font-black tracking-widest">Alpha Score</span>
                  </div>
                  <p className="text-3xl font-mono font-black text-white tracking-tighter">{opp.score.toFixed(1)}</p>
                </div>
              </div>

              <div className="space-y-6 relative z-10">
                <div className="flex justify-between items-end">
                  <div>
                    <span className="text-[10px] text-slate-500 block mb-2 font-black uppercase tracking-widest">Entry Target</span>
                    <span className="text-3xl font-black tracking-tighter text-white">₹{opp.current_price.toLocaleString()}</span>
                  </div>
                  <div className="text-right">
                    <div className="flex items-center gap-2 justify-end mb-2">
                      <Activity className="w-3 h-3 text-indigo-400" />
                      <span className="text-[10px] text-slate-500 font-black uppercase tracking-widest">Momentum</span>
                    </div>
                    <span className={`text-xl font-black tracking-tighter ${opp.adx > 25 ? 'text-indigo-400' : 'text-slate-500'}`}>
                      {opp.adx > 25 ? 'STRONG' : 'WEAK'}
                    </span>
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-[9px] uppercase font-black text-slate-500 mb-3 tracking-widest">
                    <span>RSI OVERVIEW</span>
                    <span className={opp.rsi < 30 ? 'text-emerald-400' : opp.rsi > 70 ? 'text-rose-400' : 'text-blue-400'}>
                      {opp.rsi < 30 ? 'OVERSOLD BUY' : opp.rsi > 70 ? 'OVERBOUGHT SELL' : 'NEUTRAL ZONE'}
                    </span>
                  </div>
                  <div className="h-2 w-full bg-white/[0.03] rounded-full overflow-hidden border border-white/5 p-[2px]">
                    <div 
                      className={`h-full rounded-full transition-all duration-1000 shadow-[0_0_10px_rgba(59,130,246,0.3)] ${
                        opp.rsi < 30 ? 'bg-emerald-500' : opp.rsi > 70 ? 'bg-rose-500' : 'bg-blue-500'
                      }`}
                      style={{ width: `${opp.rsi}%` }}
                    />
                  </div>
                </div>
              </div>

              <div className="mt-10 pt-8 border-t border-white/5 flex items-center justify-between text-[10px] text-slate-500 font-black uppercase tracking-widest relative z-10">
                <span className="flex items-center gap-2"><div className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" /> 20D HORIZON</span>
                <span className="flex items-center gap-1 text-white group-hover:text-blue-400 transition-all group-hover:gap-2">
                  EXECUTE TRADE <ArrowRight className="w-3 h-3" />
                </span>
              </div>
            </Link>
          ))}
        </div>
      </div>

      {/* Global Sentiment Stream */}
      <section className="bg-black/40 border border-white/5 rounded-[3rem] p-12 overflow-hidden relative">
        <div className="flex items-center justify-between mb-10">
          <h2 className="text-3xl font-black tracking-tighter">GLOBAL SENTIMENT STREAM</h2>
          <div className="flex items-center gap-3">
             <div className="w-2 h-2 rounded-full bg-blue-500 animate-ping" />
             <span className="text-[10px] font-black text-blue-400 tracking-widest uppercase">Live Pulse</span>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-h-[600px] overflow-y-auto pr-4 scrollbar-hide">
          {sentiment.map((s, i) => (
            <a 
              key={i} 
              href={s.url} 
              target="_blank" 
              rel="noopener noreferrer"
              className="p-8 bg-white/[0.02] border border-white/5 rounded-3xl hover:bg-white/[0.05] transition-all group"
            >
              <div className="flex justify-between items-start mb-4">
                <span className="px-3 py-1 bg-blue-500/10 text-blue-400 rounded-lg text-[9px] font-black tracking-widest uppercase">{s.ticker}</span>
                <span className={`px-3 py-1 rounded-lg text-[9px] font-black tracking-widest uppercase ${
                  s.sentiment > 0.3 ? 'bg-emerald-500/10 text-emerald-400' :
                  s.sentiment < -0.3 ? 'bg-rose-500/10 text-rose-400' :
                  'bg-slate-500/10 text-slate-400'
                }`}>
                  {s.sentiment > 0.3 ? 'BULLISH' : s.sentiment < -0.3 ? 'BEARISH' : 'NEUTRAL'}
                </span>
              </div>
              <h3 className="text-xl font-bold tracking-tight text-white mb-4 line-clamp-2 group-hover:text-blue-400 transition-colors">{s.title}</h3>
              <div className="flex justify-between items-center">
                 <span className="text-[10px] text-slate-600 font-bold">{mounted ? new Date(s.date).toLocaleString() : ''}</span>
                 <ArrowRight className="w-4 h-4 text-slate-700 group-hover:translate-x-2 transition-transform" />
              </div>
            </a>
          ))}
        </div>
      </section>
    </div>
  );
}
