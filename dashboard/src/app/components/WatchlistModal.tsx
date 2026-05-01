"use client";

import { useState } from 'react';

interface WatchlistModalProps {
  stock: any;
  isOpen: boolean;
  onClose: () => void;
  onSave: (targets: { above?: number, below?: number, sentiment: number }) => void;
  onRemove: () => void;
  isWatched: boolean;
}

export default function WatchlistModal({ stock, isOpen, onClose, onSave, onRemove, isWatched }: WatchlistModalProps) {
  const [above, setAbove] = useState<string>("");
  const [below, setBelow] = useState<string>("");
  const [sentiment, setSentiment] = useState<number>(0.7);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
      <div className="bg-slate-900 border border-slate-800 w-full max-w-md rounded-3xl shadow-2xl overflow-hidden animate-in fade-in zoom-in duration-200">
        <div className="p-6 border-b border-slate-800 flex justify-between items-center">
          <div>
            <h2 className="text-xl font-bold text-white">{stock.ticker} Monitoring</h2>
            <p className="text-xs text-slate-500 uppercase tracking-widest mt-1">Set Alert Thresholds</p>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-slate-800 rounded-full transition-colors text-slate-400">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="p-6 space-y-6">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-[10px] uppercase font-black text-slate-500 tracking-tighter">Price Above (₹)</label>
              <input 
                type="number" 
                placeholder="e.g. 3000"
                value={above}
                onChange={(e) => setAbove(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl py-3 px-4 focus:outline-none focus:border-indigo-500 transition-all text-sm"
              />
            </div>
            <div className="space-y-2">
              <label className="text-[10px] uppercase font-black text-slate-500 tracking-tighter">Price Below (₹)</label>
              <input 
                type="number" 
                placeholder="e.g. 2500"
                value={below}
                onChange={(e) => setBelow(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl py-3 px-4 focus:outline-none focus:border-indigo-500 transition-all text-sm"
              />
            </div>
          </div>

          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <label className="text-[10px] uppercase font-black text-slate-500 tracking-tighter">Sentiment Sensitivity</label>
              <span className="text-[10px] font-mono text-indigo-400 font-bold">{sentiment.toFixed(2)}</span>
            </div>
            <input 
              type="range" 
              min="0.1" 
              max="1.0" 
              step="0.05"
              value={sentiment}
              onChange={(e) => setSentiment(parseFloat(e.target.value))}
              className="w-full h-1 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-indigo-500"
            />
            <div className="flex justify-between text-[8px] text-slate-600 uppercase font-bold">
              <span>Very Sensitive</span>
              <span>Stable Only</span>
            </div>
          </div>
        </div>

        <div className="p-6 bg-slate-950/50 border-t border-slate-800 flex gap-3">
          {isWatched && (
            <button 
              onClick={onRemove}
              className="px-4 py-2 bg-rose-500/10 text-rose-500 rounded-xl text-xs font-bold hover:bg-rose-500/20 transition-all"
            >
              Stop Watching
            </button>
          )}
          <button 
            onClick={() => onSave({ 
              above: above ? parseFloat(above) : undefined, 
              below: below ? parseFloat(below) : undefined, 
              sentiment 
            })}
            className="flex-1 px-4 py-2 bg-indigo-600 text-white rounded-xl text-xs font-bold hover:bg-indigo-500 shadow-lg shadow-indigo-500/20 transition-all"
          >
            {isWatched ? 'Update Monitor' : 'Start Monitoring'}
          </button>
        </div>
      </div>
    </div>
  );
}
