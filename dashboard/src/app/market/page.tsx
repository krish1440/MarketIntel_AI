"use client";

import { useEffect, useState } from 'react';
import { getStocks } from '@/lib/api';
import Link from 'next/link';

export default function Home() {
  const [stocks, setStocks] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);

  const limit = 50; // Grid-friendly limit

  useEffect(() => {
    setLoading(true);
    getStocks(page, limit, search).then(data => {
      setStocks(data.stocks || []);
      setTotal(data.total || 0);
      setLoading(false);
    });
  }, [page, search]);

  const totalPages = Math.ceil(total / limit);

  return (
    <main className="min-h-screen bg-slate-950 text-slate-50 p-8 pb-24">
      <div className="max-w-6xl mx-auto">
        <header className="mb-12 md:flex justify-between items-end gap-8">
          <div>
            <Link href="/">
              <h1 className="text-4xl font-bold bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent hover:opacity-80 transition-opacity">
                MarketIntel AI
              </h1>
            </Link>
            <p className="text-slate-400 mt-2">Premium Multimodal Stock Analysis (Full Market)</p>
          </div>
          
          <div className="mt-6 md:mt-0 flex-1 max-w-md">
            <div className="relative">
              <input 
                type="text"
                placeholder="Search symbol or name..."
                value={search}
                onChange={(e) => { setSearch(e.target.value); setPage(1); }}
                className="w-full bg-slate-900/50 border border-slate-800 rounded-2xl py-3 px-12 focus:outline-none focus:border-indigo-500/50 transition-all text-sm"
              />
              <svg className="w-4 h-4 text-slate-500 absolute left-4 top-1/2 -translate-y-1/2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
          </div>

          <div className="text-right hidden lg:block">
            <span className="text-[10px] uppercase tracking-[0.2em] font-bold text-slate-600 block mb-1">Total Coverage</span>
            <span className="text-emerald-400 text-xs font-bold flex items-center justify-end">
              <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full mr-2 animate-pulse"></span>
              {total.toLocaleString()} STOCKS
            </span>
          </div>
        </header>

        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-indigo-500"></div>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {stocks.map((stock) => (
                <Link 
                  href={`/stock/${stock.ticker}`}
                  key={stock.ticker}
                  className="bg-slate-900/40 border border-slate-800/50 rounded-2xl p-5 backdrop-blur-xl hover:border-indigo-500/30 transition-all cursor-pointer group hover:bg-slate-900/60"
                >
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <h3 className="text-lg font-bold group-hover:text-indigo-400 transition-colors tracking-tight">{stock.ticker}</h3>
                      <p className="text-[9px] text-slate-500 uppercase tracking-widest font-bold mt-0.5 truncate max-w-[120px]">{stock.name}</p>
                    </div>
                    <div className={`px-1.5 py-0.5 rounded text-[9px] font-black ${stock.change >= 0 ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'}`}>
                      {stock.change >= 0 ? '+' : ''}{stock.change.toFixed(2)}%
                    </div>
                  </div>
                  
                  <div className="flex items-baseline justify-between mt-4">
                    <div className="flex items-baseline">
                      <span className="text-slate-500 text-xs font-bold mr-1">₹</span>
                      <p className="text-xl font-mono font-bold tracking-tighter">
                        {stock.price > 0 ? stock.price.toLocaleString() : '---'}
                      </p>
                    </div>
                    <div className="w-8 h-4 bg-slate-800/50 rounded flex items-end gap-0.5 p-0.5">
                      <div className="flex-1 bg-indigo-500/30 rounded-t-[1px]" style={{height: '40%'}}></div>
                      <div className="flex-1 bg-indigo-500/50 rounded-t-[1px]" style={{height: '70%'}}></div>
                      <div className="flex-1 bg-indigo-500 rounded-t-[1px]" style={{height: '50%'}}></div>
                    </div>
                  </div>
                </Link>
              ))}
            </div>

            {/* Pagination Controls */}
            {totalPages > 1 && (
              <div className="mt-16 flex items-center justify-center gap-2">
                <button 
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="p-2 rounded-xl bg-slate-900 border border-slate-800 disabled:opacity-30 hover:border-indigo-500/50 transition-all"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" /></svg>
                </button>
                
                <div className="px-4 py-2 bg-slate-900/50 border border-slate-800 rounded-xl text-sm font-bold">
                  <span className="text-indigo-400">{page}</span>
                  <span className="text-slate-600 mx-2">/</span>
                  <span className="text-slate-400">{totalPages}</span>
                </div>

                <button 
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="p-2 rounded-xl bg-slate-900 border border-slate-800 disabled:opacity-30 hover:border-indigo-500/50 transition-all"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" /></svg>
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </main>
  );
}
