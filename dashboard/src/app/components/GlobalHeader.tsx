"use client";

import Link from 'next/link';
import { Search, Activity, ShieldCheck, Zap, Layers } from 'lucide-react';

interface GlobalHeaderProps {
  search: string;
  setSearch: (val: string) => void;
  modelStatus: any;
  totalStocks: number;
}

export default function GlobalHeader({ search, setSearch, modelStatus, totalStocks }: GlobalHeaderProps) {
  return (
    <header className="relative z-50 mb-12">
      {/* Main Glass Container */}
      <div className="bg-slate-900/40 border border-white/5 rounded-[2.5rem] p-4 backdrop-blur-3xl shadow-2xl flex flex-wrap lg:flex-nowrap items-center gap-6 lg:gap-8">
        
        {/* Brand Section */}
        <Link href="/" className="flex items-center gap-4 group flex-shrink-0 ml-2">
          <div className="relative">
            <div className="absolute inset-0 bg-indigo-500/20 blur-xl group-hover:bg-indigo-500/40 transition-colors rounded-full"></div>
            <div className="w-12 h-12 bg-slate-950 rounded-2xl border border-white/10 flex items-center justify-center relative z-10 overflow-hidden group-hover:scale-105 transition-transform duration-500">
               <img src="/icon.png" alt="Logo" className="w-10 h-10 object-contain opacity-80 group-hover:opacity-100 transition-opacity" />
            </div>
          </div>
          <div className="flex flex-col">
            <h1 className="text-2xl font-black bg-gradient-to-r from-white via-slate-200 to-slate-500 bg-clip-text text-transparent tracking-tighter uppercase italic leading-none">
              MarketIntel AI
            </h1>
            <p className="text-[8px] text-slate-500 font-black uppercase tracking-[0.3em] mt-1 italic">Institutional Terminal</p>
          </div>
        </Link>

        {/* Search Engine - Expanded to fill middle */}
        <div className="flex-grow max-w-2xl relative group">
          <div className="absolute inset-0 bg-indigo-500/5 blur-xl group-focus-within:bg-indigo-500/10 transition-all rounded-2xl"></div>
          <div className="relative flex items-center">
            <Search className="w-4 h-4 text-slate-500 absolute left-5 z-20 group-focus-within:text-indigo-400 transition-colors" />
            <input 
              type="text"
              placeholder="Search symbol, index, or company name..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              suppressHydrationWarning
              className="w-full bg-slate-950/50 border border-white/5 rounded-2xl py-3.5 px-14 focus:outline-none focus:border-indigo-500/30 focus:bg-slate-950/80 transition-all text-sm font-medium backdrop-blur-xl relative z-10 placeholder:text-slate-600 text-white"
            />
          </div>
        </div>

        {/* Action & Status Hub */}
        <div className="flex items-center gap-3 ml-auto pr-2">
          {/* Opportunities Radar */}
          <Link href="/opportunities" className="hidden xl:flex items-center gap-2 px-5 py-3 bg-indigo-500/10 border border-indigo-500/20 rounded-2xl text-[9px] font-black uppercase tracking-widest text-indigo-400 hover:bg-indigo-500/20 transition-all group shadow-lg shadow-indigo-500/5">
            <Activity className="w-3.5 h-3.5 group-hover:scale-110 transition-transform" />
            Opportunities Radar
          </Link>

          {/* Precision Meter */}
          <div className="hidden md:flex items-center gap-4 bg-slate-950/50 border border-white/5 rounded-2xl px-5 py-2.5 backdrop-blur-md">
            <div className="flex flex-col">
              <span className="text-[8px] uppercase tracking-widest font-black text-slate-500 leading-none mb-1">Audit</span>
              <div className="flex items-center gap-1.5">
                <ShieldCheck className="w-3 h-3 text-emerald-500" />
                <span className="text-[10px] font-black text-emerald-400 uppercase tracking-tighter">Verified</span>
              </div>
            </div>
            
            <div className="w-px h-8 bg-white/5" />

            <div className="flex flex-col">
              <span className="text-[8px] uppercase tracking-widest font-black text-slate-500 leading-none mb-1">Precision</span>
              <span className="text-sm font-mono font-black text-white tracking-tighter">
                {modelStatus?.rmse_currency ? `±₹${modelStatus.rmse_currency.toFixed(2)}` : '---'}
              </span>
            </div>
          </div>

          {/* Coverage Badge */}
          <div className="flex items-center gap-3 bg-indigo-500/5 border border-indigo-500/20 rounded-2xl px-5 py-2.5">
            <div className="flex flex-col items-end">
              <span className="text-[8px] uppercase tracking-widest font-black text-indigo-500/70 leading-none mb-1">Coverage</span>
              <div className="flex items-center gap-2">
                <span className="text-sm font-mono font-black text-indigo-400 tracking-tighter">
                  {totalStocks.toLocaleString()}
                </span>
                <Layers className="w-3 h-3 text-indigo-500/50" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
