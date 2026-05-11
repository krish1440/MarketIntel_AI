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

export default function OpportunitiesClient() {
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('http://127.0.0.1:8000/api/top-opportunities')
      .then(res => res.json())
      .then(data => {
        setOpportunities(data);
        setLoading(false);
      })
      .catch(err => {
        console.error('Error fetching opportunities:', err);
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
                <h2 className="text-4xl font-black tracking-tighter group-hover:text-blue-400 transition-colors">{opp.ticker}</h2>
                {opp.signal.includes('BUY') ? <TrendingUp className="w-5 h-5 text-emerald-500" /> : <TrendingDown className="w-5 h-5 text-rose-500" />}
              </div>
              <p className="text-slate-500 font-bold text-sm tracking-tight truncate max-w-[180px] uppercase">{opp.name}</p>
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

            {/* Premium RSI Slider */}
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
  );
}
