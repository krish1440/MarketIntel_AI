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

  const fetchStocks = (showLoading = true) => {
    if (showLoading) setLoading(true);
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
  };

  useEffect(() => {
    fetchWatchlist();
  }, []);

  useEffect(() => {
    fetchStocks(true);
    const interval = setInterval(() => fetchStocks(false), 30000); // Background refresh every 30s
    return () => clearInterval(interval);
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
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
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
                    
                    <div className="flex justify-between items-start mb-6 relative z-10">
                      <div className="flex-1">
                        <div className="flex items-center gap-3">
                          <div className={`w-2 h-2 rounded-full ${stock.change >= 0 ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.6)]' : 'bg-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.6)]'}`}></div>
                          <h3 className="text-lg font-black group-hover:text-white transition-colors tracking-tight uppercase line-clamp-1 flex-1">{stock.name || stock.ticker}</h3>
                          <button 
                            onClick={(e) => handleWatchClick(e, stock)}
                            className={`p-1.5 rounded-xl transition-all hover:scale-110 active:scale-95 ${watchlist.includes(stock.id) ? 'text-rose-500 bg-rose-500/10' : 'text-slate-600 hover:text-slate-300 bg-slate-800/30'}`}
                          >
                            <svg className="w-4 h-4" fill={watchlist.includes(stock.id) ? "currentColor" : "none"} stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.382-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
                            </svg>
                          </button>
                        </div>
                        <p className="text-[10px] text-slate-500 font-bold tracking-[0.2em] mt-1.5 uppercase">{stock.ticker}</p>
                      </div>
                      <div className={`px-3 py-1 rounded-lg text-[10px] font-black tracking-widest ${stock.change >= 0 ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'}`}>
                        {stock.change >= 0 ? '+' : ''}{stock.change.toFixed(2)}%
                      </div>
                    </div>

                    <div className="mt-auto relative z-10">
                      <div className="flex justify-between items-end">
                        <div className="flex flex-col">
                          <span className="text-[10px] text-slate-500 font-black uppercase tracking-widest mb-1">Live Price</span>
                          <span className="text-4xl font-mono font-black text-white tracking-tighter">₹{stock.price > 0 ? stock.price.toLocaleString() : '---'}</span>
                        </div>
                        <div className="p-3 bg-white/5 rounded-2xl group-hover:bg-indigo-500/20 transition-colors">
                          <svg className="w-5 h-5 text-slate-500 group-hover:text-indigo-400 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                          </svg>
                        </div>
                      </div>
                    </div>
                  </Link>
                </div>
              ))}
            </div>

            {/* Institutional Pagination */}
            <div className="mt-16 flex justify-center items-center gap-6">
              <button 
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-8 py-3 bg-slate-900 border border-slate-800 rounded-2xl text-xs font-black uppercase tracking-widest hover:bg-slate-800 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
              >
                Previous
              </button>
              <div className="flex items-center gap-2">
                <span className="text-[10px] text-slate-500 font-black uppercase tracking-widest">Terminal Node</span>
                <span className="px-4 py-2 bg-indigo-500/10 border border-indigo-500/20 rounded-xl text-indigo-400 font-mono font-black text-sm">
                  {page.toString().padStart(2, '0')}
                </span>
                <span className="text-[10px] text-slate-500 font-black uppercase tracking-widest">of</span>
                <span className="text-[10px] text-slate-300 font-black uppercase tracking-widest">{totalPages.toString().padStart(2, '0')}</span>
              </div>
              <button 
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="px-8 py-3 bg-slate-900 border border-slate-800 rounded-2xl text-xs font-black uppercase tracking-widest hover:bg-slate-800 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
              >
                Next
              </button>
            </div>
          </>
        )}
      </div>

      <WatchlistModal 
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        stock={activeStock}
        onSave={handleSaveWatchlist}
        onRemove={handleRemoveWatchlist}
        isAlreadyInWatchlist={activeStock ? watchlist.includes(activeStock.id) : false}
      />
    </main>
  );
}
