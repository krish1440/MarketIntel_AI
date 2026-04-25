"use client";

import { useEffect, useState } from 'react';
import { getStocks } from '@/lib/api';
import Link from 'next/link';

export default function Home() {
  const [stocks, setStocks] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getStocks().then(data => {
      setStocks(data);
      setLoading(false);
    });
  }, []);

  return (
    <main className="min-h-screen bg-slate-950 text-slate-50 p-8">
      <div className="max-w-6xl mx-auto">
        <header className="mb-12 flex justify-between items-end">
          <div>
            <h1 className="text-4xl font-bold bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
              Market Intelligence
            </h1>
            <p className="text-slate-400 mt-2">Premium Multimodal Stock Analysis</p>
          </div>
          <div className="text-right hidden md:block">
            <span className="text-[10px] uppercase tracking-[0.2em] font-bold text-slate-600 block mb-1">Exchange Status</span>
            <span className="text-emerald-400 text-xs font-bold flex items-center justify-end">
              <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full mr-2 animate-pulse"></span>
              LIVE DATA ACTIVE
            </span>
          </div>
        </header>

        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-indigo-500"></div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {stocks.map((stock) => (
              <Link 
                href={`/stock/${stock.ticker}`}
                key={stock.ticker}
                className="bg-slate-900/50 border border-slate-800 rounded-3xl p-6 backdrop-blur-xl hover:border-indigo-500/50 transition-all cursor-pointer group hover:bg-slate-900/80 relative overflow-hidden"
              >
                {/* Decorative Glow */}
                <div className="absolute -top-12 -right-12 w-24 h-24 bg-indigo-500/10 blur-3xl rounded-full group-hover:bg-indigo-500/20 transition-all"></div>
                
                <div className="flex justify-between items-start mb-6">
                  <div>
                    <h3 className="text-xl font-bold group-hover:text-indigo-400 transition-colors tracking-tight">{stock.ticker}</h3>
                    <p className="text-[10px] text-slate-500 uppercase tracking-widest font-bold mt-1">{stock.name.split(' ')[0]}</p>
                  </div>
                  <div className={`px-2 py-0.5 rounded text-[10px] font-black tracking-tighter ${stock.change >= 0 ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'}`}>
                    {stock.change >= 0 ? '+' : ''}{stock.change.toFixed(2)}%
                  </div>
                </div>
                
                <div className="mt-8 flex items-baseline">
                  <span className="text-slate-500 text-sm font-bold mr-1">₹</span>
                  <p className="text-3xl font-mono font-bold tracking-tighter">
                    {stock.price > 0 ? stock.price.toLocaleString() : '---'}
                  </p>
                </div>

                <div className="mt-8 pt-6 border-t border-slate-800/50 flex justify-between items-center">
                  <span className="text-[10px] text-slate-600 uppercase tracking-[0.1em] font-black">AI Signal</span>
                  <div className="flex items-center">
                    <span className="text-[10px] text-indigo-400 font-black uppercase tracking-tighter mr-2">Neural Scan</span>
                    <div className="flex gap-0.5">
                      <div className="w-1 h-3 bg-indigo-500/40 rounded-full"></div>
                      <div className="w-1 h-3 bg-indigo-500/60 rounded-full"></div>
                      <div className="w-1 h-3 bg-indigo-500 rounded-full animate-pulse"></div>
                    </div>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
