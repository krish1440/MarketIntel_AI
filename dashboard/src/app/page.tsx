"use client";

import Link from 'next/link';

export default function LandingPage() {
  return (
    <main className="min-h-screen bg-slate-950 text-slate-50 selection:bg-indigo-500/30 overflow-hidden relative">
      {/* Background Decorative Elements */}
      <div className="absolute top-0 left-1/4 w-96 h-96 bg-indigo-600/10 rounded-full blur-[128px] -z-10 animate-pulse"></div>
      <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-purple-600/10 rounded-full blur-[128px] -z-10"></div>

      <div className="max-w-6xl mx-auto px-6 py-24 md:py-32 relative">
        {/* Navigation / Header */}
        <nav className="absolute top-8 left-6 right-6 flex justify-between items-center">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-indigo-500 rounded-lg flex items-center justify-center font-black text-white text-lg">M</div>
            <span className="font-bold tracking-tight text-xl">MarketIntel AI</span>
          </div>
          <Link 
            href="https://github.com/krish1440/MarketIntel_AI" 
            target="_blank"
            className="text-xs font-bold uppercase tracking-widest text-slate-400 hover:text-white transition-colors"
          >
            GitHub Repo
          </Link>
        </nav>

        {/* Hero Section */}
        <section className="text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-[10px] font-bold uppercase tracking-widest mb-8">
            <span className="w-1.5 h-1.5 bg-indigo-500 rounded-full animate-ping"></span>
            Production Grade Market Intelligence
          </div>
          
          <h1 className="text-5xl md:text-7xl font-black mb-6 tracking-tight leading-tight">
            Total Market Intelligence <br />
            <span className="bg-gradient-to-r from-indigo-400 via-purple-400 to-pink-400 bg-clip-text text-transparent">
              Powered by AI.
            </span>
          </h1>
          
          <p className="max-w-2xl mx-auto text-slate-400 text-lg md:text-xl mb-12 leading-relaxed">
            Unleash the power of 5-year historical data for over <span className="text-slate-100 font-semibold">2,361 stocks</span> across NSE and BSE. Real-time monitoring, sentiment analysis, and predictive modeling in one unified engine.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link 
              href="/market"
              className="w-full sm:w-auto px-8 py-4 bg-indigo-500 hover:bg-indigo-600 text-white font-bold rounded-2xl transition-all shadow-lg shadow-indigo-500/25 flex items-center justify-center gap-2 group"
            >
              Launch Dashboard
              <svg className="w-4 h-4 group-hover:translate-x-1 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
              </svg>
            </Link>
            
            <Link 
              href="https://github.com/krish1440/MarketIntel_AI"
              target="_blank"
              className="w-full sm:w-auto px-8 py-4 bg-slate-900 border border-slate-800 hover:border-slate-700 text-slate-300 font-bold rounded-2xl transition-all flex items-center justify-center gap-2"
            >
              Explore Source Code
            </Link>
          </div>
        </section>

        {/* Feature Grid */}
        <section className="mt-32 grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="p-8 rounded-3xl bg-slate-900/40 border border-slate-800/50 backdrop-blur-xl">
            <div className="w-12 h-12 bg-indigo-500/10 rounded-2xl flex items-center justify-center mb-6">
              <svg className="w-6 h-6 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <h3 className="text-xl font-bold mb-3">Real-Time Polling</h3>
            <p className="text-slate-500 text-sm leading-relaxed">
              Multi-threaded ingestion engine tracking 2,300+ symbols every minute with zero delay and deep accuracy.
            </p>
          </div>

          <div className="p-8 rounded-3xl bg-slate-900/40 border border-slate-800/50 backdrop-blur-xl">
            <div className="w-12 h-12 bg-purple-500/10 rounded-2xl flex items-center justify-center mb-6">
              <svg className="w-6 h-6 text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0012 18.75c-1.03 0-1.9-.4-2.593-1.1l-.548-.547z" />
              </svg>
            </div>
            <h3 className="text-xl font-bold mb-3">AI Intelligence</h3>
            <p className="text-slate-500 text-sm leading-relaxed">
              Integrated News Aggregator and LSTM-driven price forecasting models for forward-looking market insights.
            </p>
          </div>

          <div className="p-8 rounded-3xl bg-slate-900/40 border border-slate-800/50 backdrop-blur-xl">
            <div className="w-12 h-12 bg-emerald-500/10 rounded-2xl flex items-center justify-center mb-6">
              <svg className="w-6 h-6 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
              </svg>
            </div>
            <h3 className="text-xl font-bold mb-3">5Y Deep History</h3>
            <p className="text-slate-500 text-sm leading-relaxed">
              Complete historical mapping of the Indian equity universe, enabling long-term trend analysis and backtesting.
            </p>
          </div>
        </section>

        {/* Stats Section */}
        <section className="mt-32 pt-32 border-t border-slate-900 grid grid-cols-2 md:grid-cols-4 gap-12 text-center">
          <div>
            <div className="text-4xl font-black mb-1">2,300+</div>
            <div className="text-[10px] uppercase tracking-[0.2em] font-bold text-slate-600">Symbols</div>
          </div>
          <div>
            <div className="text-4xl font-black mb-1">5Y</div>
            <div className="text-[10px] uppercase tracking-[0.2em] font-bold text-slate-600">History</div>
          </div>
          <div>
            <div className="text-4xl font-black mb-1">1.6M+</div>
            <div className="text-[10px] uppercase tracking-[0.2em] font-bold text-slate-600">Data Points</div>
          </div>
          <div>
            <div className="text-4xl font-black mb-1">24/7</div>
            <div className="text-[10px] uppercase tracking-[0.2em] font-bold text-slate-600">Monitoring</div>
          </div>
        </section>
      </div>
    </main>
  );
}
