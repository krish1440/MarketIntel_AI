"use client";

import { useEffect, useState } from 'react';
import { getStocks, getWatchlist, addToWatchlist, removeFromWatchlist } from '@/lib/api';
import Link from 'next/link';
import WatchlistModal from '../components/WatchlistModal';
import GlobalHeader from '../components/GlobalHeader';

export default function MarketClient() {
  const [stocks, setStocks] = useState<any[]>([]);
  const [watchlist, setWatchlist] = useState<number[]>([]);
  const [modelStatus, setModelStatus] = useState<any>(null);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  
  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [activeStock, setActiveStock] = useState<any>(null);

  const limit = 50; // Grid-friendly limit

  const fetchWatchlist = () => {
    getWatchlist().then(data => {
      if (Array.isArray(data)) {
        setWatchlist(data.map((item: any) => item.id));
      } else {
        setWatchlist([]);
      }
    });
  };

  useEffect(() => {
    setLoading(true);
    fetchWatchlist();
    
    Promise.all([
      getStocks(page, limit, search),
      fetch('http://localhost:8000/api/model-status').then(res => res.json())
    ]).then(([stocksData, statusData]) => {
      setStocks(stocksData.stocks || []);
      setTotal(stocksData.total || 0);
      setModelStatus(statusData);
      setLoading(false);
    }).catch(err => {
      console.error("Critical: Failed to sync Market Data:", err);
      setStocks([]);
      setLoading(false);
    });
  }, [page, search]);

  const handleWatchClick = (e: any, stock: any) => {
    e.preventDefault();
    e.stopPropagation();
    setActiveStock(stock);
    setIsModalOpen(true);
  };

  const handleSaveWatchlist = async (targets: any) => {
    if (!activeStock) return;
    await addToWatchlist(activeStock.id, targets.above, targets.below, targets.sentiment);
    setIsModalOpen(false);
    fetchWatchlist();
  };

  const handleRemoveWatchlist = async () => {
    if (!activeStock) return;
    await removeFromWatchlist(activeStock.id);
    setIsModalOpen(false);
    fetchWatchlist();
  };

  const totalPages = Math.ceil(total / limit);

  return (
    <main className="min-h-screen bg-slate-950 text-slate-50 p-8 pb-24">
      <div className="max-w-7xl mx-auto">
        <GlobalHeader 
          search={search} 
          setSearch={(val) => { setSearch(val); setPage(1); }} 
          modelStatus={modelStatus} 
          totalStocks={total} 
        />

        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-indigo-500"></div>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {stocks.map((stock) => (
                <div key={stock.ticker} className="relative group">
                  {/* Tight Border Glow */}
                  <div className={`absolute -inset-[1px] rounded-[2rem] blur-[2px] transition-all duration-700 opacity-20 group-hover:opacity-100 group-hover:blur-[8px] ${stock.change >= 0 ? 'bg-emerald-500/50' : 'bg-rose-500/50'}`}></div>

                  <Link 
                    href={`/stock/${stock.ticker}`}
                    className={`relative overflow-hidden bg-slate-900/60 border border-slate-800/80 rounded-[2rem] p-6 backdrop-blur-xl transition-all duration-500 cursor-pointer flex flex-col h-full hover:bg-slate-900/80 hover:-translate-y-1 hover:border-slate-700/50 shadow-2xl ${stock.change >= 0 ? 'hover:shadow-[0_0_20px_-5px_rgba(16,185,129,0.3)]' : 'hover:shadow-[0_0_20px_-5px_rgba(244,63,94,0.3)]'}`}
                  >
                    {/* Persistent Ambient Glow */}
                    <div className={`absolute inset-0 opacity-[0.02] group-hover:opacity-[0.07] transition-opacity duration-700 ${stock.change >= 0 ? 'bg-emerald-400' : 'bg-rose-400'}`}></div>
                    
                    {/* Corner Accent Glow */}
                    <div className={`absolute -bottom-10 -right-10 w-32 h-32 rounded-full blur-[60px] transition-all duration-700 opacity-5 group-hover:opacity-20 ${stock.change >= 0 ? 'bg-emerald-500' : 'bg-rose-500'}`}></div>

                    <div className="flex justify-between items-start mb-6 relative z-10">
                      <div className="flex-1">
                        <div className="flex items-center gap-3">
                          <div className={`w-2 h-2 rounded-full ${stock.change >= 0 ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.6)]' : 'bg-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.6)]'}`}></div>
                          <h3 className="text-xl font-black group-hover:text-white transition-colors tracking-tighter italic uppercase">{stock.ticker}</h3>
                          <button 
                            onClick={(e) => handleWatchClick(e, stock)}
                            className={`p-1.5 rounded-xl transition-all hover:scale-110 active:scale-95 ${watchlist.includes(stock.id) ? 'text-rose-500 bg-rose-500/10' : 'text-slate-600 hover:text-slate-300 bg-slate-800/30'}`}
                          >
                            <svg className="w-3.5 h-3.5" fill={watchlist.includes(stock.id) ? "currentColor" : "none"} viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
                            </svg>
                          </button>
                        </div>
                        <p className="text-[10px] text-slate-500 uppercase tracking-[0.2em] font-black mt-1.5 truncate max-w-[140px] italic">{stock.name}</p>
                        
                        {/* New Signal Badge */}
                        {stock.signal && (
                          <div className={`mt-3 inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[8px] font-black tracking-widest border uppercase ${
                            stock.signal.includes('BUY') ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 
                            stock.signal.includes('SELL') ? 'bg-rose-500/10 text-rose-400 border-rose-500/20' : 
                            'bg-slate-800 text-slate-400 border-slate-700'
                          }`}>
                            <div className={`w-1 h-1 rounded-full animate-pulse ${stock.signal.includes('BUY') ? 'bg-emerald-400' : stock.signal.includes('SELL') ? 'bg-rose-400' : 'bg-slate-500'}`}></div>
                            {stock.signal}
                          </div>
                        )}
                      </div>
                      <div className={`px-2.5 py-1 rounded-full text-[10px] font-black tracking-widest border ${stock.change >= 0 ? 'bg-emerald-500/5 text-emerald-400 border-emerald-500/20' : 'bg-rose-500/5 text-rose-400 border-rose-500/20'}`}>
                        {stock.change >= 0 ? '▲' : '▼'} {Math.abs(stock.change).toFixed(2)}%
                      </div>
                    </div>
                  
                  <div className="flex items-end justify-between mt-8 relative z-10">
                    <div className="space-y-1">
                      <p className="text-[10px] text-slate-600 font-bold uppercase tracking-widest">Market Value</p>
                      <div className="flex items-baseline">
                        <span className="text-slate-500 text-sm font-black mr-1">₹</span>
                        <p className="text-2xl font-mono font-black tracking-tighter group-hover:text-white transition-colors">
                          {stock.price > 0 ? stock.price.toLocaleString() : '---'}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-end gap-1 h-10 px-2 py-1 bg-slate-950/40 rounded-xl border border-white/5">
                      {[40, 70, 50, 80, 60].map((h, i) => (
                        <div 
                          key={i} 
                          className={`w-1.5 rounded-full transition-all duration-700 group-hover:scale-y-110 origin-bottom ${stock.change >= 0 ? 'bg-emerald-500/40' : 'bg-rose-500/40'}`} 
                          style={{height: `${h}%`, opacity: 0.3 + (i * 0.15)}}
                        ></div>
                      ))}
                    </div>
                  </div>
                </Link>
              </div>
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

        {activeStock && (
          <WatchlistModal 
            stock={activeStock}
            isOpen={isModalOpen}
            onClose={() => setIsModalOpen(false)}
            onSave={handleSaveWatchlist}
            onRemove={handleRemoveWatchlist}
            isWatched={watchlist.includes(activeStock.id)}
          />
        )}
      </div>
    </main>
  );
}
